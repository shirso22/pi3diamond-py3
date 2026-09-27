"""
This module takes care of the upload of measurements to the AWG.

In our programming scheme, the parameters of each measurement, the gui things and the threading are
taken care of by the respective classes in measurements.awg. Here the actual uploads are defined.
That means each method decides, what to do with the given parameters (how to order them to a pulse
sequence) as well as the actual interaction with the awg (aka the uploading) is performed.
HARDWARE CONNECTION TO THE REST OF THE SETUP:
- connect Channel 1, Marker 1 to the time_tagger Laser trigger,
- connect Channel 1, Marker 2 to the time_tagger sequence trigger,
- connect Channel 2, Marker 1 to the actual AOM trigger.
"""

from measurements.awg.waveform import *

sampling = 1.0e9


def upload_rabi(awg, t_ini, t_end, t_delta, laser_on, trigger_delay, decay_ini):
    """
    upload the sequence for rabi measurement into the awg. 
    
    """
    tau = np.arange(t_ini, t_end, t_delta)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1_x = Idle(trigger_delay, marker1=True)
    trigger_delay_1_y = Idle(trigger_delay)
    trigger_delay_2_x = Idle(trigger_delay)
    trigger_delay_2_y = Idle(trigger_delay, marker1=True)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    waves = []
    main_seq = Sequence('RABI.SEQ')
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        if i == len(tau) - 1:
            drive_x = DC(t)
            drive_y = Idle(t)
            x_name = 'X_RABI_%03i.WFM' % i
            y_name = 'Y_RABI_%03i.WFM' % i
            waves.append(Waveform(x_name, [head, drive_x, trigger_delay_1_x, laser_x,
                                           trigger_delay_2_x, sequence_x, tail]))
            waves.append(Waveform(y_name, [head, drive_y, trigger_delay_1_y, laser_y,
                                           trigger_delay_2_y, sequence_y, tail]))
            main_seq.append(*waves[-2:], wait=False)
        else:
            drive_x = DC(t)
            drive_y = Idle(t)
            x_name = 'X_RABI_%03i.WFM' % i
            y_name = 'Y_RABI_%03i.WFM' % i
            waves.append(Waveform(x_name, [head, drive_x, trigger_delay_1_x, laser_x,
                                           trigger_delay_2_x, tail]))
            waves.append(Waveform(y_name, [head, drive_y, trigger_delay_1_y, laser_y,
                                           trigger_delay_2_y, tail]))
            main_seq.append(*waves[-2:], wait=False)
    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('RABI.SEQ')
    awg.tell('*WAI')


def upload_odmr(awg, t_pi, freq_begin, freq_delta, freq_end, freq_carrier, laser_on, trigger_delay,
                decay_ini):
    """
    upload the sequence for odmr measurement into the awg. 
    
    """
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1_x = Idle(trigger_delay, marker1=True)
    trigger_delay_1_y = Idle(trigger_delay)
    trigger_delay_2_x = Idle(trigger_delay)
    trigger_delay_2_y = Idle(trigger_delay, marker1=True)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    tail = Idle(1)
    head = Idle(decay_ini)
    waves = []
    main_seq = Sequence('ODMR.SEQ')
    freq_list = freq_carrier - np.arange(freq_begin, freq_end, freq_delta)
    for i in range(len(freq_list)):
        if i == len(freq_list) - 1:
            drive_x = Sin(t_pi, freq_list[i] / sampling, 0)
            drive_y = Sin(t_pi, freq_list[i] / sampling, np.pi / 2.0)
            x_name = 'X_ODMR_%03i.WFM' % i
            y_name = 'Y_OMDR_%03i.WFM' % i
            waves.append(
                Waveform(x_name, [head, drive_x, trigger_delay_1_x, laser_x, trigger_delay_2_x, sequence_x, tail]))
            waves.append(
                Waveform(y_name, [head, drive_y, trigger_delay_1_y, laser_y, trigger_delay_2_y, sequence_y, tail]))
            main_seq.append(*waves[-2:], wait=False)
        else:
            drive_x = Sin(t_pi, freq_list[i] / sampling, 0)
            drive_y = Sin(t_pi, freq_list[i] / sampling, np.pi / 2.0)
            x_name = 'X_ODMR_%03i.WFM' % i
            y_name = 'Y_OMDR_%03i.WFM' % i
            waves.append(Waveform(x_name, [head, drive_x, trigger_delay_1_x, laser_x, trigger_delay_2_x, tail]))
            waves.append(Waveform(y_name, [head, drive_y, trigger_delay_1_y, laser_y, trigger_delay_2_y, tail]))
            main_seq.append(*waves[-2:], wait=False)
    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('ODMR.SEQ')
    awg.tell('*WAI')


