# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:52:25 2016

@author: kbxu
"""

import numpy as np

# from waveform import *
from . import waveform
from hardware.awg import AWG

zero = waveform.Idle(1)
waves = []
sampling = 1.0e9
freq = 100e6
freq_center = 90e6
amp = 1
phase_1 = 0
tau_begin = 30
tau_end = 100
tau_delta = 10
half_pi = 30
vpp = 0.5
tau = np.arange(tau_begin, tau_end, tau_delta)
phase = tau * (freq - freq_center) / sampling

tau_begin = int(tau_begin * sampling / 1.0e9)
tau_delta = int(tau_delta * sampling / 1.0e9)
half_pi = int(half_pi * sampling / 1.0e9)

# generate the waveform 
main_seq = waveform.Sequence('FID.SEQ')
drive_x = waveform.Sin(0, (freq - freq_center) / sampling, 0, amp)
drive_y = waveform.Sin(0, (freq - freq_center) / sampling, np.pi / 2 + phase_1, amp)

for i, t in enumerate(tau):
    #    t = int(t * sampling / 1.0e9)
    # The first half pi pulse
    drive_x.phase = 0
    drive_y.phase = np.pi / 2
    drive_x.duration = half_pi
    drive_y.duration = half_pi
    x_name = 'X_RA_%03i_1.WFM' % i
    y_name = 'Y_RA_%03i_1.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    main_seq.append(*waves[-2:], wait=False)

    # Wait beginning   
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = tau_begin
    drive_y.duration = tau_begin
    x_name = 'X_RA_%03i_2.WFM' % i
    y_name = 'Y_RA_%03i_2.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    main_seq.append(*waves[-2:], wait=False)

    # Wait tau
    drive_x.amp = 0
    drive_y.amp = 0
    drive_x.duration = tau_delta
    drive_y.duration = tau_delta
    x_name = 'X_RA_%03i_3.WFM' % i
    y_name = 'Y_RA_%03i_3.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    main_seq.append(*waves[-2:], wait=False, repeat=i + 1)

    # The second half pi pulse 
    drive_x.amp = 1
    drive_y.amp = 1
    drive_x.phase = phase[i]
    drive_y.phase = phase[i] + np.pi / 2
    drive_x.duration = half_pi
    drive_y.duration = half_pi
    x_name = 'X_RA_%03i_4.WFM' % i
    y_name = 'Y_RA_%03i_4.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    main_seq.append(*waves[-2:], wait=False)

for w in waves:
    w.join()

# for i in range(4):
#  waveform.Waveform.plot(waves[i])

# plt.show()


awg = AWG()
awg.stop()
awg.set_output(0b0000)
awg.delete_all()
awg.upload(waves)
awg.upload(main_seq)
awg.tell('*WAI')
awg.load('FID.SEQ')
awg.set_vpp(vpp)
awg.set_sample(sampling / 1.0e9)
awg.set_mode('S')
awg.set_output(0b0011)
awg.stop()
