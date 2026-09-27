# -*- coding: utf-8 -*-
"""
Created on Mon Sep 19 15:35:06 2016

@author: kbxu
"""
import copy

import matplotlib.pyplot as plt
import numpy as np

from . import waveform
from hardware.awg import AWG

sampling = 1.0e9
freq_begin = 200e6
freq_end = 250e6
freq_delta = 10e6
half_pi = 25
half_3pi = 75
pi = 50
freq = 250e6
freq_center = 300e6

freq_list = freq_center - np.arange(freq_begin, freq_end, freq_delta)
half_pi = int(half_pi * sampling / 1.0e9)
half_3pi = int(half_3pi * sampling / 1.0e9)
pi = int(pi * sampling / 1.0e9)
RF_tau = 1000
amp = 1
vpp = 1

phase_1 = 0
drive_x = waveform.Sin(0, (freq_center - freq) / sampling, 0, amp)
drive_y = waveform.Sin(0, (freq_center - freq) / sampling, np.pi / 2 + phase_1, amp)
zero = waveform.Idle(1)

waves = []
waves_sum = []
main_seq = waveform.Sequence('TEER_freq.SEQ')
j = 0  # pts_keeper
for i in range(len(freq_list)):
    pulse_temp_x = []
    pulse_temp_y = []
    # The first half pi pulse
    # the first point begins with 0
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = half_pi
    drive_y.duration = half_pi
    x_name = 'X_RA_%03i_1.WFM' % i
    y_name = 'Y_RA_%03i_1.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y]))
    pulse_temp_x = copy.deepcopy(waves[j].pulse_seq)
    pulse_temp_y = copy.deepcopy(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau

    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = RF_tau // 2
    drive_y.duration = RF_tau // 2
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
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    x_name = 'X_RA_%03i_3.WFM' % i
    y_name = 'Y_RA_%03i_3.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))

    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The freq sweeping pi pulse
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    drive_x.freq = freq_list[i] / sampling
    drive_y.freq = freq_list[i] / sampling
    x_name = 'X_RA_%03i_4.WFM' % i
    y_name = 'Y_RA_%03i_4.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))

    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = RF_tau // 2 - pi
    drive_y.duration = RF_tau // 2 - pi
    x_name = 'X_RA_%03i_5.WFM' % i
    y_name = 'Y_RA_%03i_5.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The second half pi pulse
    # the last point ends with 0
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = half_pi
    drive_y.duration = half_pi
    drive_x.freq = (freq_center - freq) / sampling
    drive_y.freq = (freq_center - freq) / sampling
    x_name = 'X_RA_%03i_6.WFM' % i
    y_name = 'Y_RA_%03i_6.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [drive_y, zero]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    sum_name_x = 'sum_x_%03i_1.WFM' % i
    sum_name_y = 'sum_y_%03i_1.WFM' % i
    waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
    waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
    main_seq.append(*waves_sum[-2:], wait=True)

for i in range(len(freq_list)):
    pulse_temp_x = []
    pulse_temp_y = []
    # The first half pi pulse

    # the first point begins with 0
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = half_pi
    drive_y.duration = half_pi
    x_name = 'X_RA_%03i_11.WFM' % i
    y_name = 'Y_RA_%03i_11.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y]))
    pulse_temp_x = copy.deepcopy(waves[j].pulse_seq)
    pulse_temp_y = copy.deepcopy(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau

    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = RF_tau // 2
    drive_y.duration = RF_tau // 2
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
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    x_name = 'X_RA_%03i_33.WFM' % i
    y_name = 'Y_RA_%03i_33.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The freq sweeping pi
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = pi
    drive_y.duration = pi
    drive_x.freq = freq_list[i] / sampling
    drive_y.freq = freq_list[i] / sampling
    x_name = 'X_RA_%03i_44.WFM' % i
    y_name = 'Y_RA_%03i_44.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x]))
    waves.append(waveform.Waveform(y_name, [drive_y]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # Wait tau
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = RF_tau // 2 - pi
    drive_y.duration = RF_tau // 2 - pi
    x_name = 'X_RA_%03i_55.WFM' % i
    y_name = 'Y_RA_%03i_55.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    pulse_temp_x.extend(waves[j].pulse_seq)
    pulse_temp_y.extend(waves[j + 1].pulse_seq)
    j += 2

    # The half 3pi pulse

    # the last point ends with 0
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = half_3pi
    drive_y.duration = half_3pi
    drive_x.freq = (freq_center - freq) / sampling
    drive_y.freq = (freq_center - freq) / sampling
    x_name = 'X_RA_%03i_66.WFM' % i
    y_name = 'Y_RA_%03i_66.WFM' % i
    waves.append(waveform.Waveform(x_name, [drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [drive_y, zero]))
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

# ==============================================================================
for i in range(len(freq_list) - 3):
    waveform.Waveform.plot(waves_sum[i])
#    waveform.Waveform.plot(waves[i])
plt.show()

# ==============================================================================

awg = AWG()
awg.upload(waves_sum)
awg.upload(main_seq)
awg.tell('*WAI')
awg.load('TEER_freq.SEQ')

# AWG.run()