def upload_spin_lock(awg, t_pi_2, t_ini, t_delta, t_end, laser_on, trigger_delay, decay_ini):
    """
    upload the sequence for spin lock measurement into the awg. 
    
    """
    tau = np.arange(t_ini, t_end, t_delta)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1_x = Idle(trigger_delay, marker1=True)
    trigger_delay_1_y = Idle(trigger_delay)
    trigger_delay_2_x = Idle(trigger_delay)
    trigger_delay_2_y = Idle(trigger_delay, marker1=True)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    wait = Idle(10)
    waves = []
    main_seq = Sequence('spinlock.SEQ')
    drive_x_pi2 = DC(t_pi_2)
    drive_y_pi2 = Idle(t_pi_2)
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        if i == len(tau) - 1:
            drive_x = Idle(t)
            drive_y = DC(t)
            x_name = 'X_SpinLock_%03i.WFM' % i
            y_name = 'Y_SpinLock_%03i.WFM' % i
            waves.append(Waveform(x_name,
                                  [head, drive_x_pi2, wait, drive_x, trigger_delay_1_x, laser_x, trigger_delay_2_x,
                                   sequence_x, tail]))
            waves.append(Waveform(y_name,
                                  [head, drive_y_pi2, wait, drive_y, trigger_delay_1_y, laser_y, trigger_delay_2_y,
                                   sequence_y, tail]))
            main_seq.append(*waves[-2:], wait=False)
        else:
            drive_x = Idle(t)
            drive_y = DC(t)
            x_name = 'X_SpinLock_%03i.WFM' % i
            y_name = 'Y_SpinLock_%03i.WFM' % i
            waves.append(Waveform(x_name,
                                  [head, drive_x_pi2, wait, drive_x, trigger_delay_1_x, laser_x, trigger_delay_2_x,
                                   tail]))
            waves.append(Waveform(y_name,
                                  [head, drive_y_pi2, wait, drive_y, trigger_delay_1_y, laser_y, trigger_delay_2_y,
                                   tail]))
            main_seq.append(*waves[-2:], wait=False)
    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('spinlock.SEQ')
    awg.tell('*WAI')


