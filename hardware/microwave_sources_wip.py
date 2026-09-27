"""
This file is part of pi3diamond.

pi3diamond is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pi3diamond is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with diamond. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2009-2011 Helmut Fedder <helmut.fedder@gmail.com>
"""

import logging
import time

import numpy
import pyvisa as visa

from .labbrick_driver.labbrick import *

SWEEP_SINGLE = 0
SWEEP_REPEAT = 1

SWEEP_DOWN = 0
SWEEP_UP = 1


class LabBrick():
    trigger_from_ni = False

    def __init__(self, name='LSG-402'):
        fnLSG_SetTestMode(0)
        N = fnLSG_GetNumDevices()
        # print "found %d labbricks"%N
        self.devs = numpy.zeros(N, dtype=numpy.uint32)
        fnLSG_GetDevInfo(self.devs)
        self.names = []
        for dev in self.devs:
            name = fnLSG_GetModelName(int(dev))[1]
            self.names.append(name)
            # print "found labbrick model " + (fnLSG_GetModelName(dev)[1])
        try:
            self.dev = int(self.devs[self.names.index(name)])
            self.name = name
        except:
            self.dev = -1
            print("labbrick device" + name + " not present, opening dummy generator\n")
            raise
            return None
        fnLSG_InitDevice(self.dev)
        self.max_power = fnLSG_GetMaxPwr(self.dev)
        self.Off()
        # self.setOutput(-40, 3e9)

    def __del__(self):
        self.Power(-40)
        fnLSG_SaveSettings(self.dev)
        fnLSG_CloseDevice(self.dev)
        return

    def Off(self):
        # fnLSG_SetRFOn(self.dev, 0)
        self.setPower(-40)
        return 'off'

    def On(self):
        fnLSG_SetRFOn(self.dev, 1)
        return 'on'

    def Power(self, power=None):
        if power != None:
            self.setPower(power)
            self.On()
        else:
            self.setPower(-40)
            self.Off()
        return .25 * (40 - fnLSG_GetPowerLevel(self.dev))

    def setPower(self, power):
        fnLSG_SetPowerLevel(self.dev, power / .25)

    def setOutput(self, power, frequency):
        self.Power(power)
        self.Freq(frequency)

    def Freq(self, f=None):
        if f != None:
            fnLSG_SetFrequency(self.dev, int(f / 1e5))
        return fnLSG_GetFrequency(self.dev) * 1e5

    def CW(self, f=None, power=None):
        fnLSG_StartSweep(self.dev, 0);  # stop all running sweeps
        if power != None:
            self.Power(power)
        if f != None:
            self.Freq(f)

    def Sweep(self, f_start, f_stop, df, dt=20):
        usbdelay = .01  # seconds
        # print "setting start frequency"
        time.sleep(usbdelay)
        fnLSG_SetStartFrequency(self.dev, int(f_start / 1e5))
        # print "setting end frequency"
        time.sleep(usbdelay)
        fnLSG_SetEndFrequency(self.dev, int(f_stop / 1e5))
        # print "setting frequency step "
        time.sleep(usbdelay)
        fnLSG_SetFrequencyStep(self.dev, int(df / 1e5))
        # print "setting dwell time"
        time.sleep(usbdelay)
        fnLSG_SetDwellTime(self.dev, dt)
        # print "setting sweep mode"
        time.sleep(usbdelay)
        fnLSG_SetSweepMode(self.dev, SWEEP_SINGLE);
        # print "setting sweep direction"
        time.sleep(usbdelay)
        fnLSG_SetSweepDirection(self.dev, SWEEP_UP)
        # print "starting sweep ..."
        time.sleep(usbdelay)
        fnLSG_StartSweep(self.dev, 1);
        # print "sweep running"

    def initSweep(self, frequency, power):
        self.f_start = frequency[0]
        self.f_stop = frequency[-1]
        self.df = len(frequency)

    def resetListPos(self):
        self.Sweep(self.f_start, self.f_stop, self.df)

    setFrequency = Freq
    getFrequency = Freq
    getPower = Power


