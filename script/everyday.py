"""
These is an accumulation of important scripts for everyday use!

Always run these scripts with the command 'run -i'!
It is very important that they are executed in the same namespace where pi3diamond lives
so that they have the same instances and imports!
"""

# save Confocal+marked NV centers
auto_focus.save('defaults/auto_focus.pys')

# save global variables
global_vars_edt.save('defaults/global_variables.pys')

# save .png from confocal scan
filename = confocal.filename
from chaco.api import PlotGraphicsContext
import importlib

gc = PlotGraphicsContext(confocal.figure_container.outer_bounds, dpi=72)
gc.render_component(confocal.figure_container)
gc.save(filename)

# save .png from any line plot
filename = rabi_measurement.filename
from chaco.api import PlotGraphicsContext

gc = PlotGraphicsContext(rabi_measurement.line_plot.outer_bounds, dpi=72)
gc.render_component(rabi_measurement.line_plot)
gc.save(filename)

# save .png from auto_focus.drift
filename = 'Z:/python_data_temp/p+111_AreaI_10keV_drift.png'
from chaco.api import PlotGraphicsContext

gc = PlotGraphicsContext(auto_focus.figure_drift.outer_bounds, dpi=72)
gc.render_component(auto_focus.figure_drift)
gc.save(filename)

# open pulsed odmr
from measurements.podmr import pODMR

p_odmr = pODMR(pulse_generator, time_tagger, rf)
p_odmr.edit_traits()

#############################
###### MAGNET SETTINGS ######
#############################

# set the vectormagnet to the 4 orientations of NV center in (100) diamond
# B1
import numpy as np

B0 = np.array([2.5, 2.5, 2.5])
B1 = np.array([0.3058, -0.2548, -0.9173])
B2 = np.array([0.0398964, -0.99741, 0.0598446])
B3 = np.array([-0.75376066, 0.13019502, -0.64412275])
B4 = np.array([0.890043, 0.445021, -0.0988936])
b1 = (B1 + B0) / (2. * B0)
b2 = (B2 + B0) / (2. * B0)
b3 = (B3 + B0) / (2. * B0)
b4 = (B4 + B0) / (2. * B0)

# B1
vector_magnet.i_rel_coil_1 = b1[0]
vector_magnet.i_rel_coil_2 = b1[1]
vector_magnet.i_rel_coil_3 = b1[2]
# B2
vector_magnet.i_rel_coil_1 = b2[0]
vector_magnet.i_rel_coil_2 = b2[1]
vector_magnet.i_rel_coil_3 = b2[2]
# B3
vector_magnet.i_rel_coil_1 = b3[0]
vector_magnet.i_rel_coil_2 = b3[1]
vector_magnet.i_rel_coil_3 = b3[2]
# B4
vector_magnet.i_rel_coil_1 = b4[0]
vector_magnet.i_rel_coil_2 = b4[1]
vector_magnet.i_rel_coil_3 = b4[2]

