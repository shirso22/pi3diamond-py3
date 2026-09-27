import measurements.awg.rabi_awg
import measurements.awg.waveform
import importlib

importlib.reload(measurements.awg.waveform)
importlib.reload(measurements.awg.rabi_awg)

##################
### AWG Pulsed ###
##################

# rabi_awg_pulsed
import measurements.awg.rabi_awg_pulsed, measurements.awg.measurements_awg

importlib.reload(measurements.awg.measurements_awg)
importlib.reload(measurements.awg.rabi_awg_pulsed)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.rabi_awg_pulsed import Rabi_awg_pulsed as RabiAWG
from measurements.awg.rabi_awg_pulsed import RabiToolAwg as RabiToolAWG

rabi_awg = RabiAWG(pulse_generator, time_tagger, rf, awg)
rabi_tool_awg = RabiToolAWG(measurement=rabi_awg)
rabi_tool_awg.edit_traits()

# hahn_echo_awg_pulsed
import measurements.awg.hahn_echo_awg_pulsed

importlib.reload(measurements.awg.hahn_echo_awg_pulsed)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.hahn_echo_awg_pulsed import Hahn3pi2_awg_pulsed as HahnAWG
from analysis.pulsed import PulsedToolDoubleTau as HahnToolAWG

Hahn_awg = HahnAWG(pulse_generator, time_tagger, rf, awg)
Hahn_tool_awg = HahnToolAWG(measurement=Hahn_awg)
Hahn_tool_awg.edit_traits()

# spin_lock_awg_pulsed
import measurements.awg.spin_lock_awg_pulsed

importlib.reload(measurements.awg.spin_lock_awg_pulsed)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.spin_lock_awg_pulsed import Spinlock_awg_pulsed as Spinlock
from measurements.awg.rabi_awg_pulsed import RabiToolAwg as HahnToolAWG

Spinlock_awg = Spinlock(pulse_generator, time_tagger, rf, awg)
Spinlock_tool_awg = HahnToolAWG(measurement=Spinlock_awg)
Spinlock_tool_awg.edit_traits()

# xy8_awg_pulsed
import measurements.awg.xy8_awg_pulsed

importlib.reload(measurements.awg.xy8_awg_pulsed)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.xy8_awg_pulsed import XY8_awg_pulsed as XY8AWG
from measurements.awg.xy8_awg_pulsed import XY8_awg_pulsed_view

xy8_awg = XY8AWG(pulse_generator, time_tagger, rf, awg)
XY8_tool_awg = XY8_awg_pulsed_view(measurement=xy8_awg)
XY8_tool_awg.edit_traits()

# xy8_correlations_awg_pulsed
import measurements.awg.xy8_correlation

importlib.reload(measurements.awg.xy8_correlation)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.xy8_correlation import XY8Correlation
from measurements.awg.xy8_correlation import XY8CorrelationView

xy8_correlation = XY8Correlation(pulse_generator, time_tagger, rf, awg)
XY8_correlation_awg_view = XY8CorrelationView(measurement=xy8_correlation)
XY8_correlation_awg_view.edit_traits()

# odmr_awg_pulsed
import measurements.awg.ODMR_awg_pulsed

importlib.reload(measurements.awg.ODMR_awg_pulsed)

from measurements.awg.ODMR_awg_pulsed import ODMR_awg_pulsed
from hardware.awg import AWG

awg = AWG()
odmr_awg_pulsed = ODMR_awg_pulsed(pulse_generator, time_tagger, rf, awg)
odmr_awg_pulsed.edit_traits()

# pulse_calibraton_awg_pulsed
import measurements.awg.pulse_calibration_awg_pulsed

importlib.reload(measurements.awg.pulse_calibration_awg_pulsed)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.pulse_calibration_awg_pulsed import Pulse_calibration_awg_pulsed as PulseCail

pulse_cali_awg = PulseCail(pulse_generator, time_tagger, rf, awg)
PulseCail_tool_awg = RabiToolAWG(measurement=pulse_cali_awg)
PulseCail_tool_awg.edit_traits()

################
### PLOTTING ###
################

# plot hahn_awg_pulsed
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(Hahn_awg.tau)
plt.plot(Hahn_awg.tau, Hahn_awg.spin_state[:n])
plt.xlabel('evolution time [ns]')
plt.ylabel('Hahn-echo contrast')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()

# plot xy8_awg_pulsed
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(xy8_awg.tau)
plt.plot(xy8_awg.tau, xy8_awg.spin_state[:n])
plt.xlabel('evolution time [ns]')
plt.ylabel('XY-8 contrast')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()

