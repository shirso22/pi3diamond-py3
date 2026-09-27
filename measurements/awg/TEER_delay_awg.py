"""
TEER measurement 
varying the delay of the RF pi pulse
"""
import copy

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

import measurements.awg.waveform as waveform
from measurements.awg.DEER_Hahn_awg import DEER_Hahn_awg
from measurements.awg.rabi_awg import Rabi_awg
from .waveform import *


class TEER_delay_awg(Rabi_awg):
    """Defines a TEER measurement with both pi/2 and 3pi/2 readout pulse."""

    sequence_delay = Range(low=0., high=1200., value=400.)
    RF_tau = Range(low=1, high=20e9, value=1000, desc='time [ns]', label='RF Tau [ns]', mode='text', auto_set=False,
                   enter_set=True)
    NV_tau = Range(low=1, high=20e9, value=1000, desc='time [ns]', label='NV Tau [ns]', mode='text', auto_set=False,
                   enter_set=True)
    RF_t_pi2 = Range(low=1., high=1e6, value=25., desc='pi/2 pulse length', label='RF pi/2 [ns]',
                     mode='text', auto_set=False, enter_set=True)
    RF_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    RF_t_3pi2 = Range(low=1., high=1e6, value=100., desc='3pi/2 pulse length', label='RF 3pi/2 [ns]',
                      mode='text', auto_set=False, enter_set=True)
    rf_power = Range(low=-100., high=25., value=-20, desc='rf power', label='RF power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    RF_t_pi_2 = Range(low=1., high=1e6, value=50., desc='second RF pi pulse length', label='second RF pi [ns]',
                      mode='text', auto_set=False, enter_set=True)
    freq_2 = Range(low=1, high=20e9, value=300e6, desc='rf frequency [Hz]', label='second RF freq [Hz]',
                   mode='text', auto_set=False, enter_set=True,
                   editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                     format_str='%.5e'))

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setOutput(self.rf_power, self.freq_center)
        self.rf._write('SOUR:DM:IQ:STAT ON')
        self.prepare_awg()

    def prepare_awg(self):
        sampling = 1.0e9
        half_pi = self.RF_t_pi2
        half_3pi = self.RF_t_3pi2
        pi = self.RF_t_pi
        freq = self.freq
        freq_center = self.freq_center
        freq_2 = self.freq_2
        tau = self.tau

        half_pi = int(half_pi * sampling / 1.0e9)
        half_3pi = int(half_3pi * sampling / 1.0e9)
        pi = int(pi * sampling / 1.0e9)
        RF_tau = self.RF_tau
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
            t_blank = self.laser + self.NV_tau / 2. + self.mw_x_t_pi2 + self.sequence_delay
            self.waves = []
            self.waves_sum = []
            self.main_seq = Sequence('TEER_2.SEQ')
            j = 0  # pts_keeper
            for i, t in enumerate(tau):
                t = int(t * sampling / 1.0e9)
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
                drive_x.duration = RF_tau / 2
                drive_y.duration = RF_tau / 2
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

                # The delay for the second RF pi pulse
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t
                drive_y.duration = t
                x_name = 'X_RA_%03i_4.WFM' % i
                y_name = 'Y_RA_%03i_4.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2
                # The second RF pi pulse
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = pi
                drive_y.duration = pi
                drive_x.freq = (freq_center - freq_2) / sampling
                drive_y.freq = (freq_center - freq_2) / sampling
                x_name = 'X_RA_%03i_5.WFM' % i
                y_name = 'Y_RA_%03i_5.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = RF_tau / 2 - pi - t
                drive_y.duration = RF_tau / 2 - pi - t
                x_name = 'X_RA_%03i_6.WFM' % i
                y_name = 'Y_RA_%03i_6.WFM' % i
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
                drive_x.freq = (freq_center - freq) / sampling
                drive_y.freq = (freq_center - freq) / sampling
                x_name = 'X_RA_%03i_7.WFM' % i
                y_name = 'Y_RA_%03i_7.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x, zero]))
                self.waves.append(waveform.Waveform(y_name, [drive_y, zero]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                sum_name_x = 'sum_x_%03i_1.WFM' % i
                sum_name_y = 'sum_y_%03i_1.WFM' % i
                self.waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
                self.waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
                self.main_seq.append(*self.waves_sum[-2:], wait=True)

            for i, t in enumerate(self.tau):
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
                drive_x.duration = RF_tau / 2
                drive_y.duration = RF_tau / 2
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

                # The delay for the second RF pi pulse
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = t
                drive_y.duration = t
                x_name = 'X_RA_%03i_44.WFM' % i
                y_name = 'Y_RA_%03i_44.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # The second RF pi pulse
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = pi
                drive_y.duration = pi
                drive_x.freq = (freq_center - freq_2) / sampling
                drive_y.freq = (freq_center - freq_2) / sampling
                x_name = 'X_RA_%03i_55.WFM' % i
                y_name = 'Y_RA_%03i_55.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x]))
                self.waves.append(waveform.Waveform(y_name, [drive_y]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # Wait tau
                drive_x.amp = 0
                drive_y.amp = 0
                drive_x.duration = RF_tau / 2 - pi - t
                drive_y.duration = RF_tau / 2 - pi - t
                x_name = 'X_RA_%03i_66.WFM' % i
                y_name = 'Y_RA_%03i_66.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [zero, drive_x, zero]))
                self.waves.append(waveform.Waveform(y_name, [zero, drive_y, zero]))
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
                drive_x.freq = (freq_center - freq) / sampling
                drive_y.freq = (freq_center - freq) / sampling
                x_name = 'X_RA_%03i_77.WFM' % i
                y_name = 'Y_RA_%03i_77.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [drive_x, zero]))
                self.waves.append(waveform.Waveform(y_name, [drive_y, zero]))
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
            self.AWG.load('TEER_2.SEQ')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser

        trigger_delay = self.trigger_delay

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        NV_tau = self.NV_tau
        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(tau)):
                sequence.append(([], decay_init))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append(([], 0.5 * NV_tau - trigger_delay - 100))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay))
                sequence.append((['microwave', 'rf'], mw_x_t_pi))
                sequence.append((['rf'], 0.5 * NV_tau))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append((['detect', 'aom'], laser))

            for i in range(len(tau)):
                sequence.append(([], decay_init))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append(([], 0.5 * NV_tau - trigger_delay - 100))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay))
                sequence.append((['microwave', 'rf'], mw_x_t_pi))
                sequence.append((['rf'], 0.5 * NV_tau))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append((['detect', 'aom'], laser))
            sequence += [(['sequence'], 100)]
            return sequence
        else:
            sequence = []
            # INSERT SEQUENCE HERE
            return sequence

    get_set_items = DEER_Hahn_awg.get_set_items + ['RF_t_pi_2', 'RF_tau', 'freq_2']

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
                              Tabbed(VGroup(HGroup(Item('wavegenerator', style='custom',
                                                        enabled_when='state != "run"'),
                                                   Item('reload', width=20),
                                                   ),
                                            HGroup(Item('mw_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('NV_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('RF_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('RF_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('RF_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('RF_t_pi_2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('RF_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_center', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('freq', width=20,
                                                        enabled_when='state != "run"')
                                                   ),
                                            HGroup(Item('trigger_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('amp', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('vpp', width=20,
                                                        enabled_when='state != "run"'),
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
                                            HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='analysis'),
                                     ),
                              ),
                       title='TEER delay AWG Measurement',
                       )
