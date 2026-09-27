import pyvisa as visa


class DanFysik:

    def __init__(self, device='GPIB0::7::INSTR', limit_current=10.0, maximum_current=20.0):
        self.maximum_current = maximum_current
        self.limit_current = limit_current
        instr = visa.instrument(device)
        instr.timeout = 1.0
        instr.term_chars = '\r'
        self.instr = instr

    def set_current(self, current):
        """Sets the current in Ampere."""
        if current > self.limit_current:
            raise ValueError('Limit current exceeded.')
        ppm = int(current / self.maximum_current * 1000000)
        if (ppm == 0):
            self.instr.write('DA 0,%i' % ppm)
            self.instr.write('F')
        else:
            self.instr.write('DA 0,%i' % ppm)
            self.instr.write('N')

    def get_current(self):
        s = self.instr.ask('DA 0')
        return float(s.split()[1]) * 1e-6 * self.maximum_current
