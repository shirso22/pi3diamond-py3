"""
This is an accumulation of important scripts for opening measurements!

Always run these scripts with the command 'run -i'!
It is very important that they are executed in the same namespace where pi3diamond lives
so that they have the same instances and imports!
"""

# hahn
from analysis.pulsed import PulsedToolDoubleTau
from measurements.hahn_echo import Hahn3pi2

hahn = Hahn3pi2(pulse_generator, time_tagger, microwave)
hahn_plot = PulsedToolDoubleTau(measurement=hahn)
hahn_plot.edit_traits()

# Pi Pulse Calibration
# from measurements.cpmg import PulseCal
# from analysis.pulsed import PulsedTool
# pulsecal = PulseCal(pulse_generator, time_tagger, microwave)
# pulsecal_plot = PulsedTool(measurement=pulsecal)
# pulsecal_plot.edit_traits()

# T1
from measurements.t_one import T1pi
from analysis.pulsed import PulsedToolDoubleTauLog

t1pi = T1pi(pulse_generator, time_tagger, microwave)
t1pi_plot = PulsedToolDoubleTauLog(measurement=t1pi)
t1pi_plot.edit_traits()

# XY8
from measurements.xy_8 import XY_8
from analysis.pulsed import PulsedToolDoubleTau

xy8 = XY_8(pulse_generator, time_tagger, microwave)
xy8_plot = PulsedToolDoubleTau(measurement=xy8)
xy8_plot.edit_traits()

# DEER Spectrum NI-Card-Sweep
from hardware.nidaq import PulseTrainCounterOut

counter_deer = PulseTrainCounterOut('/dev1/ctr0', '/dev1/ctr1', '/dev1/pfi2')
from measurements.deer_old.deer_spectrum import DEER_spectrum

deer_spectrum = DEER_spectrum(rf, microwave, counter_deer, pulse_generator)
deer_spectrum.edit_traits()

# DEER Rabi
# from measurements.deer_rabi import DEERRabi
# from measurements.deer_rabi import DEERRabiTool
# deer_rabi = DEERRabi(pulse_generator, time_tagger, microwave, rf)
# deer_rabi_plot = DEERRabiTool(measurement=deer_rabi)
# deer_rabi_plot.edit_traits()

# DEER with signal and reference measurements of the Spin State
from measurements.deer import DEER as DEERsigref

deer_sigref = DEERsigref(pulse_generator, time_tagger, microwave, rf)
deer_sigref.edit_traits()

# DEER Rabi double sequence
from measurements.deer_rabi import DEERRabi
from measurements.deer_rabi import DEERRabiTool

deer_rabi_ds = DEERRabi(pulse_generator, time_tagger, microwave, rf)
deer_rabi_ds_plot = DEERRabiTool(measurement=deer_rabi_ds)
deer_rabi_ds_plot.edit_traits()

# generic measurement
# from measurements.generic import GenericPulsed
# from analysis.pulsed import PulsedToolDoubleTau
# generic_measurement = GenericPulsed(pulse_generator, time_tagger, microwave)
# generic_plot = PulsedToolDoubleTau(measurement=generic_measurement)
# generic_plot.edit_traits()

# Autocorrelation
# from measurements.autocorrelation import Autocorrelation
# autocorrelation = Autocorrelation(time_tagger)
# autocorrelation.edit_traits()