class SMIQ():
    """Provides control of SMIQ family microwave sources from Rhode und Schwarz with GPIB via visa."""
    _output_threshold = -90.0

    def __init__(self, visa_address='GPIB0::28'):
        self.visa_address = visa_address

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            try:  # silently ignore possible exceptions raised by del
                del self.instr
            except Exception:
                pass
            self.instr = visa.instrument(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = visa.instrument(self.visa_address)
            val = self.instr.ask(str)
        return val

    def getPower(self):
        return float(self._ask(':POW?'))

    def setPower(self, power):
        if power is None or power < self._output_threshold:
            logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' turning off.')
            self._write(':FREQ:MODE CW')
            self._write(':OUTP OFF')
            return
        logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' setting power to ' + str(power))
        self._write(':FREQ:MODE CW')
        self._write(':POW %f' % float(power))
        self._write(':OUTP ON')

    def getFrequency(self):
        return float(self._ask(':FREQ?'))

    def setFrequency(self, frequency):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ %e' % frequency)

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def initSweep(self, frequency, power):
        if len(frequency) != len(power):
            raise ValueError('Length mismatch between list of frequencies and list of powers.')
        self._write(':FREQ:MODE CW')
        self._write(':LIST:DEL:ALL')
        self._write('*WAI')
        self._write(":LIST:SEL 'ODMR'")
        FreqString = ''
        for f in frequency[:-1]:
            FreqString += ' %f,' % f
        FreqString += ' %f' % frequency[-1]
        self._write(':LIST:FREQ' + FreqString)
        self._write('*WAI')
        PowerString = ''
        for p in power[:-1]:
            PowerString += ' %f,' % p
        PowerString += ' %f' % power[-1]
        self._write(':LIST:POW' + PowerString)
        self._write(':LIST:LEAR')
        self._write(':TRIG1:LIST:SOUR EXT')
        # we switch frequency on negative edge. Thus, the first square pulse of the train
        # is first used for gated count and then the frequency is increased. In this way
        # the first frequency in the list will correspond exactly to the first acquired count. 
        self._write(':TRIG1:SLOP NEG')
        self._write(':LIST:MODE STEP')
        self._write(':FREQ:MODE LIST')
        self._write('*WAI')
        N = int(numpy.round(float(self._ask(':LIST:FREQ:POIN?'))))
        if N != len(frequency):
            raise RuntimeError('Error in SMIQ with List Mode')

    def resetListPos(self):
        self._write(':ABOR:LIST')
        self._write('*WAI')