# plot odmr_awg_pulsed
from matplotlib import pyplot as plt
import numpy as np

plt.switch_backend('TkAGG')
plt.figure(1)
plt.plot(np.arange(odmr_awg_pulsed.freq_begin, odmr_awg_pulsed.freq_end, odmr_awg_pulsed.freq_delta),
         odmr_awg_pulsed.spin_state)
plt.xlabel('MW frequency [Hz]')
plt.ylabel('NV contrast')
plt.show()

# plot PulseCali
import numpy as np
from matplotlib import pyplot as plt

n = len(pulse_cali_awg.spin_state)
spin_state_ave = float(sum(pulse_cali_awg.spin_state) / len(pulse_cali_awg.spin_state))
amp = 0.5 * (pulse_cali_awg.spin_state[0] - pulse_cali_awg.spin_state[1])
len_err = 1.0
cos_wave = amp * np.cos(np.arange(0, n, 1) * np.pi * len_err) + spin_state_ave
plt.switch_backend('TkAGG')
plt.plot(np.arange(0, n, 1), pulse_cali_awg.spin_state)
plt.plot(np.arange(0, n, 1), cos_wave)
plt.xlabel(' # of pi pulse [ns]')
plt.ylabel(' Contrast')
plt.show()

############
### AWG ####
############
# rabi_awg
import measurements.awg.rabi_awg

importlib.reload(measurements.awg.rabi_awg)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.rabi_awg import Rabi_awg as RabiAWG
from analysis.pulsed import PulsedToolDoubleTau as RabiToolAWG

rabi_awg = RabiAWG(pulse_generator, time_tagger, microwave, rf, awg)
rabi_tool_awg = RabiToolAWG(measurement=rabi_awg)
rabi_tool_awg.edit_traits()

# hahn_echo_awg
import measurements.awg.hahn_echo_awg

importlib.reload(measurements.awg.hahn_echo_awg)

from hardware.awg import AWG

awg = AWG()
from measurements.awg.hahn_echo_awg import Hahn3pi2_awg as HahnAWG
from analysis.pulsed import PulsedToolDoubleTau as HahnToolAWG

Hahn_awg = HahnAWG(pulse_generator, time_tagger, microwave, rf, awg)
Hahn_tool_awg = HahnToolAWG(measurement=Hahn_awg)
Hahn_tool_awg.edit_traits()

# TEER Measurement_freq
import measurements.awg.TEER_freq_awg

importlib.reload(measurements.awg.TEER_freq_awg)

from measurements.awg.TEER_freq_awg import TEER_freq_awg
from hardware.awg import AWG

awg = AWG()
teer_freq_awg = TEER_freq_awg(pulse_generator, time_tagger, microwave, rf, awg)
teer_freq_awg.edit_traits()

# TEER Measurement_delay
import measurements.awg.TEER_delay_awg

importlib.reload(measurements.awg.TEER_delay_awg)

from measurements.awg.TEER_delay_awg import TEER_delay_awg
from hardware.awg import AWG

awg = AWG()
teer_delay_awg = TEER_delay_awg(pulse_generator, time_tagger, microwave, rf, awg)
teer_delay_awg_view = PulsedToolDoubleTau(measurement=teer_delay_awg)
teer_delay_awg_view.edit_traits()

# TEER Measurement_tau
import measurements.awg.TEER_tau_awg

importlib.reload(measurements.awg.TEER_tau_awg)

from measurements.awg.TEER_tau_awg import TEER_tau_awg
from hardware.awg import AWG

awg = AWG()
teer_tau_awg = TEER_tau_awg(pulse_generator, time_tagger, microwave, rf, awg)
teer_tau_awg_view = PulsedToolDoubleTau(measurement=teer_tau_awg)
teer_tau_awg_view.edit_traits()

# TEER Measurement_freq_2pi
import measurements.awg.TEER_freq_2pi_awg

importlib.reload(measurements.awg.TEER_freq_2pi_awg)

from measurements.awg.TEER_freq_2pi_awg import TEER_freq_2pi_awg
from hardware.awg import AWG

awg = AWG()
teer_freq_2pi_awg = TEER_freq_2pi_awg(pulse_generator, time_tagger, microwave, rf, awg)
teer_freq_2pi_awg.edit_traits()

# DEER Rabi
import measurements.awg.DEER_Rabi_awg

importlib.reload(measurements.awg.DEER_Rabi_awg)