def upload_hahn_echo(awg, t_pi_2, t_pi, t_3pi_2, t_ini, t_delta, t_end, laser_on, trigger_delay,
                     decay_ini):
    """
    upload the sequence for hahn echo into the awg.
    """
    t_pi_2 = int(t_pi_2)
    t_3pi_2 = int(t_3pi_2)
    t_pi = int(t_pi)
    tau = np.arange(t_ini, t_end, t_delta)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1 = Idle(trigger_delay, marker1=True)
    trigger_delay_2 = Idle(trigger_delay)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    drive_x_pi2 = DC(t_pi_2)
    drive_y_pi2 = Idle(t_pi_2)
    drive_x_pi = DC(t_pi)
    drive_y_pi = Idle(t_pi)
    drive_x_3pi2 = DC(t_3pi_2)
    drive_y_3pi2 = Idle(t_3pi_2)
    waves = []
    main_seq = Sequence('hahn.SEQ')

    # pi/2 measurement
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        drive_blank = Idle(t / 2)
        x_name = 'X_hahn_%03i.WFM' % i
        y_name = 'Y_hahn_%03i.WFM' % i
        waves_x = []
        waves_y = []
        waves_x.append(head)
        waves_x.append(drive_x_pi2)
        waves_x.append(drive_blank)
        waves_x.append(drive_x_pi)
        waves_x.append(drive_blank)
        waves_x.append(drive_x_pi2)
        waves_x.append(trigger_delay_1)
        waves_x.append(laser_x)
        waves_x.append(trigger_delay_2)
        waves_x.append(tail)

        waves_y.append(head)
        waves_y.append(drive_y_pi2)
        waves_y.append(drive_blank)
        waves_y.append(drive_y_pi)
        waves_y.append(drive_blank)
        waves_y.append(drive_y_pi2)
        waves_y.append(trigger_delay_2)
        waves_y.append(laser_y)
        waves_y.append(trigger_delay_1)
        waves_y.append(tail)

        waves.append(Waveform(x_name, waves_x))
        waves.append(Waveform(y_name, waves_y))
        main_seq.append(*waves[-2:], wait=False)

    # 3pi/2 measurement    
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        drive_blank = Idle(t / 2)
        x_name = 'X_hahn_%03i.WFM' % (i + len(tau))
        y_name = 'Y_hahn_%03i.WFM' % (i + len(tau))
        waves_x = []
        waves_y = []

        waves_x.append(head)
        waves_x.append(drive_x_pi2)
        waves_x.append(drive_blank)
        waves_x.append(drive_x_pi)
        waves_x.append(drive_blank)
        waves_x.append(drive_x_3pi2)
        waves_x.append(trigger_delay_1)
        waves_x.append(laser_x)
        waves_x.append(trigger_delay_2)
        if i == len(tau) - 1:
            waves_x.append(sequence_x)
            waves_x.append(tail)
        else:
            waves_x.append(tail)

        waves_y.append(head)
        waves_y.append(drive_y_pi2)
        waves_y.append(drive_blank)
        waves_y.append(drive_y_pi)
        waves_y.append(drive_blank)
        waves_y.append(drive_y_3pi2)
        waves_y.append(trigger_delay_2)
        waves_y.append(laser_y)
        waves_y.append(trigger_delay_1)
        if i == len(tau) - 1:
            waves_y.append(sequence_y)
            waves_y.append(tail)
        else:
            waves_y.append(tail)

        waves.append(Waveform(x_name, waves_x))
        waves.append(Waveform(y_name, waves_y))
        main_seq.append(*waves[-2:], wait=False)

    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('hahn.SEQ')
    awg.tell('*WAI')


