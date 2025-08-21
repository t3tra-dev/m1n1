# SPDX-License-Identifier: MIT
from enum import IntEnum

from ..utils import *

__all__ = ["SGXRegs", "SGXRegsT602X", "SGXInfoRegs", "agx_decode_unit", "R_FAULT_INFO"]


class FAULT_REASON(IntEnum):
    INVALID = 0
    AF_FAULT = 1
    WRITE_ONLY = 2
    READ_ONLY = 3
    NO_ACCESS = 4
    UNK = 5


class R_FAULT_INFO(Register64):
    ADDR = 63, 30
    SIDEBAND = 29, 23
    CONTEXT = 22, 17
    UNIT = 16, 9
    LEVEL = 8, 7
    UNK_5 = 6, 5
    READ = 4
    REASON = 3, 1, FAULT_REASON
    FAULTED = 0


class SGXRegs(RegMap):
    FAULT_INFO = 0x17030, R_FAULT_INFO


class SGXRegsT602X(RegMap):
    FAULT_INFO = 0xD8C0, R_FAULT_INFO
    FAULT_ADDR = 0xD8C8, Register64


class SGXInfoRegs(RegMap):
    CORE_MASK_0 = (
        0x1500,
        Register32,
    )
    CORE_MASK_1 = (
        0x1514,
        Register32,
    )

    ID_00 = (
        0x4000,
        Register32,
    )
    ID_04 = (
        0x4004,
        Register32,
    )
    ID_08 = (
        0x4008,
        Register32,
    )
    ID_0c = (
        0x400C,
        Register32,
    )
    ID_10 = (
        0x4010,
        Register32,
    )
    ID_14 = (
        0x4014,
        Register32,
    )
    ID_18 = (
        0x4018,
        Register32,
    )
    ID_1c = (
        0x401C,
        Register32,
    )

    ID_8024 = (
        0x8024,
        Register32,
    )


class UNIT_00(IntEnum):
    DCMPn = 0x00  # VDM/PDM/CDM
    UL1Cn = 0x01  # VDM/PDM/CDM
    CMPn = 0x02  # VDM/PDM/CDM
    GSL1_n = 0x03  # VDM/PDM/CDM
    IAPn = 0x04  # VDM/PDM/CDM
    VCEn = 0x05  # VDM
    TEn = 0x06  # VDM
    RASn = 0x07  # VDM
    VDMn = 0x08  # VDM
    PPPn = 0x09  # VDM
    IPFn = 0x0A  # PDM
    IPF_CPFn = 0x0B  # PDM
    VFn = 0x0C  # PDM
    VF_CPFn = 0x0D  # PDM
    ZLSn = 0x0E  # PDM


class UNIT_A0(IntEnum):
    dPM = 0xA1  # VDM/PDM/CDM
    dCDM_KS0 = 0xA2  # CDM
    dCDM_KS1 = 0xA3  # CDM
    dCDM_KS2 = 0xA4  # CDM
    dIPP = 0xA5  # PDM
    dIPP_CS = 0xA6  # PDM
    dVDM_CSD = 0xA7  # VDM
    dVDM_SSD = 0xA8  # VDM
    dVDM_ILF = 0xA9  # VDM
    dVDM_ILD = 0xAA  # VDM
    dRDE0 = 0xAB  # VDM/PDM/CDM
    dRDE1 = 0xAC  # VDM/PDM/CDM
    FC = 0xAD  # VDM/PDM/CDM
    GSL2 = 0xAE  # VDM/PDM/CDM

    GL2CC_META0 = 0xB0  # VDM/PDM/CDM
    GL2CC_META1 = 0xB1  # VDM/PDM/CDM
    GL2CC_META2 = 0xB2  # VDM/PDM/CDM
    GL2CC_META3 = 0xB3  # VDM/PDM/CDM
    GL2CC_META4 = 0xB4  # VDM/PDM/CDM
    GL2CC_META5 = 0xB5  # VDM/PDM/CDM
    GL2CC_META6 = 0xB6  # VDM/PDM/CDM
    GL2CC_META7 = 0xB7  # VDM/PDM/CDM
    GL2CC_MB = 0xB8  # VDM/PDM/CDM


class UNIT_D0_T602X(IntEnum):
    gCDM_CS = 0xD0  # CDM
    gCDM_ID = 0xD1  # CDM
    gCDM_CSR = 0xD2  # CDM
    gCDM_CSW = 0xD3  # CDM
    gCDM_CTXR = 0xD4  # CDM
    gCDM_CTXW = 0xD5  # CDM
    gIPP = 0xD6  # PDM
    gIPP_CS = 0xD7  # PDM
    gKSM_RCE = 0xD8  # VDM/PDM/CDM


class UNIT_E0_T602X(IntEnum):
    gPM_SPn = 0xE0  # VDM/PDM/CDM
    gVDM_CSD_SPn = 0xE1  # VDM
    gVDM_SSD_SPn = 0xE2  # VDM
    gVDM_ILF_SPn = 0xE3  # VDM
    gVDM_TFP_SPn = 0xE4  # VDM
    gVDM_MMB_SPn = 0xE5  # VDM
    gRDE_SPn = 0xE6  # VDM/PDM/CDM


class UNIT_E0_T8103(IntEnum):
    gPM_SPn = 0xE0  # VDM/PDM/CDM
    gVDM_CSD_SPn = 0xE1  # VDM
    gVDM_SSD_SPn = 0xE2  # VDM
    gVDM_ILF_SPn = 0xE3  # VDM
    gVDM_TFP_SPn = 0xE4  # VDM
    gVDM_MMB_SPn = 0xE5  # VDM
    gCDM_CS_SPn_KS0 = 0xE6  # CDM
    gCDM_CS_SPn_KS1 = 0xE7  # CDM
    gCDM_CS_SPn_KS2 = 0xE8  # CDM
    gCDM_SPn_KS0 = 0xE9  # CDM
    gCDM_SPn_KS1 = 0xEA  # CDM
    gCDM_SPn_KS2 = 0xEB  # CDM
    gIPP_SPn = 0xEC  # PDM
    gIPP_CS_SPn = 0xED  # PDM
    gRDE0_SPn = 0xEE  # VDM/PDM/CDM
    gRDE1_SPn = 0xEF  # VDM/PDM/CDM


def agx_decode_unit(v):
    if v < 0xA0:
        group = v >> 4
        return UNIT_00(v & 0x0F).name.replace("n", str(group))
    elif v < 0xD0:
        return UNIT_A0(v).name
    elif v < 0xE0:
        return UNIT_D0_T602X(v).name
    else:
        group = (v >> 4) & 1
        return UNIT_E0_T8103(v & 0xEF).name.replace("n", str(group))
