# SPDX-License-Identifier: MIT
import contextlib
import struct

from ...hw.dart import DART
from ...proxyutils import RegMonitor
from ...utils import *
from .decoder import *


class AVDDevice:
    def __init__(self, u, dev_path="/arm-io/avd", dart_path="/arm-io/dart-avd"):
        self.u = u
        self.p = u.proxy
        self.iface = u.iface

        self.PAGE_SIZE = 0x4000
        self.base = u.adt[dev_path].get_reg(0)[0]  # 0x268000000
        self.node = u.adt[dev_path]

        self.p.pmgr_adt_clocks_enable(dev_path)
        self.p.pmgr_adt_clocks_enable(dart_path)
        dart = DART.from_adt(u, dart_path)
        dart.initialize()
        self.dart = dart

        mon = RegMonitor(u)
        AVD_REGS = [
            # (0x1000000, 0x4000, "unk0"),
            # (0x1010000, 0x4000, "dart"),
            # (0x1002000, 0x1000, "unk2"),
            # (0x1070000, 0x4000, "piodma"),
            # (0x108c000, 0xc000, "cmd"),
            # (0x1098000, 0x4000, "mbox"),
            # (0x10a3000, 0x1000, "unka"),
            (0x1100000, 0xC000, "dec"),
            (0x110C000, 0x4000, "dma"),
            # (0x1400000, 0x4000, "wrap"),
        ]
        for x in AVD_REGS:
            mon.add(self.base + x[0], x[1], name=x[2])
        self.mon = mon

        iomon = RegMonitor(u, ascii=True)
        iomon1 = RegMonitor(u, ascii=True)

        def readmem_iova(addr, size, readfn=None):
            try:
                return self.dart.ioread(0, addr, size)
            except Exception as e:
                print(e)
                return None

        def readmem_iova1(addr, size, readfn=None):
            try:
                return self.dart.ioread(1, addr, size)
            except Exception as e:
                print(e)
                return None

        iomon.readmem = readmem_iova
        iomon1.readmem = readmem_iova1
        self.iomon = iomon
        self.iomon1 = iomon1
        self.stfu = False
        self.decoder = AVDDec(self)

    def log(self, x):
        print(f"[AVD] {x}")

    def poll(self):
        self.mon.poll()

    def avd_r32(self, off):
        return self.p.read32(self.base + off)

    def avd_w32(self, off, x):
        if not self.stfu:
            self.log("w32(0x%x, 0x%x)" % (off, x))
        return self.p.write32(self.base + off, x)

    def avd_r64(self, off):
        return self.p.read64(self.base + off)

    def avd_w64(self, off, x):
        return self.p.write64(self.base + off, x)

    def avd_wbuf(self, off, buf):
        for n in range(len(buf) // 4):
            x = struct.unpack("<I", buf[n * 4 : (n + 1) * 4])[0]
            self.p.write32(self.base + off + (n * 4), x)

    def boot(self):
        self.avd_w32(0x1000000, 0xFFF)
        self.p.mask32(0x269010060, self.p.read32(0x269010060), 0x80016100)
        self.p.mask32(0x269010068, self.p.read32(0x269010068), 0xF0F0F)
        self.p.mask32(0x26901006C, self.p.read32(0x26901006C), 0x80808)
        self.p.memset32(self.base + 0x1080000, 0, 0xC000)  # CODE
        self.p.memset32(self.base + 0x108C000, 0, 0xC000)  # SRAM
        with contextlib.redirect_stdout(None):
            self.wrap_ctrl_device_init()
            self.avd_dma_tunables_stage0()
        self.poll()

    def avd_mcpu_start(self):
        avd_r32 = self.avd_r32
        avd_w32 = self.avd_w32
        avd_w32(0x1098008, 0xE)
        avd_w32(0x1098010, 0x0)
        avd_w32(0x1098048, 0x0)

        avd_w32(0x1098010, 0x0)
        avd_w32(0x1098048, 0x0)

        avd_w32(0x1098050, 0x1)
        avd_w32(0x1098068, 0x1)
        avd_w32(0x109805C, 0x1)
        avd_w32(0x1098074, 0x1)

        avd_w32(0x1098010, 0x2)  # Enable mailbox interrupts
        avd_w32(0x1098048, 0x8)  # Enable mailbox interrupts
        avd_w32(0x1098008, 0x1)
        assert avd_r32(0x1098090) == 0x1
        self.avd_w32(0x1400014, 0x0)

    def mcpu_boot(self, fw):
        if isinstance(fw, str):
            fw = open(fw, "rb").read()[:0xC000]
        else:
            fw = fw[:0xC000]
        self.avd_wbuf(0x1080000, fw)
        self.avd_mcpu_start()

    def mcpu_decode_init(self, fw):
        self.mcpu_boot(fw=fw)
        dump = """
        26908ee80: 00000000 00000000 00000000 00000000 04020002 00020002 04020002 04020002
        26908eea0: 04020002 00070007 00070007 00070007 00070007 00070007 04020002 00020002
        26908eec0: 04020002 04020002 04020002 00070007 00070007 00070007 00070007 00070007
        26908eee0: 04020002 02020202 04020002 04020002 04020202 00070007 00070007 00070007
        26908ef00: 00070007 00070007 00000000 00000000 00000000 00000000 00000000 00000000
        """
        for line in dump.strip().splitlines():
            offset = int(line.split()[0].replace(":", ""), 16)
            vals = line.split()[1:]
            for n, arg in enumerate(vals[:8]):
                self.avd_w32(offset + (n * 4) - self.base, int(arg, 16))
        self.avd_w32(0x1098054, 0x108EB30)

    def wrap_ctrl_device_init(self):
        avd_w32 = self.avd_w32
        avd_w32(0x1400014, 0x1)
        avd_w32(0x1400018, 0x1)
        avd_w32(0x1070000, 0x0)  # PIODMA cfg
        avd_w32(0x1104064, 0x3)
        avd_w32(0x110CC90, 0xFFFFFFFF)  # IRQ clear
        avd_w32(0x110CC94, 0xFFFFFFFF)  # IRQ clear
        avd_w32(0x110CCD0, 0xFFFFFFFF)  # IRQ clear
        avd_w32(0x110CCD4, 0xFFFFFFFF)  # IRQ clear
        avd_w32(0x110CAC8, 0xFFFFFFFF)  # IRQ clear
        avd_w32(0x1070024, 0x26907000)
        avd_w32(0x1400014, 0x0)  # idle thing

    def avd_dma_tunables_stage0(self):
        avd_w32 = self.avd_w32
        avd_r32 = self.avd_r32

        avd_w32(0x1070024, 0x26907000)
        avd_w32(0x1400000, 0x3)
        avd_w32(0x1104000, 0x0)
        avd_w32(0x110405C, 0x0)
        avd_w32(0x1104110, 0x0)
        avd_w32(0x11040F4, 0x1555)

        avd_w32(0x1100000, 0xC0000000)
        avd_w32(0x1101000, 0xC0000000)
        avd_w32(0x1102000, 0xC0000000)
        avd_w32(0x1103000, 0xC0000000)
        avd_w32(0x1104000, 0xC0000000)
        avd_w32(0x1105000, 0xC0000000)
        avd_w32(0x1106000, 0xC0000000)
        avd_w32(0x1107000, 0xC0000000)
        avd_w32(0x1108000, 0xC0000000)
        avd_w32(0x1109000, 0xC0000000)
        avd_w32(0x110A000, 0xC0000000)
        avd_w32(0x110B000, 0xC0000000)

        avd_w32(0x110C010, 0x1)
        avd_w32(0x110C018, 0x1)

        avd_w32(0x110C040, avd_r32(0x110C040) | 0xC0000000)
        avd_w32(0x110C080, avd_r32(0x110C080) | 0xC0000000)
        avd_w32(0x110C0C0, avd_r32(0x110C0C0) | 0xC0000000)
        avd_w32(0x110C100, avd_r32(0x110C100) | 0xC0000000)

        avd_w32(0x110C140, avd_r32(0x110C140) | 0xC0000000)
        avd_w32(0x110C180, avd_r32(0x110C180) | 0xC0000000)
        avd_w32(0x110C1C0, avd_r32(0x110C1C0) | 0xC0000000)
        avd_w32(0x110C200, avd_r32(0x110C200) | 0xC0000000)

        avd_w32(0x110C240, avd_r32(0x110C240) | 0xC0000000)
        avd_w32(0x110C280, avd_r32(0x110C280) | 0xC0000000)
        avd_w32(0x110C2C0, avd_r32(0x110C2C0) | 0xC0000000)
        avd_w32(0x110C300, avd_r32(0x110C300) | 0xC0000000)

        avd_w32(0x110C340, avd_r32(0x110C340) | 0xC0000000)
        avd_w32(0x110C380, avd_r32(0x110C380) | 0xC0000000)
        avd_w32(0x110C3C0, avd_r32(0x110C3C0) | 0xC0000000)
        avd_w32(0x110C400, avd_r32(0x110C400) | 0xC0000000)

        avd_w32(0x110C440, avd_r32(0x110C440) | 0xC0000000)
        avd_w32(0x110C480, avd_r32(0x110C480) | 0xC0000000)
        avd_w32(0x110C4C0, avd_r32(0x110C4C0) | 0xC0000000)
        avd_w32(0x110C500, avd_r32(0x110C500) | 0xC0000000)

        avd_w32(0x110C540, avd_r32(0x110C540) | 0xC0000000)
        avd_w32(0x110C580, avd_r32(0x110C580) | 0xC0000000)
        avd_w32(0x110C5C0, avd_r32(0x110C5C0) | 0xC0000000)
        avd_w32(0x110C600, avd_r32(0x110C600) | 0xC0000000)

        avd_w32(0x110C640, avd_r32(0x110C640) | 0xC0000000)
        avd_w32(0x110C680, avd_r32(0x110C680) | 0xC0000000)
        avd_w32(0x110C6C0, avd_r32(0x110C6C0) | 0xC0000000)
        avd_w32(0x110C700, avd_r32(0x110C700) | 0xC0000000)

        avd_w32(0x110C740, avd_r32(0x110C740) | 0xC0000000)
        avd_w32(0x110C780, avd_r32(0x110C780) | 0xC0000000)
        avd_w32(0x110C7C0, avd_r32(0x110C7C0) | 0xC0000000)
        avd_w32(0x110C800, avd_r32(0x110C800) | 0xC0000000)

        avd_w32(0x110C840, avd_r32(0x110C840) | 0xC0000000)
        avd_w32(0x110C880, avd_r32(0x110C880) | 0xC0000000)
        avd_w32(0x110C8C0, avd_r32(0x110C8C0) | 0xC0000000)
        avd_w32(0x110C900, avd_r32(0x110C900) | 0xC0000000)

        avd_w32(0x110C940, avd_r32(0x110C940) | 0xC0000000)
        avd_w32(0x110C980, avd_r32(0x110C980) | 0xC0000000)
        avd_w32(0x110C9C0, avd_r32(0x110C9C0) | 0xC0000000)
        avd_w32(0x110CA00, avd_r32(0x110CA00) | 0xC0000000)

        avd_w32(0x110CA40, avd_r32(0x110CA40) | 0xC0000000)
        avd_w32(0x110CA80, avd_r32(0x110CA80) | 0xC0000000)
        avd_w32(0x110CAC0, avd_r32(0x110CAC0) | 0xC0000000)
        avd_w32(0x110CB00, avd_r32(0x110CB00) | 0xC0000000)

        avd_w32(0x110CB40, avd_r32(0x110CB40) | 0xC0000000)
        avd_w32(0x110CB80, avd_r32(0x110CB80) | 0xC0000000)
        avd_w32(0x110CBC0, avd_r32(0x110CBC0) | 0xC0000000)
        avd_w32(0x110CC00, avd_r32(0x110CC00) | 0xC0000000)

        avd_w32(0x110CC40, avd_r32(0x110CC40) | 0xC0000000)
        avd_w32(0x110CC80, avd_r32(0x110CC80) | 0xC0000000)
        avd_w32(0x110CCC0, avd_r32(0x110CCC0) | 0xC0000000)
        avd_w32(0x110CD00, avd_r32(0x110CD00) | 0xC0000003)

        avd_w32(0x110C044, 0x40)
        avd_w32(0x110C084, 0x400040)
        avd_w32(0x110C244, 0x800034)
        avd_w32(0x110C284, 0x18)
        avd_w32(0x110C2C4, 0xB40020)
        avd_w32(0x110C3C4, 0xD40030)
        avd_w32(0x110C404, 0x180014)
        avd_w32(0x110C444, 0x104001C)
        avd_w32(0x110C484, 0x2C0014)
        avd_w32(0x110C4C4, 0x1200014)
        avd_w32(0x110C504, 0x400018)
        avd_w32(0x110C544, 0x1340024)
        avd_w32(0x110C584, 0x580014)
        avd_w32(0x110C5C4, 0x1580014)
        avd_w32(0x110C1C4, 0x6C0048)
        avd_w32(0x110C204, 0xB40048)
        avd_w32(0x110C384, 0xFC0038)
        avd_w32(0x110C604, 0x1340030)
        avd_w32(0x110C644, 0x16C00B0)
        avd_w32(0x110C684, 0x21C00B0)
        avd_w32(0x110C844, 0x164001C)
        avd_w32(0x110C884, 0x2CC0028)
        avd_w32(0x110C744, 0x1800018)
        avd_w32(0x110C784, 0x2F40020)
        avd_w32(0x110C7C4, 0x1980018)
        avd_w32(0x110C804, 0x314001C)
        avd_w32(0x110C8C4, 0x1B00024)
        avd_w32(0x110C904, 0x3300040)
        avd_w32(0x110C944, 0x1D4001C)
        avd_w32(0x110C984, 0x370002C)
        avd_w32(0x110C9C4, 0x1F00030)
        avd_w32(0x110CA04, 0x39C003C)
        avd_w32(0x110CA44, 0x2200014)
        avd_w32(0x110CA84, 0x3D80014)
        avd_w32(0x110CB04, 0x2340014)
        avd_w32(0x110CB44, 0x3EC0014)
        avd_w32(0x110CAC4, 0x2480080)
        avd_w32(0x110CC8C, 0x2C80014)
        avd_w32(0x110CCCC, 0x2DC0014)
        avd_w32(0x110CC88, 0x2F00060)
        avd_w32(0x110CCC8, 0x3500054)
        avd_w32(0x110CB84, 0x3A4001C)
        avd_w32(0x110CBC4, 0x4000040)
        avd_w32(0x110CC04, 0x3C00040)
        avd_w32(0x110CC44, 0x44000C0)

        avd_w32(0x110405C, avd_r32(0x110405C) | 0x500000)
        avd_w32(0x109807C, 0x1)
        avd_w32(0x1098080, 0xFFFFFFFF)

    def ioread(self, iova, size, stream=0):
        data = self.dart.ioread(stream, iova & 0xFFFFFFFFFF, size)
        return data

    def iowrite(self, iova, data, stream=0):
        self.dart.iowrite(stream, iova & 0xFFFFFFFFFF, data)

    def iomap_at(self, iova, phys, size, stream):
        self.dart.iomap_at(stream, iova & 0xFFFFFFFFFF, phys, size)

    def ioalloc_at(self, iova, size, stream=0, val=0):
        phys = self.u.heap.memalign(self.PAGE_SIZE, size)
        self.p.memset32(phys, val, size)
        self.dart.iomap_at(stream, iova & 0xFFFFFFFFFF, phys, size)

    def iowrite32(self, iova, val, stream=0):
        data = struct.pack("<I", val)
        self.dart.iowrite(stream, iova & 0xFFFFFFFFFF, data)

    def ioread32(self, iova, stream=0):
        data = self.dart.ioread(stream, iova & 0xFFFFFFFFFF, 0x4)
        return struct.unpack("<I", data)[0]