def upload_xy8(awg, order, t_pi_x, t_pi_2_x, t_3pi_2_x, t_pi_y, t_ini, t_delta, t_end, laser_on,
               trigger_delay, decay_ini):
    """
    upload the sequence for xy8 measurement into the awg.
    
    """
    t_pi_2 = int(t_pi_2_x)
    t_3pi_2 = int(t_3pi_2_x)
    t_pi_x = int(t_pi_x)
    t_pi_y = int(t_pi_y)
    tau = np.arange(t_ini, t_end, t_delta)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1 = Idle(trigger_delay, marker1=True)
    trigger_delay_2 = Idle(trigger_delay)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    drive_x_pi2 = DC(t_pi_2)
    drive_y_pi2 = Idle(t_pi_2)
    drive_x_pi_x = DC(t_pi_x)
    drive_y_pi_x = Idle(t_pi_x)
    drive_x_pi_y = Idle(t_pi_y)
    drive_y_pi_y = DC(t_pi_y)
    drive_x_3pi2 = DC(t_3pi_2)
    drive_y_3pi2 = Idle(t_3pi_2)
    waves = []
    main_seq = Sequence('XY8.SEQ')

    # pi/2 measurement
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        # drive_blank: free evolution time between pi pulses, the total evolution time takes
        # the length of pi pulse into consideration 
        drive_blank_x = Idle(t / (16 * order) - t_pi_x / 2.)
        drive_blank_y = Idle(t / (16 * order) - t_pi_y / 2.)
        waves_1_x = []
        waves_1_y = []
        waves_2_x = []
        waves_2_y = []
        waves_3_x = []
        waves_3_y = []
        pulse_pi_x_ch1 = []
        pulse_pi_y_ch1 = []
        pulse_pi_x_ch2 = []
        pulse_pi_y_ch2 = []
        # the decay ini and the first pi/2
        waves_1_x.append(head)
        waves_1_x.append(drive_x_pi2)

        waves_1_y.append(head)
        waves_1_y.append(drive_y_pi2)

        x_name = 'X_xy8_begin_%03i.WFM' % i
        y_name = 'Y_xy8_begin_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_1_x))
        waves.append(Waveform(y_name, waves_1_y))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        pulse_pi_x_ch1.append(drive_blank_x)
        pulse_pi_x_ch1.append(drive_x_pi_x)
        pulse_pi_x_ch1.append(drive_blank_x)

        pulse_pi_x_ch2.append(drive_blank_x)
        pulse_pi_x_ch2.append(drive_y_pi_x)
        pulse_pi_x_ch2.append(drive_blank_x)

        pulse_pi_y_ch1.append(drive_blank_y)
        pulse_pi_y_ch1.append(drive_x_pi_y)
        pulse_pi_y_ch1.append(drive_blank_y)

        pulse_pi_y_ch2.append(drive_blank_y)
        pulse_pi_y_ch2.append(drive_y_pi_y)
        pulse_pi_y_ch2.append(drive_blank_y)

        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)

        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)

        x_name = 'X_xy8_mid_%03i.WFM' % i
        y_name = 'Y_xy8_mid_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last pi/2 and the laser
        waves_3_x.append(drive_x_pi2)
        waves_3_x.append(trigger_delay_1)
        waves_3_x.append(laser_x)
        waves_3_x.append(trigger_delay_2)
        waves_3_x.append(tail)

        waves_3_y.append(drive_y_pi2)
        waves_3_y.append(trigger_delay_2)
        waves_3_y.append(laser_y)
        waves_3_y.append(trigger_delay_1)
        waves_3_y.append(tail)

        x_name = 'X_xy8_end_%03i.WFM' % i
        y_name = 'Y_xy8_end_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_3_x))
        waves.append(Waveform(y_name, waves_3_y))
        main_seq.append(*waves[-2:], wait=False)

    # 3pi/2 measurement
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        drive_blank_x = Idle(t / (16 * order) - t_pi_x / 2.)
        drive_blank_y = Idle(t / (16 * order) - t_pi_y / 2.)
        waves_1_x = []
        waves_1_y = []
        waves_2_x = []
        waves_2_y = []
        waves_3_x = []
        waves_3_y = []
        pulse_pi_x_ch1 = []
        pulse_pi_y_ch1 = []
        pulse_pi_x_ch2 = []
        pulse_pi_y_ch2 = []

        # the decay ini and the first pi/2
        waves_1_x.append(head)
        waves_1_x.append(drive_x_pi2)

        waves_1_y.append(head)
        waves_1_y.append(drive_y_pi2)

        x_name = 'X_xy8_begin_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_begin_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_1_x))
        waves.append(Waveform(y_name, waves_1_y))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        pulse_pi_x_ch1.append(drive_blank_x)
        pulse_pi_x_ch1.append(drive_x_pi_x)
        pulse_pi_x_ch1.append(drive_blank_x)

        pulse_pi_x_ch2.append(drive_blank_x)
        pulse_pi_x_ch2.append(drive_y_pi_x)
        pulse_pi_x_ch2.append(drive_blank_x)

        pulse_pi_y_ch1.append(drive_blank_y)
        pulse_pi_y_ch1.append(drive_x_pi_y)
        pulse_pi_y_ch1.append(drive_blank_y)

        pulse_pi_y_ch2.append(drive_blank_y)
        pulse_pi_y_ch2.append(drive_y_pi_y)
        pulse_pi_y_ch2.append(drive_blank_y)

        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)

        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)

        x_name = 'X_xy8_mid_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_mid_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last 3pi/2 and the laser
        waves_3_x.append(drive_x_3pi2)
        waves_3_x.append(trigger_delay_1)
        waves_3_x.append(laser_x)
        waves_3_x.append(trigger_delay_2)
        if i == len(tau) - 1:
            waves_3_x.append(sequence_x)
            waves_3_x.append(tail)
        else:
            waves_3_x.append(tail)

        waves_3_y.append(drive_y_3pi2)
        waves_3_y.append(trigger_delay_2)
        waves_3_y.append(laser_y)
        waves_3_y.append(trigger_delay_1)
        if i == len(tau) - 1:
            waves_3_y.append(sequence_y)
            waves_3_y.append(tail)
        else:
            waves_3_y.append(tail)

        x_name = 'X_xy8_end_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_end_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_3_x))
        waves.append(Waveform(y_name, waves_3_y))
        main_seq.append(*waves[-2:], wait=False)

    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('XY8.SEQ')
    awg.tell('*WAI')


