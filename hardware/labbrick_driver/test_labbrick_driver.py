# PY3-PORT: pasted shell command, not Python. cd
# PY3-PORT: pasted shell command, not Python. d: / software / pi3diamond / hardware /

# PY3-PORT: implicit relative import across packages; 2to3 only rewrites siblings.
from hardware.microwave_sources import *

lb = labbrick()
lb.Sweep(2.4e9, 3e9, 1e6)

# PY3-PORT: pasted shell command, not Python. cd
# PY3-PORT: pasted shell command, not Python. d: / software / pi3diamond / hardware / labbrick_driver
from . import labbrick
import numpy

dev = 1
labbrick.fnLSG_SetTestMode(0)
N = labbrick.fnLSG_GetNumDevices()
devs = numpy.zeros(N, dtype=numpy.uint32)
labbrick.fnLSG_GetDevInfo(devs)
dev = int(devs[0])
labbrick.fnLSG_InitDevice(dev)
labbrick.fnLSG_GetPowerLevel(dev)
