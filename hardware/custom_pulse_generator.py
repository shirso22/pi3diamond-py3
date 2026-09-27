from .pulse_generator import PulseGenerator


class CustomPulseGenerator(PulseGenerator):

    def Light(self):
        # ORANGE-LASER: aom2 (channel 8) gates the 594 nm Cobolt.
        self.setContinuous(['aom', 'aom2'])

    def Open(self):
        # ORANGE-LASER: aom2 (channel 8) gates the 594 nm Cobolt.
        self.setContinuous(['aom', 'mw', 'aom2'])

    def Night(self):
        self.setContinuous([])

    Sequence = PulseGenerator.setSequence
