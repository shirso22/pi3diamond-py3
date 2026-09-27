"""
Dummy hardware classes for testing.
"""

import time

import numpy as np


class Scanner():
    def get_x_range(self):
        return (0., 100.)

    def get_y_range(self):
        return (0., 100.)

    def get_z_range(self):
        return (-20., 20.)

    def setx(self, x):
        pass

    def sety(self, y):
        pass

    def setz(self, z):
        pass

    def set_position(self, x, y, z):
        """Move stage to x, y, z"""
        pass

    def scan_line(self, Line, SecondsPerPoint, return_speed=None):
        time.sleep(0.05)
        return (1000 * np.sin(Line[0, :]) * np.sin(Line[1, :]) * np.exp(-Line[2, :] ** 2)).astype(int)
        # return np.random.random(Line.shape[1])


class Counter():
    def configure(self, n, SecondsPerPoint, DutyCycle=0.8):
        x = np.arange(n)
        a = 100.
        c = 50.
        x0 = n / 2.
        g = n / 10.
        y = np.int32(c - a / np.pi * (g ** 2 / ((x - x0) ** 2 + g ** 2)))
        Counter._sweeps = 0
        Counter._y = y

    def run(self):
        time.sleep(1)
        Counter._sweeps += 1
        return np.random.poisson(Counter._sweeps * Counter._y)

    def clear(self):
        pass

    def start(self):
        """DUMMY-SHIM: measurements drive a start/read/stop protocol that
        hardware/nidaq.py provides and the dummy never grew. There is nothing
        to arm here, so this just resets the accumulator."""
        self.clear()

    def read(self):
        """DUMMY-SHIM: returns (counts, analog_in), matching nidaq's counter.

        The dummy's own run() is what produces a sweep, so read() delegates to
        it. The second element is the AI trace; measurements unpack it as
        `counts, self.ai = self.counter.read()` and tolerate None.
        """
        return self.run(), None

    def stop(self):
        """DUMMY-SHIM: no hardware to quiesce."""
        return


class Microwave():
    def setFrequency(self, frequency):
        pass

    def setPower(self, power):
        pass

    def setOutput(self, power, frequency):
        pass

    def initSweep(self, f, p):
        pass

    def resetListPos(self):
        pass

    def Sweep(self, begin, end, delta, power):
        """DUMMY-SHIM: the real sources expose Sweep(); the dummy only had
        initSweep(). Delegates so the frequency list is still built."""
        import numpy
        frequencies = numpy.arange(begin, end + delta, delta)
        return self.initSweep(frequencies, power * numpy.ones(frequencies.shape))


class PulseGenerator():
    def Sequence(self, sequence, loop=True):
        pass

    def Light(self):
        pass

    def Night(self):
        pass

    def Open(self):
        pass

    def High(self):
        pass

    def checkUnderflow(self):
        return False

    def setSequence(self, sequence, loops=-1, triggered=False, padding=[]):
        """DUMMY-SHIM: mirrors hardware/pulse_generator.py:setSequence().

        The dummy only ever had Sequence(sequence, loop). The real driver
        signature grew `triggered` and `padding`; both are accepted and
        ignored here, since nothing is being pulsed.
        """
        return self.Sequence(sequence, loops)
        # return np.random.random()<0.1


class MagCoilControl():
    """Provides Control over the magnetic field of all three coils with HMP2030 and BipolarHMP2030"""

    def set_field_cartesian(self, bx, by, bz):
        pass

    def save_stop():
        pass


class Laser():
    """Provides control of the laser power."""
    voltage = 0.


class PowerMeter():
    """Provides an optical power meter."""
    power = 0.

    def getPower(self):
        """Return the optical power in Watt."""
        PowerMeter.power += 1
        return PowerMeter.power * 1e-3


class Coil():
    def set_output(self, channel, current):
        pass


class RotationStage():
    def set_angle(self, angle):
        pass


