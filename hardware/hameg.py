'''
Created on 20.04.2012

author: Helmut Fedder
'''

import operator
import time

import numpy as np
from functools import reduce


# helper class to represent a visa instrument via a socket
class SocketInstrument():
    def __init__(self, device):
        import socket
        host, port = device.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        self.sock = sock

    def write(self, cmd):
        """Sends a command over the socket"""
        # HW-FIX: sendall() takes bytes in Python 3.
        cmd_string = cmd + '\n'
        if isinstance(cmd_string, str):
            cmd_string = cmd_string.encode('ascii')
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        time.sleep(
            .1)  # add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question):
        """sends the question and receives the answer"""
        # HW-FIX: recv() returns bytes; callers do float(...) on the result.
        self.write(question)
        answer = self.sock.recv(2048)  # 2000
        if isinstance(answer, bytes):
            answer = answer.decode('ascii', 'replace')
        return answer[:-1]

    def close(self):
        self.sock.close()


class HMP2030():

    def __init__(self, device, voltage_max=32.0, current_max=5.0, fuse_voltage_max=32.0, fuse_current_max=5.0,
                 reset=True):
        """
        Provides communication with a HMP2030 power supply
        via USB (virtual COM) or LAN.
        
        Usage Examples:
        
            hmp = HMP2030('ASRL11::INSTR')
            hmp = HMP2030('169.254.10.10:50000')
        
        Parameters:
        
            device:        string that describes the device (see examples above)
            
        Optional Parameters:
            voltage_max:   maximum allowed voltage
            current_max:   maximum allowed current
            fuse_voltage_max:    maximum allowed fuse voltage
            fuse_current_max:    maximum allowed fuse current
        """
        if '::' in device:
            self._connect_serial(device)
        else:
            self._connect_lan(device)

        self.voltage_max = voltage_max
        self.current_max = current_max
        self.fuse_voltage_max = fuse_voltage_max
        self.fuse_current_max = fuse_current_max
        self.instr.write('SYST:REM')  # sets the instrument to remote control
        if reset:
            self.reset()

    def _connect_serial(self, device):
        # HW-FIX: visa.instrument() was removed in pyvisa 1.6, and the address
        # was hard-coded to ASRL11 regardless of the `device` argument passed
        # in. Also: pyvisa timeouts are in MILLISECONDS, so `timeout = 1.0`
        # meant 1 ms, not 1 s -- every read would have timed out.
        import pyvisa as visa
        rm = visa.ResourceManager()
        instr = rm.open_resource(device)
        instr.read_termination = '\n'
        instr.write_termination = '\n'
        instr.chunk_size = 4096
        instr.timeout = 1000.0  # ms
        self.instr = instr

    def _connect_lan(self, device):
        """connects to the hameg powersupply"""
        self.instr = SocketInstrument(device)

        # convenience method

    def set_output(self, channel, current):
        """Set the current on the given channel. Turn output on or off depending on the specified current."""
        self.set_ch(channel)
        if current <= 0 or current is None:
            self.stop()
        else:
            self.set_current(current)
            self.run()

    # functions to perform different SCPI-commands
    def set_ch(self, ch):
        """sets the channel 1, 2 or 3"""
        if ch in [1, 2, 3]:
            self.instr.write('INST OUTP' + str(ch))
        else:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')

    def get_ch(self):
        """asks for the selected channel"""
        channel = int(self.instr.ask('INST:NSEL?'))
        return channel

    def status(self, ch):
        """gets the current status of the selected channel (CC or CV)"""
        state = int(self.instr.ask('STAT:QUES:INST:ISUM' + str(ch) + ':COND?'))
        if state == 1:
            return 'CC'
        elif state == 2:
            return 'CV'
        else:
            raise ValueError("Couldn't read the status of the selected channel.")

    def set_voltage(self, volt):
        """sets the voltage to the desired value"""
        if volt < 0:
            raise ValueError('The selected voltage cannot be set.')
        elif volt > self.voltage_max:  # the voltage_max will be set on the power supply if volt exceed voltage_max
            self.instr.write('VOLT %1.3f' % self.voltage_max)
            print('The set voltage exceed the maximum voltage: %1.3f' % self.voltage_max)
        else:
            self.instr.write('VOLT %1.3f' % volt)

    def set_voltage_step(self, vstep):
        """increases the voltage by a desired step (can only be used if the output is on)"""
        vset = self.get_voltage()
        self.set_voltage(vset + vstep)

    def get_voltage(self):
        """measures the voltage"""
        voltage = float(self.instr.ask('MEAS:VOLT?'))
        return voltage

    def set_current(self, curr):
        """sets the current to the desired value"""
        if curr < 0:
            raise ValueError('The selected current cannot be set.')
        elif curr > self.current_max:  # the current_max will be set on the power supply if curr exceed current_max
            self.instr.write('CURR %1.3f' % self.current_max)
            print('The set current exceed the maximum current: %1.3f' % self.current_max)
        else:
            self.instr.write('CURR %1.3f' % curr)

    def set_current_step(self, cstep):
        """increases the current by a desired step (can only be used if the output is on)"""
        cset = self.get_current()
        self.set_current(cset + cstep)

    def get_current(self):
        """measures the current"""
        current = float(self.instr.ask('MEAS:CURR?'))
        return current

    def set_arbitrary(self, ch, seq, N):
        """performs a sequence of voltage and current values for a given time on one channel with a number of repetitions.
           ch: channel for output
           seq: sequence to be set in form of a nested list = [(voltage,current,time),(..),(..),...]
           N: number of repetitions [1..255]. 0 means infinite repetitions."""
        seq_ary = np.array(seq)
        if max(seq_ary[:, 0]) > self.voltage_max:
            raise ValueError('The set voltage exceed the maximum voltage: %1.3f' % self.voltage_max)
        elif max(seq_ary[:, 1]) > self.current_max:
            raise ValueError('The set current exceed the maximum current: %1.3f' % self.current_max)
        elif min(seq_ary[:, 2]) < .5:
            raise ValueError('The set time is shorter than 0.5s.')
        elif seq_ary.min() <= 0:
            # HW-FIX: was `seq <= 0`, comparing a list against an int. Python 2
            # allowed that and always returned False, so the check never fired;
            # Python 3 raises TypeError. Compare the values instead.
            raise ValueError('Negative value of voltage, current or time.')
        elif ch not in [1, 2, 3]:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')
        elif N not in list(range(0, 256)):
            raise ValueError('The set repetitions are outside the range [0,255].')
        else:
            # HW-FIX: str.translate(None, chars) is Python 2 only.
            self.instr.write('ARB:DATA' + ' ' +
                             str(seq).translate({ord(c): None for c in '[()] '}))
            self.instr.write('ARB:REP' + ' ' + str(N))
            self.instr.write('ARB:TRANS' + ' ' + str(ch))
            self.instr.write('ARB:STAR' + ' ' + str(ch))
            self.set_ch(ch)
            self.run()

    def stop_arbitrary(self, ch):
        """stops the arbitrary sequence of a specified channel ch."""
        self.instr.write('ARB:STOP' + ' ' + str(ch))

    def get_arbitrary(self, ch):
        """gets the number of repetitions of the arbitrary sequence"""
        self.set_ch(ch)
        num = int(self.instr.ask('ARB:REP?'))
        return num

    def get_all(self):
        """gets the measured values for all channels in the form [(ch,V,A),]"""
        l = []
        for i in [1, 2, 3]:
            self.set_ch(i)
            vset = self.get_voltage()
            cset = self.get_current()
            l.append((i, vset, cset))
        return l

    def run(self):
        """turns the output from the chosen channel on"""
        self.instr.write('OUTP ON')

    def run_all(self):
        """turns the output from all channels on"""
        self.set_ch(1)
        self.instr.write('OUTP:SEL ON')
        self.set_ch(2)
        self.instr.write('OUTP:SEL ON')
        self.set_ch(3)
        self.instr.write('OUTP:SEL ON')
        self.instr.write('OUTP:GEN ON')

    def stop(self):
        """turns the output from the chosen channel off"""
        self.instr.write('OUTP OFF')

    def stop_all(self):
        """stops the output of all channels"""
        self.set_ch(1)
        self.instr.write('OUTP:SEL OFF')
        self.set_ch(2)
        self.instr.write('OUTP:SEL OFF')
        self.set_ch(3)
        self.instr.write('OUTP:SEL OFF')
        self.instr.write('OUTP:GEN OFF')

    def reset(self):
        """resets the currents to 0.0 on all channels"""
        for ch in [1, 2, 3]:
            self.set_ch(ch)
            self.set_current(0.0)
            self.stop()
        self.instr.write('*RST')  # resets the device

    def close(self):
        """stops and disconnects the device"""
        self.stop_all()
        self.instr.close_lan()

    def beep(self):
        """gives an acoustical signal from the device"""
        self.instr.write('SYST:BEEP')

    def error_list(self):
        """prints all errors from the error register."""
        error = str(self.instr.ask('SYST:ERR?'))
        return error

    def OVP(self, fuse_voltage_max):
        """sets the Over-Voltage-Protection to the value fuse_voltage_max for a selected channel"""
        if fuse_voltage_max < 0:
            raise ValueError('The selected value for voltage protection cannot be set.')
        elif fuse_voltage_max > 32.0:  # the maximal voltage which the HMP2030 supplies
            raise ValueError('The set voltage exceed the maximum voltage: 32V')
        else:
            self.instr.write('VOLT:PROT %1.3f' % fuse_voltage_max)

    def FUSE(self, fuse_current_max):
        """sets the fuse to the value fuse_current_max and the delay time to 0ms for a selected channel"""
        self.instr.write('FUSE ON')
        if fuse_current_max < 0:
            raise ValueError('The selected value for current fuse cannot be set.')
        elif fuse_current_max > 5.0:  # the maximal current which the HMP2030 supplies
            raise ValueError('The set current exceed the maximum current: 5A')
        else:
            self.instr.write('CURR %1.3f' % fuse_current_max)
        self.instr.write('FUSE:DEL 0')

    def del_FUSE(self):
        """turns the the fuse off"""
        self.instr.write('FUSE OFF')


