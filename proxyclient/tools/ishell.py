#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from m1n1.ishell import run_ishell
from m1n1.setup import *

run_ishell(globals(), msg="Have fun!")
