# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
# PY3-PORT: pickle.load(..., encoding='latin1') throughout this file.
# Python 2 pickled `str` as bytes; without an explicit codec every string
# in a historical .pys file comes back as bytes, or raises
# UnicodeDecodeError. latin-1 round-trips bytes 0-255 one-to-one, so numpy
# arrays and ASCII dict keys both survive. No-op for Python 3 pickles.
import numpy as np


def record_calibration_data(microwave,
                            voltmeter,
                            frequencies=np.arange(1e9, 10e9, 2e9),
                            powers=np.arange(-20., 20., 2.)
                            ):
    import time

    voltage = np.empty((len(frequencies), len(powers)))

    for i, f in enumerate(frequencies):
        for k, p in enumerate(powers):
            microwave.setOutput(p, f)
            if k == 0:
                time.sleep(2.0)
            time.sleep(1.0)
            v = np.abs(voltmeter.get_voltage())
            voltage[i, k] = v
            print(f, p, v)

    microwave.setPower(-20)

    return (voltage, frequencies, powers)


def make_calibration_function(voltages, frequencies, powers):
    """Creates a new calibration function based on measured voltage, frequency and power."""

    import scipy.interpolate
    import scipy.ndimage

    new_voltages = np.arange(0.0, voltages.max(), 0.0001)
    new_powers = np.empty((len(frequencies), len(new_voltages)))

    for i, f in enumerate(frequencies):
        new_powers[i, :] = scipy.interpolate.interp1d(voltages[i, :], powers, bounds_error=False, fill_value=0.0)(
            new_voltages)

    coeffs = scipy.ndimage.spline_filter(new_powers)

    v_min = voltages[:, 0].max()
    v_max = voltages[:, -1].min()
    v0 = new_voltages[0]
    dv = new_voltages[1] - new_voltages[0]
    f0 = frequencies[0]
    df = frequencies[1] - frequencies[0]

    def voltage_to_power(f, v):
        if v < v_min:
            return 0.0
        elif v > v_max:
            return np.inf
        else:
            coords = np.array([((f - f0) / (df),), ((v - v0) / (dv),)])
            return scipy.ndimage.map_coordinates(coeffs, coords, prefilter=False)[0]

    return voltage_to_power


def ohms_law(f, v):
    return 10. * np.log10(v ** 2 / 50.) + 30.


class Schottky():
    """Measure microwave power with a voltmeter and a schottky diode."""

    def __init__(self, voltmeter, calibration=None):
        self.voltmeter = voltmeter
        self.set_frequency()
        if calibration is None:
            self.volt_to_power = ohms_law
        else:
            import pickle
            fil = open(calibration, 'rb')
            cal_data = pickle.load(fil, encoding='latin1')
            fil.close()
            self.volt_to_power = make_calibration_function(*cal_data)

    def set_frequency(self, frequency=3e9):
        """Set the frequency used for calibration."""
        self.frequency = frequency

    def get_frequency(self):
        return self.frequency

    def get_power(self):
        """Measure the power."""
        voltage = np.abs(self.voltmeter.get_voltage())
        return self.volt_to_power(self.frequency, voltage)


from traits.api import HasTraits, Float, Property
from traitsui.api import View, Item, HGroup
from tools.emod import Job

import threading


class SchottkyHasTraits(Schottky, Job):
    frequency = Float(3e9)
    power = Property()
    current_power = Float(np.nan, label='power')
    refresh_interval = Float(1.0)

    def __init__(self, voltmeter, **kwargs):
        HasTraits.__init__(self, **kwargs)
        Schottky.__init__(self, voltmeter, **kwargs)
        self.start()

    def _get_power(self):
        power = self.get_power(self.frequency)
        self.current_power = power
        return power

    def _run(self):
        while True:
            threading.current_thread().stop_request.wait(self.refresh_interval)
            if threading.current_thread().stop_request.is_set():
                break
            self.power

    #    def _power_changed(self):
    #        self.current_power = power

    traits_view = View(HGroup(Item('current_power', style='readonly'),
                              Item('frequency'),
                              ),
                       )


if __name__ == '__main__':
    #
    #    voltmeter = VoltMeter('/Dev1/ai0', range=(-10.,10.), n_samples=1000)
    #
    cal_data = record_calibration_data(microwave,
                                       voltmeter,
                                       frequencies=np.arange(1e9, 6e9, 1e9),
                                       powers=np.arange(-16., 20., 1.)
                                       )

    import pickle

    fil = open('schottky_calibration_6GHz.pyd', 'wb')
    pickle.dump(cal_data, fil, 1)
    fil.close()

#    from volt_meter import VoltMeter
#    voltmeter = VoltMeter('/Dev1/ai0', range=(-10.,10.), n_samples=1000)
#    schottky = Schottky(voltmeter,'hardware/schottky_calibration.pyd')

#    s_ohm = Schottky(voltmeter)

# s_cal = SchottkyHasTraits(voltmeter,calibration='schottky_calibration.pyd')
# s_cal.edit_traits()

# import pylab
# pylab.figure()
# pylab.imshow(newP, extent=(0,1,0,1))
