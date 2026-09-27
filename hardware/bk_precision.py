"""
requires NI-VISA runtime libraries
"""

import numpy as np
import pyvisa as visa

"""
calibrating output voltage with 0 Ohm load attached

BK 5042     output

calibration = [[50, 106],
               [100, 182],
               [200, 351],
               [300, 523],
               [500, 871],
               [800, 1386],
               [1000, 1767],
               [1200, 2118],
               [1500, 2636],
               [1800, 3111],
               [2000, 3479],
               [2200, 3818],
               [2500, 4299],
               ]
               
conclusion: the gain drops approximately linearly to about 1.7 instead of 2.
"""


class BK4052():
    """
    RF source based on a BK 4052 AWG followed by an ADA 4870
    eval board with gain 2.0 and built in 4.99 Ohm output load.
    """

    def __init__(self, device='USB0::0xF4ED::0xEE3A::388L13139::INSTR', load=5., gain=2.0, max_current=0.5):
        self.device = device
        self.load = load
        self.gain = gain
        self.max_current = max_current

    def _connect(self):
        self.instr = visa.instrument(self.device)

    def _disconnect(self):
        self.instr.close()

    def _write(self, string):
        self._connect()
        self.instr.write(string)
        self._disconnect()

    def _ask(self, string):
        self._connect()
        answer = self.instr.ask(string)
        self._disconnect()
        return answer

    def reset(self):
        self._write('C1:OUTP OFF,LOAD,50')
        self._write('C1:BSWV WVTP,SINE,FRQ,1.000e+06HZ,AMP,0.004V,OFST,0V,PHSE,0')

    def getVpp(self):
        """Return the peak-to-peak voltage."""
        answer = self._ask('C1:OUTP?')
        if 'OFF' in answer:
            return 0.0
        answer = self._ask('C1:BSWV?')
        answer = answer[answer.find('AMP') + 4:]
        answer = answer[:answer.find('V')]
        v_pp = float(answer)
        return v_pp

    def setVpp(self, v_pp):
        """
        Set the peak-to-peak voltage. The output is turned off,
        if below the smallest possible value of 0.004 V.
        """
        self._write(':FREQ:MODE CW')
        if v_pp < 0.004:
            self._write('C1:OUTP OFF')
        elif v_pp > 6:
            raise ValueError('Voltage exceeds maximum value of 6V.')
        else:
            self._write('C1:BSWV AMP,%fV' % (v_pp))
            self._write('C1:OUTP ON')

    def getVrms(self):
        """Get the rms voltage."""
        return self.getVpp() * 2 ** -1.5

    def setVrms(self, v_rms):
        """Set the rms voltage."""
        self.setVpp(v_rms * 2 ** 1.5)

    def getPower(self):
        """Returns the power in dBm based on the load set beforehand."""
        volt = self.getVrms() * self.gain
        watt = volt ** 2 / self.load
        dBm = 10 * np.log10(watt * 1000)
        return dBm

    def getCurrent(self):
        """Returns the current in amps based on the load set beforehand."""
        volt = self.getVrms() * self.gain
        current = volt / self.load
        return current

    def setCurrent(self, amps):
        """Sets the current in amps based on the load set beforehand."""
        if amps > self.max_current:
            raise ValueError('Maximum output current of ' + str(self.max_current) + ' A exceeded.')
        volt = self.load * amps / self.gain
        self.setVrms(volt)

    def setPower(self, dBm):
        """Sets the power in dBm based on the load set beforehand."""
        watt = 1e-3 * 10 ** (dBm / 10.)
        current = (watt / self.load) ** 0.5
        if current > self.max_current:
            raise ValueError('Maximum output current of ' + str(self.max_current) + ' A exceeded.')
        volt = (watt * self.load) ** 0.5 / self.gain
        self.setVrms(volt)

    def getFrequency(self):
        """Returns the frequency in Hz."""
        answer = self._ask('C1:BSWV?')
        answer = answer[answer.find('FRQ') + 4:]
        answer = answer[:answer.find('HZ')]
        return float(answer)

    def setFrequency(self, frequency):
        """Sets the frequency in Hz."""
        self._write('C1:BSWV FRQ, %eHZ' % frequency)

    def setOutput(self, power, frequency):
        """Sets the power in dBm and frequency in Hz."""
        self.setPower(power)
        self.setFrequency(frequency)


if __name__ == '__main__':
    bk = BK4052()


    def test():
        bk.setVpp(1)
        for f in np.linspace(1e6, 3e6, 201):
            print(f)
            bk.setVpp(f * 1e-6)
            bk.setFrequency(f)
