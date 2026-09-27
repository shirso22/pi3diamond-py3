"""
Provide pulse generation with DTG and custom pulse generator as bypass
"""

import numpy as np


class CombinedPulser():

    def __init__(self, dtg, fpga, microwave):
        self.dtg = dtg
        self.fpga = fpga
        self.microwave = microwave

    def Sequence(self, sequence, repeat=np.inf):
        self.microwave.set_iq(True)
        self.fpga.enableFanout()
        self.dtg.Sequence(sequence, repeat)

    def Light(self):
        self.dtg.Off()
        self.fpga.pullupFanout()
        self.microwave.set_iq(True)

    def Night(self):
        self.dtg.Off()
        self.fpga.enableFanout()
        self.microwave.set_iq(True)

    def Open(self):
        self.microwave.set_iq(False)
        self.fpga.pullupFanout()

    def checkUnderflow(self):
        return False
