#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from m1n1.hw.pmu import PMU
from m1n1.setup import *

PMU(u).reset_panic_counter()