class USBRelais():
    """To control the Conrad '8fach Relaiskarte' (Bestnr.: 197720)
       via USB (virtual COM). Needs "pyserial" to run.
        
        Usage Examples:
        
            hmpbipolar = BipolarHMP2030(serPort)
            
            The status of the relais is changed according to self.status or self.select.
            In the list [K1,K2,K3,K4,K5,K6,K7,K8] the relais can be addressed using (1=on,select) and (0=off,not selcted). 
                    
        Optional Parameters:
        
            serPort:    Serial Port (normally COM3 -> serPort=2)"""

    def __init__(self, serPort=2):
        self.nBits = 8
        self.vBits = [2 ** b for b in range(self.nBits)]

        import serial
        # HW-FIX: pyserial 3 dropped integer port numbers. The old default of 2
        # meant COM3; a bare int now raises. Ints are mapped for compatibility.
        if isinstance(serPort, int):
            serPort = 'COM%d' % (serPort + 1)
        self.port = serial.Serial(serPort, 19200, timeout=1, xonxoff=0, rtscts=0)
        self.status = []
        self.select = []

        # if not self.NOP() == 1:
        #    raise ValueError("Couldn't connect to BipolarHMP2030.")

    # helper functions to convert bit into integer and vice versa
    def bit(self, i):
        """convert values to 0 or 1, depending on the truth value"""
        if i:
            return 1
        else:
            return 0

    def intConvert(self, x, n=8):
        """return a bitlist from integer x, using n bits (1 == [1,0,0,0,0,0,0,0])"""
        if not 0 <= x <= ((2 ** n) - 1):
            raise ValueError("number to large")
        return [self.bit(x & b) for b in self.vBits[:n]]

    def bitConvert(self, l):
        """return an integer from bitlist ([1,0,0,0,0,0,0,0] == 1)"""
        if len(l) > self.nBits:
            raise ValueError("number of digits to large")
        return reduce(operator.add, list(map(lambda a, b: self.bit(a) * b, l, self.vBits[:len(l)])))

    # functions to communicate with the device
    def sendFrame(self, a, b, c):
        """The frame consists of 4byts (CMD,Address,Data,Checksum)"""
        # HW-FIX: pyserial 3 writes bytes, not str. The old '%c%c%c%c' string
        # would also have been encoded as UTF-8 for values above 127, turning a
        # 4-byte frame into 5 or more bytes on the wire.
        self.port.write(bytes((a & 0xFF, b & 0xFF, c & 0xFF, (a ^ b ^ c) & 0xFF)))
        time.sleep(0.1)
        self.port.flushOutput()

    def readFrame(self):
        """Also the answer consists of 4byts"""
        s = self.port.read(4)
        self.port.flushInput()
        if not s:
            return s
        # HW-FIX: read() returns bytes; iterating already yields ints, so
        # map(ord, ...) raised TypeError.
        r = tuple(bytearray(s))
        if not r[0] ^ r[1] ^ r[2] == r[3]:
            raise RuntimeError('Checksum error: ' + str(r))
        if r[0] == 255:
            raise RuntimeError('Received error frame: ' + str(r))
        return r[:3]

    def sendCmd(self, a, b, c):
        """The device answers with an answer frame on every send
           frame containing (inverted CMD,Address,Data, new Checksum)"""
        for i in range(3):  # retries
            self.sendFrame(a, b, c)
            time.sleep(0.5)
            f = self.readFrame()
            if f and f[0] == 255 - a and f[1] == b:
                return f
            time.sleep(i * 0.1)
        # HW-FIX: f is empty when the device sent nothing, so the old message
        # raised IndexError instead of reporting the failure.
        if f:
            raise RuntimeError('Command failed: %d-%d-%d -> %s' % (a, b, c, tuple(f)))
        raise RuntimeError('Command failed: %d-%d-%d -> no answer' % (a, b, c))

    # functions to perform commands
    def NOP(self):
        """No Operation: receives an error (CMD=255) and returns 1"""
        self.sendFrame(0, 1, 0)
        time.sleep(0.5)
        s = self.port.read(4)
        self.port.flushInput()
        if not s:
            # HW-FIX: was RuntimError -- a typo that turned this failure into a
            # NameError, hiding what actually went wrong.
            raise RuntimeError('Communication failure error: received empty string')
        r = tuple(bytearray(s))  # HW-FIX: bytes iterate as ints
        if not r[0] ^ r[1] ^ r[2] == r[3]:
            raise ValueError('Checksum error: ' + str(r))
        if r[0] == 255:
            return 1
        return 0

    def cardInit(self):
        print('deprecated, use reset instead')
        self.reset()

    def reset(self):
        """(re)initialize card and get status"""
        f = self.sendCmd(1, 1, 0)
        return f[2]  # returns version of microcontroller-software

    # functions to control the relais
    def getPort(self):
        """asks for the status of each port (answer in form of [K1,K2,K3,K4,K5,K6,K7,K8])"""
        f = self.sendCmd(2, 1, 0)
        return self.intConvert(int(f[2]))

    def setPort(self, x):
        """set relay status from self.status (x in form of [K1,K2,K3,K4,K5,K6,K7,K8])"""
        self.status = x
        c = self.bitConvert(self.status)
        r = self.sendCmd(3, 1, c)

    def onSinglePort(self, x):
        """switch single relay on from self.select without changing the others (x in form of [K1,K2,K3,K4,K5,K6,K7,K8])"""
        self.select = x
        c = self.bitConvert(self.select)
        r = self.sendCmd(6, 1, c)

    def offSinglePort(self, x):
        """switch single relay off from self.select without changing the others (x in form of [K1,K2,K3,K4,K5,K6,K7,K8])"""
        self.select = x
        c = self.bitConvert(self.select)
        r = self.sendCmd(7, 1, c)

    def Toggle(self, x):
        """switch status of selected relais according to self.select (x in form of [K1,K2,K3,K4,K5,K6,K7,K8])"""
        self.select = x
        c = self.bitConvert(self.select)
        r = self.sendCmd(8, 1, c)