# 1.6*beins
beins = (b1 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
vector_magnet.i_rel_coil_1 = beins[0]
vector_magnet.i_rel_coil_2 = beins[1]
vector_magnet.i_rel_coil_3 = beins[2]

# 1.6*bzwei
bzwei = (b2 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
vector_magnet.i_rel_coil_1 = bzwei[0]
vector_magnet.i_rel_coil_2 = bzwei[1]
vector_magnet.i_rel_coil_3 = bzwei[2]

# 1.6*bdrei
bdrei = (b3 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
vector_magnet.i_rel_coil_1 = bdrei[0]
vector_magnet.i_rel_coil_2 = bdrei[1]
vector_magnet.i_rel_coil_3 = bdrei[2]

# 1.8*bvier
bvier = (b4 - np.array([0.5, 0.5, 0.5])) * 1.8 + np.array([0.5, 0.5, 0.5])
vector_magnet.i_rel_coil_1 = bvier[0]
vector_magnet.i_rel_coil_2 = bvier[1]
vector_magnet.i_rel_coil_3 = bvier[2]

# Sequence to test the time_tagger.PulsedExtTrig class.
# WATCH OUT: _binwidth is in picoseconds! We set the _bin_trigger to 4, which corresponds to
# Channel 3:48 on the breakout board (SEE: TimeTaggerController.ucf)
import time
from hardware.nidaq import SquareWave

ext_pulser = time_tagger.PulsedExtTrig(3000, 1000, 8, 0, 1, 2, 3, 4, -1, -1, False)
squarewave = SquareWave('/dev1/ctr0, /dev1/ctr1', 8, 0.5, 0.1)
# initialize =  SquareWave('/dev1/ctr0', 1, 2e-6, 0.5)
s = 1000 * [(['microwave'], 50), (['detect', 'aom'], 3000), ([], 1000)]
counts = np.zeros((100, 3000))
microwave.setPower(-7)
frequencies = np.arange(2.41e9, 2.43e9, 0.2e6)
microwave.initSweep(np.insert(frequencies, 0, 2.41e9), -6 * np.ones(frequencies.shape[0] + 1))
ext_pulser.start()
pulse_generator.setSequence(s)
starttime = time.time()
timelimit = 10
while (time.time() - starttime < timelimit):
    ext_pulser.resetSweep()
    # initialize.output()
    squarewave.output()
counts = ext_pulser.getData()

pulse_generator.setContinuous(['rf'])
frequencies = np.arange(50e6, 800e6, 0.2e6)
counts = []
for f in frequencies:
    rf.setFrequency(f)
    counts.append(time_trace.C0C1[300:].sum() / 100.)
    time.sleep(1)

# some sequences for a HahnDQT Comparison
generic.seq = "[(['mw_x'], t_pi2_x + t_pi_x), ([], tau/2.), (['mw_x'], 3*t_pi_x), " \
              "([], tau/2.), (['mw_x'], t_pi2_x + t_pi_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x + t_pi_x), ([], tau/2.), (['mw_x'], 3*t_pi_x), " \
               "([], tau/2.), (['mw_x'], t_3pi2_x + t_pi_x)]"

# some sequences for a DEER-Hahn-measurement
generic.seq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
              "(['rf'], rf_evo_t_pi2), ([], tau/2.), (['rf'], rf_evo_t_pi), ([], tau/2.)," \
              "(['rf'], rf_evo_t_pi2), ([], mw_tau/2.-2*rf_evo_t_pi2-rf_evo_t_pi-tau-rf_pulse_delay)," \
              "(['mw_x'], t_pi2_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
               "(['rf'], rf_evo_t_pi2), ([], tau/2.), (['rf'], rf_evo_t_pi), ([], tau/2.)," \
               "(['rf'], rf_evo_t_pi2), ([], mw_tau/2.-2*rf_evo_t_pi2-rf_evo_t_pi-tau-rf_pulse_delay)," \
               "(['mw_x'], t_3pi2_x)]"

# DEER-Hahn-measurement: as a second sequence imply 3pi2 on the SL instead of on the NV center
generic.seq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
              "(['rf'], rf_evo_t_pi2), ([], tau/2.), (['rf'], rf_evo_t_pi), ([], tau/2.)," \
              "(['rf'], rf_evo_t_pi2), ([], mw_tau/2.-2*rf_evo_t_pi2-rf_evo_t_pi-tau-rf_pulse_delay)," \
              "(['mw_x'], t_pi2_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
               "(['rf'], rf_evo_t_pi2), ([], tau/2.), (['rf'], rf_evo_t_pi), ([], tau/2.)," \
               "(['rf'], rf_evo_t_pi2+rf_evo_t_pi), ([], mw_tau/2.-2*rf_evo_t_pi2-rf_evo_t_pi-rf_evo_t_pi-tau-rf_pulse_delay)," \
               "(['mw_x'], t_pi2_x)]"

# some sequences for a DEER-Ramsey-measurement
generic.seq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
              "(['rf'], rf_evo_t_pi2), ([], tau), (['rf'], rf_evo_t_pi2)," \
              "([], mw_tau/2.-2*rf_evo_t_pi2-tau-rf_pulse_delay), (['mw_x'], t_pi2_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
               "(['rf'], rf_evo_t_pi2), ([], tau), (['rf'], rf_evo_t_pi2)," \
               "([], mw_tau/2.-2*rf_evo_t_pi2-tau-rf_pulse_delay), (['mw_x'], t_3pi2_x)]"

# some sequences for a Ramsey-measurement
generic.seq = "[(['mw_x'], t_pi2_x), ([], mw_tau), (['mw_x'], t_pi2_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x), ([], mw_tau), (['mw_x'], t_3pi2_x)]"


# some sequences for a DEER-T1-measurement
generic.seq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
              "(['rf'], rf_evo_t_pi2), ([], tau), (['rf'], rf_evo_t_pi2)," \
              "([], mw_tau/2.-2*rf_evo_t_pi2-tau-rf_pulse_delay), (['mw_x'], t_pi2_x)]"
generic.iseq = "[(['mw_x'], t_pi2_x), ([], mw_tau/2.), (['mw_x'], t_pi_x), ([], rf_pulse_delay)," \
               "(['rf'], rf_evo_t_pi2), ([], tau), (['rf'], rf_evo_t_pi2)," \
               "([], mw_tau/2.-2*rf_evo_t_pi2-tau-rf_pulse_delay), (['mw_x'], t_3pi2_x)]"

# trigger for awg
pulse_generator.setSequence(1000 * [(['detect', 'aom'], 100), ([], 1000)])
pulse_generator.Light()

pulse_generator.setSequence(1000 * [(['ch7'], 200), ([], 1000)])

# get the fucking fitting better!
import numpy as np
from analysis.odmr_analysis import fit_odmr, n_gaussians
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
data = np.load('Z:\\data\\20160819\\9002_acidboiled\\NV4H04\\9002_N-PP-N_NV4H04_ODMR.pys')
x, y = (data['frequency'], data['counts'])
p, dp = fit_odmr(x, y, threshold=-0.5, number_of_peaks='auto', peakshape='gaussian')
plt.figure(1)
plt.plot(x, y, x, n_gaussians(*p)(x))
plt.show()

######################
###### PLOTTING ######
######################

# Plot a deer spectrum
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
fig = plt.figure(1)
plt.plot(deer_spectroscopy.frequency / 1e6, deer_spectroscopy.spin_state / (deer_spectroscopy.spin_state.max()))
plt.xlabel('DEER Frequency [MHz]')
plt.ylabel('NV Spin State [a.u.]')
plt.grid(b=True, which='major', color='black', linestyle='--')
ax = fig.gca()
ax.xaxis.set_tick_params(labelsize=18)
ax.yaxis.set_tick_params(labelsize=18)
plt.show()

# Evaluate a deer_evolution_tau measurement on the fly!
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(deer_evolution_tau.tau)
plt.plot(deer_evolution_tau.tau, (deer_evolution_tau.spin_state[:n] -
                                  deer_evolution_tau.spin_state[n:2 * n]) -
         (deer_evolution_tau.spin_state[2 * n:3 * n] -
          deer_evolution_tau.spin_state[3 * n:4 * n]))
plt.xlabel('free evolution time [ns]', fontsize=18)
plt.ylabel('DEER contrast', fontsize=18)
plt.show()

# Evaluate a deer_evolution_rf measurement on the fly!
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(deer_evolution_rf.tau)
plt.plot(deer_evolution_rf.tau, (deer_evolution_rf.spin_state[2 * n:3 * n] -
                                 deer_evolution_rf.spin_state[3 * n:4 * n]))
plt.xlabel('free evolution time [ns]', fontsize=18)
plt.ylabel('DEER contrast', fontsize=18)
plt.show()

# Evaluate a deer_rabi measurement on the fly!
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
n = len(deer_rabi.tau)
plt.plot(deer_rabi.tau, (deer_rabi.spin_state[:n] -
                         deer_rabi.spin_state[n:2 * n]))
plt.xlabel('free evolution time [ns]')
plt.ylabel('DEER contrast')
plt.show()

# Evaluate a hahn measurement on the fly!
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
n = len(hahn.tau)
plt.plot(hahn.tau, (hahn.spin_state[:n] - hahn.spin_state[n:2 * n]))
plt.xlabel('free evolution time [ns]')
plt.ylabel('NV Contrast [a.u.]')
plt.show()

# Plot deer correlation measurement!
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
n = len(xy8_awg.tau)
plt.plot(xy8_awg.tau, xy8_awg.spin_state[:n] - xy8_awg.spin_state[n:2 * n])
plt.xlabel('free evolution time [ns]')
plt.ylabel('Correlation Signal')
plt.show()

# PulseCal
import measurements.cpmg

importlib.reload(measurements.cpmg)

from measurements.cpmg import PulseCal

pulse_cal = PulseCal(pulse_generator, time_tagger, microwave, rf=rf)
pulse_cal_view = RabiTool(measurement=pulse_cal)
pulse_cal_view.edit_traits()

# plot PulseCal
import numpy as np
from matplotlib import pyplot as plt

n = len(pulse_cal.spin_state)
spin_state_ave = float(sum(pulse_cal.spin_state) / len(pulse_cal.spin_state))
amp = 0.5 * (pulse_cal.spin_state[0] - pulse_cal.spin_state[1])
len_err = 1.0
cos_wave = amp * np.cos(np.arange(0, n, 1) * np.pi * len_err) + spin_state_ave
plt.switch_backend('TkAGG')
plt.plot(np.arange(0, n, 1), pulse_cal.spin_state)
plt.plot(np.arange(0, n, 1), cos_wave)
plt.xlabel(' evolution time [ns]')
plt.ylabel('DEER rabi contrast')
plt.show()

from measurements.hahn_echo import HahnDQT

hahn_dqt = HahnDQT(pulse_generator, time_tagger, microwave, microwave2=microwave2)
hahn_dqt_plot = PulsedToolDoubleTau(measurement=hahn_dqt)
hahn_dqt_plot.edit_traits()

from measurements.deer_spectroscopy import DEERSpectroscopyDQT

deer_spectroscopy_dqt = DEERSpectroscopyDQT(pulse_generator, time_tagger, microwave, microwave2, rf)
deer_spectroscopy_dqt.edit_traits()

# small test
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
from analysis.fitting import nonlinear_model, Cosinus, CosinusEstimator


def fit_rabis(x, y, s):
    fit_result = nonlinear_model(x, y, s, Cosinus, CosinusEstimator)
    p, v, q, chisqr = fit_result
    if p[0] < 0:
        p[0] = -p[0]
        p[2] = ((p[2] / p[1] + 0.5) % 1) * p[1]
    if (p[2] / p[1] % 1) > 0.5:
        p[2] = (p[2] / p[1] % 1) * p[1] - p[1]
    else:
        p[2] = (p[2] / p[1] % 1) * p[1]
    return p, v, q, chisqr


s = 10 * [(['microwave'], 20), (['detect', 'aom'], 3000), ([], 1000)]
s += [(['sequence'], 100)]
pulse_generator.Sequence(s)