"""
pi3diamond dummy startup script

for testing
"""

import matplotlib as mpl

mpl.use('TkAGG')

# start the JobManager
from tools import emod

emod.JobManager().start()

# start the CronDaemon
from tools import cron

cron.CronDaemon().start()

# define a shutdown function
from tools.utility import StoppableThread
import threading


def shutdown(timeout=1.0):
    """Terminate all threads."""
    cron.CronDaemon().stop()
    emod.JobManager().stop()
    for t in threading.enumerate():
        if isinstance(t, StoppableThread):
            t.stop(timeout=timeout)


#########################################
# dummy hardware
#########################################
from hardware.dummy import *

# create hardware backends
scanner = Scanner()

counter = Counter()

pulse_generator = PulseGenerator()
microwave = Microwave()
microwave2 = Microwave()
rf = Microwave()
laser = Laser()
time_tagger = TimeTagger()

#########################################
# configure hardware
#########################################
pulse_generator.Light()

#########################################
# create measurements
#########################################
from measurements.photon_time_trace import PhotonTimeTrace as TimeTrace
from measurements.odmr import ODMR
from measurements.autocorrelation import Autocorrelation

from measurements.rabi import Rabi
from measurements.t_one import T1pi
from measurements.xy_8 import XY_8
from measurements.generic import Generic_Pulsed
from measurements.deer import DEER, DEEREvolutionTau, DEEREvolutionRf
from measurements.deer_rabi import DEERRabi
from measurements.deer_correlation import DEER_correlation, DarkSpin_Rabi, DarkSpin_T1, \
    DarkSpin_Hahn
from measurements.hahn_echo import Hahn, HahnDQT
from measurements.deer_spectroscopy import DEERSpectroscopy, DEERSpectroscopyDQT

from global_vars_editor import GlobalVarsEditor

global_vars_edt = GlobalVarsEditor()

time_trace = TimeTrace(time_tagger)
autocorrelation = Autocorrelation(time_tagger)
odmr = ODMR(microwave, counter, pulse_generator)
rabi = Rabi(pulse_generator, time_tagger, microwave)
hahn = Hahn(pulse_generator, time_tagger, microwave)
generic = Generic_Pulsed(pulse_generator, time_tagger, microwave, rf)
t1pi = T1pi(pulse_generator, time_tagger, microwave)
xy8 = XY_8(pulse_generator, time_tagger, microwave)
hahn_dqt = HahnDQT(pulse_generator, time_tagger, microwave, microwave2=microwave2)
deer_spectroscopy = DEERSpectroscopy(pulse_generator, time_tagger, microwave, rf)
deer_spectroscopy_dqt = DEERSpectroscopyDQT(pulse_generator, time_tagger, microwave, microwave2, rf)

# DEER
deer_rabi = DEERRabi(pulse_generator, time_tagger, microwave, rf)
deer_simple = DEER(pulse_generator, time_tagger, microwave, rf)
deer_evolution_tau = DEEREvolutionTau(pulse_generator, time_tagger, microwave, rf)
deer_evolution_rf = DEEREvolutionRf(pulse_generator, time_tagger, microwave, rf)

# DEER correlation
deer_correlation = DEER_correlation(pulse_generator, time_tagger, microwave, rf)
darkspin_rabi = DarkSpin_Rabi(pulse_generator, time_tagger, microwave, rf)
darkspin_t1 = DarkSpin_T1(pulse_generator, time_tagger, microwave, rf)
darkspin_hahn = DarkSpin_Hahn(pulse_generator, time_tagger, microwave, rf)

#########################################
# fire up the GUI
#########################################

time_trace.edit_traits()
rabi.edit_traits()
hahn.edit_traits()
generic.edit_traits()
autocorrelation.edit_traits()
deer_spectroscopy.edit_traits()
deer_spectroscopy_dqt.edit_traits()
t1pi.edit_traits()
xy8.edit_traits()
deer_evolution_tau.edit_traits()
deer_rabi.edit_traits()
darkspin_hahn.edit_traits()
darkspin_rabi.edit_traits()
