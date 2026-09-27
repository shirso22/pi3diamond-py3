# -*- coding: utf-8 -*-
"""
Created on Fri Jul 01 11:55:49 2016

@author: kbxu
"""

"""
Classes to conduct a Hahn measurement.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
Alongside to recieve them from global_vars.py
See rabi.py as example.
TODO: On the fly evaluation, i.e. subtracting the two pulse sequences and evaluation of the latter.
"""

import copy

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

import measurements.awg.waveform as waveform
from measurements.awg.rabi_awg import Rabi_awg
from .waveform import *


class Hahn3pi2_awg(Rabi_awg):
    """Defines a Hahn-Echo measurement with both pi/2 and 3pi/2 readout pulse."""

    sequence_delay = Range(low=0., high=1200., value=400.)

    def prepare_awg(self):
        sampling = 1.0e9
        tau_begin = self.tau_begin
        tau_end = self.tau_end
        tau_delta = self.tau_delta
        half_pi = self.mw_x_t_pi2
        half_3pi = self.mw_x_t_3pi2
        pi = self.mw_x_t_pi
        freq = self.freq
        freq_center = self.freq_center
        tau = self.tau

        tau_begin = int(tau_begin * sampling / 1.0e9)
        tau_delta = int(tau_delta * sampling / 1.0e9)
        half_pi = int(half_pi * sampling / 1.0e9)
        half_3pi = int(half_3pi * sampling / 1.0e9)
        pi = int(pi * sampling / 1.0e9)

        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.delete_all()
            if self.phase:
                phase_1 = self.phase_1
            else:
                phase_1 = 0
            drive_x = Sin(0, (self.freq_center - self.freq) / sampling, 0, self.amp)
            drive_y = Sin(0, (self.freq_center - self.freq) / sampling, np.pi / 2 + phase_1, self.amp)
            zero = Idle(1)
            zeros = Idle(250)
            t_blank = self.laser + self.sequence_delay
            self.waves = []
            self.waves_sum = []
            self.main_seq = Sequence('Hahn.SEQ')
            j = 0  # pts_keeper
            for i, t in enumerate(tau):
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
                self.waves.append(waveform.Waveform(x_name, [zero, drive_x]))
                self.waves.append(waveform.Waveform(y_name, [zero, drive_y]))
                pulse_temp_x = copy.deepcopy(self.waves[j].pulse_seq)
                pulse_temp_y = copy.deepcopy(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau

                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t / 2
                drive_y.duration = t / 2
                x_name = 'X_RA_%03i_2.WFM' % i
                y_name = 'Y_RA_%03i_2.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
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
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t / 2
                drive_y.duration = t / 2
                x_name = 'X_RA_%03i_4.WFM' % i
                y_name = 'Y_RA_%03i_4.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # The second half pi pulse
                # the last point ends with 0
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = half_pi
                drive_y.duration = half_pi
                x_name = 'X_RA_%03i_5.WFM' % i
                y_name = 'Y_RA_%03i_5.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x, zeros]))
                self.waves.append(waveform.Waveform(y_name, [drive_y, zeros]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                sum_name_x = 'sum_x_%03i_1.WFM' % i
                sum_name_y = 'sum_y_%03i_1.WFM' % i
                self.waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
                self.waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
                self.main_seq.append(*self.waves_sum[-2:], wait=True)

            for i, t in enumerate(tau):
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
                self.waves.append(waveform.Waveform(x_name, [zero, drive_x]))
                self.waves.append(waveform.Waveform(y_name, [zero, drive_y]))
                pulse_temp_x = copy.deepcopy(self.waves[j].pulse_seq)
                pulse_temp_y = copy.deepcopy(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau

                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t / 2
                drive_y.duration = t / 2
                x_name = 'X_RA_%03i_22.WFM' % i
                y_name = 'Y_RA_%03i_22.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
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
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t / 2
                drive_y.duration = t / 2
                x_name = 'X_RA_%03i_44.WFM' % i
                y_name = 'Y_RA_%03i_44.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # The half 3pi pulse

                # the last point ends with 0
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = half_3pi
                drive_y.duration = half_3pi
                x_name = 'X_RA_%03i_55.WFM' % i
                y_name = 'Y_RA_%03i_55.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x, zeros]))
                self.waves.append(waveform.Waveform(y_name, [drive_y, zeros]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                sum_name_x = 'sum_x_%03i_2.WFM' % i
                sum_name_y = 'sum_y_%03i_2.WFM' % i
                self.waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
                self.waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
                self.main_seq.append(*self.waves_sum[-2:], wait=True)

            add_marker(self.waves_sum, self.main_seq, t_blank)
            self.AWG.upload(self.waves_sum)
            self.AWG.upload(self.main_seq)
            self.AWG.tell('*WAI')
            self.AWG.load('Hahn.SEQ')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        t_switch_1 = np.arange(len(tau))
        t_switch_2 = np.arange(len(tau))
        aom_delay = self.aom_delay
        for i in range(len(tau)):
            t_switch_1[i] = 2 * self.mw_x_t_pi2 + self.mw_x_t_pi + self.tau[i]
            t_switch_2[i] = self.mw_x_t_pi2 + self.mw_x_t_3pi2 + self.mw_x_t_pi + self.tau[i]

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2

        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(tau)):
                sequence.append(([], decay_init))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], t_switch_1[i] + aom_delay))
                sequence.append((['detect', 'aom'], laser))

            for i in range(len(tau)):
                sequence.append(([], decay_init))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], t_switch_2[i] + aom_delay))
                sequence.append((['detect', 'aom'], laser))

            sequence += [(['sequence'], 100)]
            return sequence
        else:
            sequence = []
            # INSERT SEQUENCE HERE
            return sequence

    get_set_items = Rabi_awg.get_set_items + ['mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f',
                                          width=-60),
                                     Item('stop_time', format_str='%.f', width=-60),
                                     Item('stop_counts', width=-60),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(HGroup(Item('wavegenerator', style='custom', enabled_when='state != "run"'),
                                                   Item('reload', width=20, enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_center', width=20, enabled_when='state != "run"'),
                                                   Item('freq', width=20, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('aom_delay', width=-80, enabled_when='state != "run"'),
                                                   Item('amp', width=20, enabled_when='state != "run"'),
                                                   Item('vpp', width=20, enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'
                                            ),
                                     VGroup(HGroup(Item('record_length', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
                              ),
                       title='Hahn-Echo_awg 3pi/2 Measurement',
                       )