class GTX():
    """Provides control of gigatronics family microwave sources from toby with GPIB via visa."""
    _output_threshold = -90.0

    def __init__(self, visa_address='GPIB0::6'):
        self.visa_address = visa_address

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            try:  # silently ignore possible exceptions raised by del
                del self.instr
            except Exception:
                pass
            self.instr = visa.instrument(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = visa.instrument(self.visa_address)
            val = self.instr.ask(str)
        return val

    def getPower(self):
        return float(self._ask(':POW?'))

    def setPower(self, power):
        if power is None or power < self._output_threshold:
            logging.getLogger().debug('gtx at ' + str(self.visa_address) + ' turning off.')
            self._write(':MODE CW')
            self._write(':OUTP OFF')
            return
        logging.getLogger().debug('gtx at ' + str(self.visa_address) + ' setting power to ' + str(power))
        self._write(':MODE CW')
        self._write(':POW %f DBM' % float(power))
        self._write(':OUTP ON')

    def getFrequency(self):
        return float(self._ask(':FREQ?'))

    def setFrequency(self, frequency):
        self._write(':MODE CW')
        self._write(':FREQ %e' % frequency)

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def initSweep(self, frequency, power):
        if len(frequency) != len(power):
            raise ValueError('Length mismatch between list of frequencies and list of powers.')
        self._write(':OUTP OFF')
        self._write(':MODE LIST')
        self._write(':LIST:SEQ:AUTO ON')
        self._write(':LIST:DEL:LIST 1')
        FreqString = ''
        for f in frequency[:-1]:
            FreqString += ' %f,' % f
        FreqString += ' %f' % frequency[-1]
        self._write(':LIST:FREQ' + FreqString)
        PowerString = ''
        for p in power[:-1]:
            PowerString += ' %f,' % p
        PowerString += ' %f' % power[-1]
        self._write(':LIST:POW' + PowerString)
        self._write(':LIST:DWEL' + ' %f' % 0.3)
        self._write(':LIST:PREC 1')
        self._write(':LIST:REP STEP')
        self._write(':TRIG:SOUR EXT')
        self._write(':OUTP ON')
        N = int(numpy.round(float(self._ask(':LIST:FREQ:POIN?'))))
        if N != len(frequency):
            raise RuntimeError('Error in SMIQ with List Mode')

    def resetListPos(self):
        pass
        # self._write(':ABOR:LIST')
        # self._write('*WAI')


class SMR20():
    """Provides control of SMR20 microwave source from Rhode und Schwarz with GPIB via visa."""
    _output_threshold = -90.0

    def __init__(self, visa_address='GPIB0::29'):
        self.visa_address = visa_address

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            try:  # silently ignore possible exceptions raised by del
                del self.instr
            except Exception:
                pass
            self.instr = visa.instrument(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = visa.instrument(self.visa_address)
            val = self.instr.ask(str)
        return val

    def getPower(self):
        return float(self._ask(':POW?'))

    def setPower(self, power):
        if power is None or power < self._output_threshold:
            self._write(':OUTP OFF')
            return
        self._write(':FREQ:MODE CW')
        self._write(':POW %f' % float(power))
        self._write(':OUTP ON')

    def getFrequency(self):
        return float(self._ask(':FREQ?'))

    def setFrequency(self, frequency):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ %e' % frequency)

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def initSweep(self, frequency, power):
        if len(frequency) != len(power):
            raise ValueError('Length mismatch between list of frequencies and list of powers.')
        self._write(':FREQ:MODE CW')
        self._write(':LIST:DEL:ALL')
        self._write('*WAI')
        self._write(":LIST:SEL 'ODMR'")
        FreqString = ''
        for f in frequency[:-1]:
            FreqString += ' %f,' % f
        FreqString += ' %f' % frequency[-1]
        self._write(':LIST:FREQ' + FreqString)
        self._write('*WAI')
        PowerString = ''
        for p in power[:-1]:
            PowerString += ' %f,' % p
        PowerString += ' %f' % power[-1]
        self._write(':LIST:POW' + PowerString)
        self._write(':TRIG1:LIST:SOUR EXT')
        self._write(':TRIG1:SLOP NEG')
        self._write(':LIST:MODE STEP')
        self._write(':FREQ:MODE LIST')
        self._write('*WAI')
        N = int(numpy.round(float(self._ask(':LIST:FREQ:POIN?'))))
        if N != len(frequency):
            raise RuntimeError('Error in SMIQ with List Mode')

    def resetListPos(self):
        self._write(':ABOR:LIST')
        self._write('*WAI')


from .nidaq import SquareWave


class HybridMicrowaveSourceSMIQNIDAQ():
    """Provides a microwave source that can do frequency sweeps
    with pixel clock output using SMIQ and nidaq card."""

    def __init__(self, visa_address, square_wave_device):
        self.source = SMIQ(visa_address)
        self.square_wave = SquareWave(square_wave_device)

    def setOutput(self, power, frequency, seconds_per_point=1e-2):
        """Sets the output of the microwave source.
        'power' specifies the power in dBm. 'frequency' specifies the
        frequency in Hz. If 'frequency' is a single number, the source
        is set to cw. If 'frequency' contains multiple values, the
        source sweeps over the frequencies. 'seconds_per_point' specifies
        the time in seconds that the source spends on each frequency step.
        A sweep is excecute by the 'doSweep' method."""

        # in any case set the CW power
        self.source.setPower(power)
        self.square_wave.setTiming(seconds_per_point)

        try:
            length = len(frequency)
        except TypeError:
            length = 0

        self._length = length

        if length:
            self.source.setFrequency(frequency[0])
            self.source.initSweep(frequency, power * numpy.ones(length))
        else:
            self.source.setFrequency(frequency)

    def doSweep(self):
        """Perform a single sweep."""
        if not self._length:
            raise RuntimeError('Not in sweep mode. Change to sweep mode and try again.')
        # self.source.resetListPos()
        self.square_wave.setLength(self._length)
        self.square_wave.output()


class SMBV100A():
    """Provides control of SMBV100A family microwave sources from Rhode und Schwarz via visa."""
    _output_threshold = -90.0

    def __init__(self, visa_address='GPIB0::28'):
        self.visa_address = visa_address

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            self.instr = visa.instrument(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = visa.instrument(self.visa_address)
            val = self.instr.ask(str)
        return val

    def getPower(self):
        return float(self._ask(':POW?'))

    def setPower(self, power):
        if power is None or power < self._output_threshold:
            logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' turning off.')
            self._write(':FREQ:MODE CW')
            self._write(':OUTP OFF')
            return
        logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' setting power to ' + str(power))
        self._write(':FREQ:MODE CW')
        self._write(':POW %f' % float(power))
        self._write(':OUTP ON')

    def getFrequency(self):
        return float(self._ask(':FREQ?'))

    def setFrequency(self, frequency):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ %e' % frequency)

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def initSweep(self, frequency, power):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ:STAR %f' % frequency[0])
        self._write(':FREQ:STOP %f' % frequency[-1])
        self._write(':SWE:SPAC LIN')
        self._write(':SWE:POIN %i' % (len(frequency)))
        self._write(':SWE:DWEL 16 ms')
        self._write(':SWE:MODE STEP')
        self._write(':SYST:DISP:UPD OFF')
        self._write(':INP:TRIG:SLOP NEG')
        self._write(':TRIG:FSW:SOUR EXT')
        self._write(':FREQ:MODE SWE')
        self._write('*OPC?')

    def resetListPos(self):
        self._write(':SWE:RES')


class SMBV100AIQ():
    """
    Provides control of SMBV100A family microwave sources from Rhode und Schwarz via visa. 
    It also should allow access to the IQ-Function of the SMBV100A\
    """
    _output_threshold = -90.0

    def __init__(self, visa_address):  # , visa_address='GPIB0::28'):
        self.visa_address = visa_address

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            try:  # silently ignore possible exceptions raised by del
                del self.instr
            except Exception:
                pass
            self.instr = visa.instrument(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = visa.instrument(self.visa_address)
            val = self.instr.ask(str)
        return val

    def getPower(self):
        return float(self._ask(':POW?'))

    def setPower(self, power):
        if power is None or power < self._output_threshold:
            logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' turning off.')
            self._write(':FREQ:MODE CW')
            self._write(':OUTP OFF')
            return
        logging.getLogger().debug('SMIQ at ' + str(self.visa_address) + ' setting power to ' + str(power))
        self._write(':FREQ:MODE CW')
        self._write(':POW %f' % float(power))
        self._write(':OUTP ON')

    def getFrequency(self):
        return float(self._ask(':FREQ?'))

    def setFrequency(self, frequency):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ %e' % frequency)

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def initSweep(self, frequency, power):
        self._write(':FREQ:MODE CW')
        self._write(':FREQ:STAR %f' % frequency[0])
        self._write(':FREQ:STOP %f' % frequency[-1])
        self._write(':SWE:SPAC LIN')
        self._write(':SWE:POIN %i' % (len(frequency)))
        self._write(':SWE:DWEL 16 ms')
        self._write(':SWE:MODE STEP')
        self._write(':SYST:DISP:UPD OFF')
        self._write(':INP:TRIG:SLOP NEG')
        self._write(':TRIG:FSW:SOUR EXT')
        self._write(':FREQ:MODE SWE')
        self._write('*OPC?')

    def resetListPos(self):
        self._write(':SWE:RES')

    def set_iq(self, state):
        """Enables or disables IQ modulation"""
        if state:
            self._write(':IQ:STAT ON')
        else:
            self._write(':IQ:STAT OFF')

    def get_iq(self):
        return self._ask(':IQ:STAT?')

    def set_iq_swap(self, state):
        """Swaps between adding or subtracting both channels. I think the standard is adding"""
        if state:
            self._write(':IQ:SWAP ON')
        else:
            self._write(':IQ:SWAP OFF')

    def get_iq_swap(self):
        return self._ask(':IQ:SWAP?')

    def set_iq_input(self, source='ANAL'):
        if source == 'BAS':
            self._write(':IQ:SOUR BAS')
        elif source == 'ANAL':
            self._write(':IQ:SOUR ANAL')
            print('selectInputIQ ' + source)
        elif source == 'DIFF':
            self._write(':IQ:SOUR DIFF')
            print('selectInputIQ ' + source)
        else:
            raise ValueError(
                'The source has to be either BASeline, ANALog or DIFFerential.\n use the capital letters.  IF none is select, the ANALog input is used')

    def set_iq_impairment(self, state):
        """This Function enables or disables the impairment of the IQ"""
        if state:
            self._write(':IQ:IMP ON')
        else:
            self._write(':IQ:IMP OFF')

    def get_iq_impairment(self):
        return self._ask(':IQ:IMP?')

    def set_iq_impairment_crest_factor(self, crest):
        """This command specifies the crest factor of the external analog signal"""
        self._write(':IQ:CRES ' + str(crest))

    def set_iq_impairment_magnitude(self, magn=0):
        """This command sets the ratio of I modulation to Q modulation"""
        self._write(':IQ:IMP:IQR') + str(magn)

    def set_iq_impairment_leakage(self, channel='I', offset=0.0):
        """This command sets the carrier offset for the channel modulation to the other channel's modulation (amplification Imbalance) """
        if offset > 10.0 or offset < -10.0:
            raise ValueError('The offset has to be in the range of [-10.:10.]. The offset is given in an percent.')
        if channel == 'I':
            self._write(':IQ:IMP:LEAK:I ' + str(offset) + 'PCT')
        elif channel == 'Q':
            self._write(':IQ:IMP:LEAK:Q ' + str(offset) + 'PCT')
        else:
            raise ValueError("The variable for the channel has either to be 'I' or 'Q' everything else won't work.")

    def set_iq_impairment_quadrature_offset(self, offset=0.0):
        """This command sets the QUADrature offset for the IQ modulation"""
        if (offset < 10.) and (offset > -10.):
            self._write(':IQ:IMP:QUAD:ANGL ' + str(offset) + 'DEG')
        else:
            raise ValueError('The quadrature offset has to be in the range of -10 to 10 degrees.')

    def set_iq_gain_imbalance(self, imbalance=0.0):
        """This command sets the imbalance between the I and the Q vextor. The entry is made in dB. Positive values mean that Q is more amplified than I and negative ones state that Q is more amplified than I"""
        if imbalance <= -1. or imbalance >= 1.:
            raise ValueError("The range of the gain imbalance is [-1:1]. Values given in dB")
        self._write('IQ:IMP:IQR:MAGN ' + str(imbalance) + 'dB')

    def get_iq_gain_imbalance(self):
        return float(microwave._ask(':IQ:IMP:IQR:MAGN?'))


if __name__ == '__main__':
    microwave = LabBrick('LSG-402')