def upload_xy8_correlation(awg, order, t_pi_x, t_pi_2_x, t_3pi_2_x, t_pi_y, tau_xy8, t_ini, t_delta,
                           t_end, laser_on, trigger_delay, decay_ini):
    """
    upload the sequence for a xy8 correlation measurement.

    The sequence is XY8-tau-XY8.
    """
    t_pi_2 = int(t_pi_2_x)
    t_3pi_2 = int(t_3pi_2_x)
    t_pi_x = int(t_pi_x)
    t_pi_y = int(t_pi_y)
    tau = np.arange(t_ini, t_end, t_delta)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1 = Idle(trigger_delay, marker1=True)
    trigger_delay_2 = Idle(trigger_delay)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    drive_x_pi2 = DC(t_pi_2)
    drive_y_pi2 = Idle(t_pi_2)
    drive_x_pi_x = DC(t_pi_x)
    drive_y_pi_x = Idle(t_pi_x)
    drive_x_pi_y = Idle(t_pi_y)
    drive_y_pi_y = DC(t_pi_y)
    drive_x_3pi2 = DC(t_3pi_2)
    drive_y_3pi2 = Idle(t_3pi_2)
    waves = []
    main_seq = Sequence('XY8_correlation.SEQ')

    # drive_blank: free evolution time between pi pulses, the total evolution time takes
    # the length of pi pulse into consideration
    drive_blank_x = Idle(tau_xy8 / (16 * order) - t_pi_x / 2.)
    drive_blank_y = Idle(tau_xy8 / (16 * order) - t_pi_y / 2.)

    # pi/2 measurement
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        waves_1_x = []
        waves_1_y = []
        waves_2_x = []
        waves_2_y = []
        waves_3_x = []
        waves_3_y = []
        pulse_pi_x_ch1 = []
        pulse_pi_y_ch1 = []
        pulse_pi_x_ch2 = []
        pulse_pi_y_ch2 = []

        # the decay ini and the first pi/2
        waves_1_x.append(head)
        waves_1_x.append(drive_x_pi2)

        waves_1_y.append(head)
        waves_1_y.append(drive_y_pi2)

        x_name = 'X_xy8_begin_%03i.WFM' % i
        y_name = 'Y_xy8_begin_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_1_x))
        waves.append(Waveform(y_name, waves_1_y))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        pulse_pi_x_ch1.append(drive_blank_x)
        pulse_pi_x_ch1.append(drive_x_pi_x)
        pulse_pi_x_ch1.append(drive_blank_x)

        pulse_pi_x_ch2.append(drive_blank_x)
        pulse_pi_x_ch2.append(drive_y_pi_x)
        pulse_pi_x_ch2.append(drive_blank_x)

        pulse_pi_y_ch1.append(drive_blank_y)
        pulse_pi_y_ch1.append(drive_x_pi_y)
        pulse_pi_y_ch1.append(drive_blank_y)

        pulse_pi_y_ch2.append(drive_blank_y)
        pulse_pi_y_ch2.append(drive_y_pi_y)
        pulse_pi_y_ch2.append(drive_blank_y)

        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)

        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)

        x_name = 'X_xy8_mid_%03i.WFM' % i
        y_name = 'Y_xy8_mid_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last pi/2
        x_name = 'X_xy8_end_%03i.WFM' % i
        y_name = 'Y_xy8_end_%03i.WFM' % i
        waves.append(Waveform(x_name, [drive_x_pi2]))
        waves.append(Waveform(y_name, [drive_y_pi2]))
        main_seq.append(*waves[-2:], wait=False)

        # wait for tau
        x_name = 'X_xy8_wait_%03i.WFM' % i
        y_name = 'Y_xy8_wait_%03i.WFM' % i
        waves.append(Waveform(x_name, [Idle(t)]))
        waves.append(Waveform(y_name, [Idle(t)]))
        main_seq.append(*waves[-2:], wait=False)

        # the first pi/2
        x_name = 'X_xy8_2_begin_%03i.WFM' % i
        y_name = 'Y_xy8_2_begin_%03i.WFM' % i
        waves.append(Waveform(x_name, [drive_x_pi2]))
        waves.append(Waveform(y_name, [drive_y_pi2]))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        x_name = 'X_xy8_2_mid_%03i.WFM' % i
        y_name = 'Y_xy8_2_mid_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last pi/2 and the laser
        waves_3_x.append(drive_x_pi2)
        waves_3_x.append(trigger_delay_1)
        waves_3_x.append(laser_x)
        waves_3_x.append(trigger_delay_2)
        waves_3_x.append(tail)

        waves_3_y.append(drive_y_pi2)
        waves_3_y.append(trigger_delay_2)
        waves_3_y.append(laser_y)
        waves_3_y.append(trigger_delay_1)
        waves_3_y.append(tail)

        x_name = 'X_xy8_2_end_%03i.WFM' % i
        y_name = 'Y_xy8_2_end_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_3_x))
        waves.append(Waveform(y_name, waves_3_y))
        main_seq.append(*waves[-2:], wait=False)

    # 3pi/2 measurement
    for i, t in enumerate(tau):
        t = int(t * sampling / 1.0e9)
        waves_1_x = []
        waves_1_y = []
        waves_2_x = []
        waves_2_y = []
        waves_3_x = []
        waves_3_y = []
        pulse_pi_x_ch1 = []
        pulse_pi_y_ch1 = []
        pulse_pi_x_ch2 = []
        pulse_pi_y_ch2 = []

        # the decay ini and the first pi/2
        waves_1_x.append(head)
        waves_1_x.append(drive_x_pi2)

        waves_1_y.append(head)
        waves_1_y.append(drive_y_pi2)

        x_name = 'X_xy8_begin_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_begin_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_1_x))
        waves.append(Waveform(y_name, waves_1_y))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        pulse_pi_x_ch1.append(drive_blank_x)
        pulse_pi_x_ch1.append(drive_x_pi_x)
        pulse_pi_x_ch1.append(drive_blank_x)

        pulse_pi_x_ch2.append(drive_blank_x)
        pulse_pi_x_ch2.append(drive_y_pi_x)
        pulse_pi_x_ch2.append(drive_blank_x)

        pulse_pi_y_ch1.append(drive_blank_y)
        pulse_pi_y_ch1.append(drive_x_pi_y)
        pulse_pi_y_ch1.append(drive_blank_y)

        pulse_pi_y_ch2.append(drive_blank_y)
        pulse_pi_y_ch2.append(drive_y_pi_y)
        pulse_pi_y_ch2.append(drive_blank_y)

        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_x.extend(pulse_pi_y_ch1)
        waves_2_x.extend(pulse_pi_x_ch1)

        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)
        waves_2_y.extend(pulse_pi_y_ch2)
        waves_2_y.extend(pulse_pi_x_ch2)

        x_name = 'X_xy8_mid_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_mid_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last pi/2
        x_name = 'X_xy8_end_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_end_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, [drive_x_pi2]))
        waves.append(Waveform(y_name, [drive_y_pi2]))
        main_seq.append(*waves[-2:], wait=False)

        # wait for tau
        x_name = 'X_xy8_wait_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_wait_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, [Idle(t)]))
        waves.append(Waveform(y_name, [Idle(t)]))
        main_seq.append(*waves[-2:], wait=False)

        # the first pi/2
        x_name = 'X_xy8_2_begin_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_2_begin_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, [drive_x_pi2]))
        waves.append(Waveform(y_name, [drive_y_pi2]))
        main_seq.append(*waves[-2:], wait=False)

        # the 8 pi pulses
        x_name = 'X_xy8_2_mid_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_2_mid_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the last 3pi/2 and the laser
        waves_3_x.append(drive_x_3pi2)
        waves_3_x.append(trigger_delay_1)
        waves_3_x.append(laser_x)
        waves_3_x.append(trigger_delay_2)
        if i == len(tau) - 1:
            waves_3_x.append(sequence_x)
            waves_3_x.append(tail)
        else:
            waves_3_x.append(tail)

        waves_3_y.append(drive_y_3pi2)
        waves_3_y.append(trigger_delay_2)
        waves_3_y.append(laser_y)
        waves_3_y.append(trigger_delay_1)
        if i == len(tau) - 1:
            waves_3_y.append(sequence_y)
            waves_3_y.append(tail)
        else:
            waves_3_y.append(tail)

        x_name = 'X_xy8_2_end_%03i.WFM' % (i + len(tau))
        y_name = 'Y_xy8_2_end_%03i.WFM' % (i + len(tau))
        waves.append(Waveform(x_name, waves_3_x))
        waves.append(Waveform(y_name, waves_3_y))
        main_seq.append(*waves[-2:], wait=False)

    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('XY8_correlation.SEQ')
    awg.tell('*WAI')