class TimeTagger:
    class Pulsed:

        def __init__(self, n_bins, bin_width, n_slots, channel_apd_0, channel_apd_1, shot_trigger,
                     sequence_trigger=None):
            self.n_bins = n_bins
            self.n_slots = n_slots
            self.sequence_data = 'doublehahn'
            self.clear()

        def clear(self):
            n_slots = self.n_slots
            n_bins = self.n_bins
            data = np.zeros((n_slots, n_bins))
            m0 = int(n_bins / 5)
            m = float(n_bins - m0)
            M = np.arange(m, dtype=float)
            n = float(n_slots)
            k = n_slots / 2
            for i in range(n_slots):
                if self.sequence_data == 'hahn':
                    data[i, m0:] = 30 * np.exp(-9 * i ** 2 / n ** 2) * np.exp(-5 * M / m) + 100
                elif self.sequence_data == 'doublehahn':
                    if i < k:
                        data[i, m0:] = 30 * np.exp(-9 * i ** 2 / float(k ** 2)) * np.exp(-5 * M / m) + 100
                    else:
                        data[i, m0:] = -30 * np.exp(-9 * (i - k) ** 2 / float(k ** 2)) * np.exp(-5 * M / m) + 100
                elif self.sequence_data == 't1':
                    data[i, m0:] = 30 * np.exp(-3 * i / n) * np.exp(-5 * M / m) + 100
                else:
                    """Rabi Data"""
                    data[i, m0:] = 30 * np.cos(3 * 2 * np.pi * i / n) * np.exp(-5 * M / m) + 100
            self.data = data
            self.counter = 0.1 / n_slots

        def setMaxCounts(self, arg):
            pass

        def ready(self):
            time.sleep(0.1)
            return True

        def getData(self):
            self.counter += 0.1 / self.n_slots
            return np.random.poisson(self.counter * self.data)

        def getCounts(self):
            return self.counter

        def start(self):
            pass

        def stop(self):
            pass

    class Countrate():
        def __init__(self, channel):
            self.rate = 0.

        def getData(self):
            self.rate += 1.
            return 1e5 / (1 + 20. / self.rate)

        def clear(self):
            pass

    class Counter():
        def __init__(self, channel, bins_per_point, length):
            self.channel = channel
            self.seconds_per_point = float(bins_per_point) / 800000000
            self.length = length

        def getData(self):
            return np.random.random_integers(100000, 120000, self.length) * self.seconds_per_point

    class PulsedExtTrig(Pulsed):
        """DUMMY-SHIM: externally triggered Pulsed measurement.

        Signature mirrors the real C++ class in
        timetagger/backend/PulsedExtTrig.cpp:36 --

            PulsedExtTrig(int length, long long binwidth, int sequence_length,
                          int channel, int channel2, int shot_trigger=-1,
                          int sequence_trigger=-1, int bin_trigger=-1,
                          int trig1=-1, int trig2=-1, bool dual_sequence=true)

        Inheriting Pulsed's 7-argument __init__ is not enough: the call in
        deer_spectroscopy.py passes 11 and raised
            TypeError: Pulsed.__init__() takes from 7 to 8 positional
                       arguments but 12 were given

        hardware/dummy.py's TimeTagger only ever had Pulsed, Counter and
        Countrate. measurements/deer_spectroscopy.py calls PulsedExtTrig, so
        both DEER Spectroscopy variants died with

            AttributeError: 'TimeTagger' object has no attribute 'PulsedExtTrig'

        The real class waits on an external trigger and tracks sweep state.
        With no hardware there is nothing to trigger on, so this inherits the
        Pulsed dummy's synthetic data and adds the extra methods the
        measurement calls.
        """

        def __init__(self, n_bins, bin_width, sequence_length, channel_apd_0,
                     channel_apd_1, shot_trigger=-1, sequence_trigger=-1,
                     bin_trigger=-1, trig1=-1, trig2=-1, dual_sequence=True):
            # super(), not Pulsed.__init__: these are classes nested inside
            # TimeTagger, and a nested class body is not an enclosing scope for
            # its own methods, so the bare name `Pulsed` is unresolvable here
            # even though it works as a base class in the class statement.
            super().__init__(n_bins, bin_width, sequence_length,
                             channel_apd_0, channel_apd_1, shot_trigger,
                             sequence_trigger)
            self.bin_trigger = bin_trigger
            self.trig1 = trig1
            self.trig2 = trig2
            self.dual_sequence = dual_sequence

        def resetSweep(self):
            self.clear()

        def getSequenceNumber(self):
            return 0

        def getPulse(self):
            return self.getData()

    class PulsedAFM(Pulsed):
        """DUMMY-SHIM: AFM variant. Same reasoning as PulsedExtTrig."""
        pass

class SquareWave(object):
    """DUMMY-SHIM: stand-in for hardware/nidaq.py's SquareWave.

    measurements/deer_spectroscopy.py is the one measurement that does NOT
    take its hardware by injection -- every other dependency arrives through
    __init__ (pulse_generator, time_tagger, microwave, rf), but line 28 does

        from hardware.nidaq import SquareWave

    and constructs it directly. So the measurement reaches into a real NI-DAQ
    driver no matter what pi3dummy passes it, and on a machine without
    NI-DAQmx installed it dies with

        OSError: nicaiu.dll could not be loaded

    That is pre-existing: the same failure happens under Python 2. Only
    output() is ever called on the object.
    """

    def __init__(self, square_wave_device, length=100, seconds_per_point=1e-3,
                 duty_cycle=0.5):
        self._square_wave_device = square_wave_device
        self._length = length
        self._seconds_per_point = seconds_per_point
        self._duty_cycle = duty_cycle

    def set_timing(self, seconds_per_point, duty_cycle=0.5):
        self._seconds_per_point = seconds_per_point
        self._duty_cycle = duty_cycle

    def get_timing(self):
        return self._seconds_per_point, self._duty_cycle

    def setLength(self, length):
        self._length = length

    def getLength(self):
        return self._length

    def output(self):
        """No hardware to drive. Sleep for the duration the real pulse train
        would have taken, so the measurement's timing still looks plausible."""
        import time as _time
        _time.sleep(min(self._length * self._seconds_per_point, 1.0))