class BipolarHMP2030():

    def __init__(self, hmp, relais):
        self.hmp = hmp
        self.relais = relais

    def _get_polarity(self, ch):
        """returns the polarity p of a given channel ch.
           The polarity is 1 for (+ -> 1, - -> 2 | [1,0,1,0,1,0,0,0])
           and -1 for (+ -> 2, - -> 1 | [0,1,0,1,0,1,0,0])."""
        r = self.relais.getPort()
        if ch not in [1, 2, 3]:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')
        elif r[2 * ch - 2] == r[2 * ch - 1]:
            raise ValueError('Undefined polarity.')
        elif r[2 * ch - 2] == 1 and r[2 * ch - 1] == 0:
            return 1
        elif r[2 * ch - 2] == 0 and r[2 * ch - 1] == 1:
            return -1
        else:
            raise ValueError("Couldn't get the polarity.")

    def _set_polarity(self, ch, p):
        """sets the polarity p of a given channel ch.
           It ramps down the current and changes the polarity.
           The output is turned off when the polarity is switched"""
        r = self._get_polarity(ch)
        if ch not in [1, 2, 3]:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')
        elif p not in [-1, 1]:
            raise ValueError('Undefined polarity.')
        elif r != p:
            self.hmp.set_ch(ch)
            self.hmp.set_voltage(0.0)
            time.sleep(0.5)  # add a timeout for the current to settle
            self.hmp.stop()
            time.sleep(0.1)
            x = [0, 0, 0, 0, 0, 0, 0, 0]
            x[2 * ch - 2] = 1
            x[2 * ch - 1] = 1
            self.relais.Toggle(x)
            time.sleep(0.1)
            s = self._get_polarity(ch)
            if s != p:
                raise ValueError("cannot change polarity")

    def set_voltage(self, voltage):
        polarity = np.sign(voltage)
        if polarity == 0:
            polarity = 1
        self._set_polarity(1, polarity)
        self.hmp.set_ch(1)
        self.hmp.run()
        self.hmp.set_voltage(abs(voltage))


from traits.api import HasTraits, Range
from traitsui.api import View, Item


class HMP2030Traits(HMP2030, HasTraits):
    """add simple traits for hmp2030, untested, default branch"""

    def __init__(self, device, voltage_max=20.0, current_max=2.0, fuse_voltage_max=20.0, fuse_current_max=2.5,
                 **kwargs):
        HMP2030.__init__(self, device, voltage_max, current_max, fuse_voltage_max, fuse_current_max)
        self.add_trait('current',
                       Range(low=0.0, high=current_max, value=self.get_current(), label='Current [A]', auto_set=False,
                             enter_set=True))
        HasTraits.__init__(self, **kwargs)

    def _current_changed(self, new):
        self.set_output(1, new)

    traits_view = View(Item('current'), title='HMP2030')


if __name__ == '__main__':
    hmp = HMP2030('192.168.1.16:50000', reset=False)
    relais = USBRelais()
    bipolar = BipolarHMP2030(hmp, relais)
