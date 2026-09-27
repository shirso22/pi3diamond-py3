from .pulse_generator import PulseGenerator


class Pulser(PulseGenerator):
    """Adds compatibility code to the FPGA PulseGenerator"""

    def Sequence(self, sequence, loop=True):
        self.setSequence(sequence, loop=loop)

    def Night(self):
        self.setContinuous(0x0000)

    def Light(self):
        self.setContinuous(0x0001)

    def Open(self):
        self.setContinuous(0xffff)
