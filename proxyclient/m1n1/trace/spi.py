# SPDX-License-Identifier: MIT

from ..hv import TraceMode
from ..hw.spi import *
from ..utils import *
from . import ADTDevTracer


class SPITracer(ADTDevTracer):
    REGMAPS = [SPIRegs]
    NAMES = ["spi"]
