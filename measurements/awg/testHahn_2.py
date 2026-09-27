# -*- coding: utf-8 -*-
"""
Created on Mon Jul 04 11:50:05 2016

@author: kbxu
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Jun 30 18:00:39 2016

@author: kbxu
"""

import matplotlib.pyplot as plt
import numpy as np

# from waveform import *
from . import waveform
from hardware.awg import AWG

vpp = 1
zero = waveform.Idle(1)
waves = []
sampling = 1.0e9
freq = 100e6
freq_center = 90e6
amp = 1
phase_1 = 0
tau_begin = 200
tau_end = 300
tau_delta = 20
half_pi = 30
half_3pi = 90
pi = 60
t_read = 400
n_read = t_read // 10

waves_sum = []

tau = np.arange(tau_begin, tau_end, tau_delta)
phase = 2 * np.pi * tau * (freq - freq_center) / sampling + 2 * np.pi * half_pi * (freq - freq_center) / sampling
phase_2 = 2 * 2 * np.pi * tau * (freq - freq_center) / sampling + 2 * np.pi * (half_pi + pi) * (
        freq - freq_center) / sampling
print(tau)
print(phase)

tau_begin = int(tau_begin * sampling / 1.0e9)
tau_delta = int(tau_delta * sampling / 1.0e9)
half_pi = int(half_pi * sampling / 1.0e9)
half_3pi = int(half_3pi * sampling / 1.0e9)
pi = int(pi * sampling / 1.0e9)
read_time = int(10 * sampling / 1.0e9)

# generate the waveform
main_seq = waveform.Sequence('Hahn.SEQ')
drive_x = waveform.Sin(0, (freq - freq_center) / sampling, 0, amp)
drive_y = waveform.Sin(0, (freq - freq_center) / sampling, np.pi / 2 + phase_1, amp)
n_pts = len(tau)
j = 0  # pts_keeper

for i, t in enumerate(tau):
    pulse_temp_x = []
    pulse_temp_y = []
    # The first half pi pulse
    if i == 0:
        # the first point begins with 0
        drive_x.phase = 0
        drive_y.phase = np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_1.WFM' % i
        y_name = 'Y_RA_%03i_1.WFM' % i
        waves.append(waveform.Waveform(x_name, [zero, drive_x]))
        waves.append(waveform.Waveform(y_name, [zero, drive_y]))
        pulse_temp_x = waves[j].pulse_seq
        pulse_temp_y = waves[j + 1].pulse_seq
        j += 2
    else:
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = 0
        drive_y.phase = np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_1.WFM' % i
        y_name = 'Y_RA_%03i_1.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x]))
        waves.append(waveform.Waveform(y_name, [drive_y]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2

    # Wait tau

    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = t
    drive_y.duration = t
    x_name = 'X_RA_%03i_2.WFM' % i
    y_name = 'Y_RA_%03i_2.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The pi pulse
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = phase[i]
    drive_y.phase = phase[i] + np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    x_name = 'X_RA_%03i_3.WFM' % i
    y_name = 'Y_RA_%03i_3.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = t
    drive_y.duration = t
    x_name = 'X_RA_%03i_4.WFM' % i
    y_name = 'Y_RA_%03i_4.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The second half pi pulse
    if i == len(tau) - 1:
        # the last point ends with 0
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = phase_2[i]
        drive_y.phase = phase_2[i] + np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_5.WFM' % i
        y_name = 'Y_RA_%03i_5.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x, zero]))
        waves.append(waveform.Waveform(y_name, [drive_y, zero]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2
    else:
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = phase_2[i]
        drive_y.phase = phase_2[i] + np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_5.WFM' % i
        y_name = 'Y_RA_%03i_5.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x]))
        waves.append(waveform.Waveform(y_name, [drive_y]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2
    sum_name_x = 'sum_x_%03i_1.WFM' % i
    sum_name_y = 'sum_y_%03i_1.WFM' % i
    waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
    waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
    main_seq.append(*waves_sum[-2:], wait=True)

for i, t in enumerate(tau):
    pulse_temp_x = []
    pulse_temp_y = []
    # The first half pi pulse
    if i == 0:
        # the first point begins with 0
        drive_x.phase = 0
        drive_y.phase = np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_11.WFM' % i
        y_name = 'Y_RA_%03i_11.WFM' % i
        waves.append(waveform.Waveform(x_name, [zero, drive_x]))
        waves.append(waveform.Waveform(y_name, [zero, drive_y]))
        pulse_temp_x = waves[j].pulse_seq
        pulse_temp_y = waves[j + 1].pulse_seq
        j += 2
    else:
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = 0
        drive_y.phase = np.pi / 2
        drive_x.duration = half_pi
        drive_y.duration = half_pi
        x_name = 'X_RA_%03i_11.WFM' % i
        y_name = 'Y_RA_%03i_11.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x]))
        waves.append(waveform.Waveform(y_name, [drive_y]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2

    # Wait tau

    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = t
    drive_y.duration = t
    x_name = 'X_RA_%03i_22.WFM' % i
    y_name = 'Y_RA_%03i_22.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The pi pulse
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = phase[i]
    drive_y.phase = phase[i] + np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    x_name = 'X_RA_%03i_33.WFM' % i
    y_name = 'Y_RA_%03i_33.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = t
    drive_y.duration = t
    x_name = 'X_RA_%03i_44.WFM' % i
    y_name = 'Y_RA_%03i_44.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The half 3pi pulse
    if i == len(tau) - 1:
        # the last point ends with 0
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = phase_2[i]
        drive_y.phase = phase_2[i] + np.pi / 2
        drive_x.duration = half_3pi
        drive_y.duration = half_3pi
        x_name = 'X_RA_%03i_55.WFM' % i
        y_name = 'Y_RA_%03i_55.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x, zero]))
        waves.append(waveform.Waveform(y_name, [drive_y, zero]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2
    else:
        drive_x.amp = 1
        drive_y.amp = 1
        drive_x.phase = phase_2[i]
        drive_y.phase = phase_2[i] + np.pi / 2
        drive_x.duration = half_3pi
        drive_y.duration = half_3pi
        x_name = 'X_RA_%03i_55.WFM' % i
        y_name = 'Y_RA_%03i_55.WFM' % i
        waves.append(waveform.Waveform(x_name, [drive_x]))
        waves.append(waveform.Waveform(y_name, [drive_y]))
        pulse_temp_x.extend(waves[j].pulse_seq)
        pulse_temp_y.extend(waves[j + 1].pulse_seq)
        j += 2

    sum_name_x = 'sum_x_%03i_2.WFM' % i
    sum_name_y = 'sum_y_%03i_2.WFM' % i
    waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
    waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
    main_seq.append(*waves_sum[-2:], wait=True)

for w in waves:
    w.join()

for i in range(2):
    waveform.Waveform.plot(waves_sum[i])
    waveform.Waveform.plot(waves[i])
plt.show()

awg = AWG()
awg.stop()
awg.set_output(0b0000)
awg.delete_all()
awg.upload(waves_sum)
awg.upload(main_seq)
awg.tell('*WAI')
awg.load('Hahn.SEQ')
awg.set_vpp(vpp)
awg.set_sample(sampling / 1.0e9)
awg.set_mode('S')
awg.set_output(0b0011)
awg.stop()