from measurements.awg.DEER_Rabi_awg import DEER_Rabi_awg, DEER_Rabi_awg_view
from hardware.awg import AWG

awg = AWG()
deer_rabi_awg = DEER_Rabi_awg(pulse_generator, time_tagger, microwave, rf, awg)
deer_rabi_awg_view = DEER_Rabi_awg_view(measurement=deer_rabi_awg)
deer_rabi_awg_view.edit_traits()

# DEER Hahn
import measurements.awg.DEER_Hahn_awg

importlib.reload(measurements.awg.DEER_Hahn_awg)

from measurements.awg.DEER_Hahn_awg import DEER_Hahn_awg
from hardware.awg import AWG

awg = AWG()
deer_hahn_awg = DEER_Hahn_awg(pulse_generator, time_tagger, microwave, rf, awg)
deer_hahn_awg_view = PulsedToolDoubleTau(measurement=deer_hahn_awg)
deer_hahn_awg_view.edit_traits()

# DEER
import measurements.awg.DEER_awg

importlib.reload(measurements.awg.DEER_awg)

from measurements.awg.DEER_awg import DEER_awg
from hardware.awg import AWG

awg = AWG()
deer_awg = DEER_awg(pulse_generator, time_tagger, microwave, rf, awg)
deer_awg.edit_traits()

# ODMR
import measurements.awg.ODMR_awg

importlib.reload(measurements.awg.ODMR_awg)

from measurements.awg.ODMR_awg import ODMR_awg
from hardware.awg import AWG

awg = AWG()
odmr_awg = ODMR_awg(pulse_generator, time_tagger, microwave, rf, awg)
odmr_awg.edit_traits()

################
### PLOTTING ###
################

# plot TEER_freq_awg
import numpy as np
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
f = np.arange(teer_freq_awg.freq_begin, teer_freq_awg.freq_end, teer_freq_awg.freq_delta)
n = len(f)
plt.plot(f, teer_freq_awg.spin_state[:n] - teer_freq_awg.spin_state[n:2 * n])
plt.xlabel('TEER frequency [Hz]')
plt.ylabel('TEER contrast')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()

# plot TEER_freq_2pi_awg
import numpy as np
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
f = np.arange(teer_freq_2pi_awg.freq_begin, teer_freq_2pi_awg.freq_end, teer_freq_2pi_awg.freq_delta)
n = len(f)
plt.plot(f / 1e6, teer_freq_2pi_awg.spin_state[n:2 * n], linewidth=2.,
         color='b', marker='.', ms=20.0)
plt.plot(f / 1e6, teer_freq_2pi_awg.spin_state[:n], linewidth=2.,
         color='g', marker='.', ms=20.0)
plt.xlabel('TEER frequency [MHz]')
plt.ylabel('TEER contrast')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()

# plot odmr_awg
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
plt.plot(np.arange(odmr_awg.freq_begin, odmr_awg.freq_end, odmr_awg.freq_delta),
         odmr_awg.spin_state)
plt.xlabel('MW frequency [Hz]')
plt.ylabel('NV contrast')
plt.show()

# plot deer_awg
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
plt.figure(1)
plt.plot(np.arange(deer_awg.freq_begin, deer_awg.freq_end, deer_awg.freq_delta),
         deer_awg.spin_state)
plt.xlabel('DEER frequency [Hz]')
plt.ylabel('DEER contrast')
plt.show()

# plot deer_rabi
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(deer_rabi_awg.tau)
plt.plot(deer_rabi_awg.tau, (deer_rabi_awg.spin_state[:n]))
plt.xlabel(' evolution time [ns]')
plt.ylabel('DEER rabi contrast')
plt.show()

# plot deer_hahn_awg
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(deer_hahn_awg.tau)
plt.plot(deer_hahn_awg.tau, (deer_hahn_awg.spin_state[:n] - deer_hahn_awg.spin_state[n:2 * n]))
plt.xlabel('evolution time [ns]')
plt.ylabel('DEER hahn contrast')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()

# plot deer_hahn_awg
from matplotlib import pyplot as plt

plt.switch_backend('TkAGG')
n = len(teer_delay_awg.tau)
plt.plot(teer_delay_awg.tau, (teer_delay_awg.spin_state[:n] - teer_delay_awg.spin_state[n:2 * n]))
plt.xlabel('evolution time [ns]')
plt.ylabel('TEER Delay contrast {a.u.]')
plt.grid(b=True, which='major', color='black', linestyle='--')
plt.show()