def upload_pi_calibrate(awg, order, t_pi_x, pulse_delay, laser_on, trigger_delay, decay_ini):
    """
    upload the sequence for pi pulse length calibration measurement into the awg.
    """
    t_pi_x = int(t_pi_x)
    pulse_delay = int(pulse_delay)
    laser_x = Idle(laser_on - trigger_delay, marker1=True)
    laser_y = Idle(laser_on - trigger_delay, marker1=True)
    trigger_delay_1 = Idle(trigger_delay, marker1=True)
    trigger_delay_2 = Idle(trigger_delay)
    sequence_x = Idle(100, marker2=True)
    sequence_y = Idle(100)
    head = Idle(decay_ini)
    tail = Idle(1)
    pi_delay = Idle(pulse_delay)
    drive_x_pi_x = DC(t_pi_x)
    drive_y_pi_x = Idle(t_pi_x)

    waves = []
    main_seq = Sequence('pulse_length.SEQ')

    for i in range(order):
        waves_1_x = []
        waves_1_y = []
        waves_2_x = []
        waves_2_y = []
        waves_3_x = []
        waves_3_y = []
        pulse_pi_x_ch1 = []
        pulse_pi_x_ch2 = []

        # the decay ini
        waves_1_x.append(head)
        waves_1_y.append(head)

        x_name = 'X_begin_%03i.WFM' % i
        y_name = 'Y_begin_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_1_x))
        waves.append(Waveform(y_name, waves_1_y))
        main_seq.append(*waves[-2:], wait=False)

        # repeat the pi pulse N times
        pulse_pi_x_ch1.append(drive_x_pi_x)
        pulse_pi_x_ch1.append(pi_delay)

        pulse_pi_x_ch2.append(drive_y_pi_x)
        pulse_pi_x_ch2.append(pi_delay)

        waves_2_x.extend(pulse_pi_x_ch1)
        waves_2_y.extend(pulse_pi_x_ch2)

        x_name = 'X_mid_%03i.WFM' % i
        y_name = 'Y_mid_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_2_x))
        waves.append(Waveform(y_name, waves_2_y))
        main_seq.append(*waves[-2:], repeat=order, wait=False)

        # the end
        waves_3_x.append(trigger_delay_1)
        waves_3_x.append(laser_x)
        waves_3_x.append(trigger_delay_2)
        if i == order - 1:
            waves_3_x.append(sequence_x)
            waves_3_x.append(tail)
        else:
            waves_3_x.append(tail)

        waves_3_y.append(trigger_delay_2)
        waves_3_y.append(laser_y)
        waves_3_y.append(trigger_delay_1)
        if i == order - 1:
            waves_3_y.append(sequence_y)
            waves_3_y.append(tail)
        else:
            waves_3_y.append(tail)

        x_name = 'X_end_%03i.WFM' % i
        y_name = 'Y_end_%03i.WFM' % i
        waves.append(Waveform(x_name, waves_3_x))
        waves.append(Waveform(y_name, waves_3_y))
        main_seq.append(*waves[-2:], wait=False)

    awg.upload(waves)
    awg.upload(main_seq)
    awg.tell('*WAI')
    awg.load('pulse_length.SEQ')
    awg.tell('*WAI')
