# -*- coding: utf-8 -*-
"""

"""

import numpy as np

from . import waveform
from hardware.awg import AWG

# ==============================================================================
# Test waveform upload and output
# ==============================================================================


# initial parameters

zero = waveform.Idle(1)
waves = []
sampling = 1.0e9
freq = 10e6
freq_center = 0e6
amp = 1
phase_1 = 0
tau_begin = 10
tau_end = 50
tau_delta = 10
vpp = 0.5

# generate the waveform
waves = []
main_seq = waveform.Sequence('RABI.SEQ')
drive_x = waveform.Sin(0, (freq - freq_center) / sampling, 0, amp)
drive_y = waveform.Sin(0, (freq - freq_center) / sampling, np.pi / 2 + phase_1, amp)
tau = np.arange(tau_begin, tau_end, tau_delta)

for i, t in enumerate(tau):
    t = int(t * sampling / 1.0e9)

    drive_x.duration = t
    drive_y.duration = t
    x_name = 'X_RA_%03i.WFM' % i
    y_name = 'Y_RA_%03i.WFM' % i
    waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
    waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
    main_seq.append(*waves[-2:], wait=True)
for w in waves:
    w.join()

# waveform.Waveform.plot(waves[15])


# prepare the awg
awg = AWG()
awg.stop()
awg.set_output(0b0000)
awg.delete_all()
awg.upload(waves)
awg.upload(main_seq)
awg.tell('*WAI')
awg.load('RABI.SEQ')
awg.set_vpp(vpp)
awg.set_sample(sampling / 1.0e9)
awg.set_mode('S')
awg.set_output(0b0011)

# ==============================================================================
# thefile = open('waveform.txt', 'w')   
# for item in waves:
#   thefile.write("%s\n" % item)
# ==============================================================================
# ==============================================================================
# i = 0
# for p in main_seq:
#     i += p.duration
#     plt.plot([i,i], [-1,1], 'r--')
# plt.step(np.arange(len(wave)) + 1, wave, 'k')
# plt.xlim((0,len(wave)))
# plt.ylim((-1,1))
# plt.plot((0,len(wave)),(0,0), 'k--')
# plt.show()
# ==============================================================================


# from ftplib import FTP   #加载ftp模块
# ftp=FTP()         #设置变量
# ftp.set_debuglevel(2)   #打开调试级别2，显示详细信息
# ftp.connect("169.254.237.87","4001")
