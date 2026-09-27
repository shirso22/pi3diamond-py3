"""

"""

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

import measurements.awg.waveform as waveform
from measurements.awg.hahn_echo_awg import Hahn3pi2_awg
from measurements.awg.rabi_awg import Rabi_awg
from .waveform import *


class TEER_freq_2pi_awg(Rabi_awg):
    """Defines a TEER measurement with both pi/2 and 3pi/2 readout pulse."""
    sequence_delay = Range(low=0., high=1200., value=400.)
    freq_begin = Range(low=1, high=20e9, value=200e6, desc='frequency [Hz]', label='Freq Begin[Hz]',
                       mode='text', auto_set=False, enter_set=True,
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                         format_str='%.5e'))
    freq_delta = Range(low=1, high=20e9, value=1e6, desc='frequency [Hz]', label='Freq Delta [Hz]',
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                         format_str='%.5e'), mode='text', auto_set=False,
                       enter_set=True)
    freq_end = Range(low=1, high=20e9, value=250e6, desc='frequency [Hz]', label='Freq End [Hz]',
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                       format_str='%.5e'), mode='text', auto_set=False,
                     enter_set=True)
    NV_tau = Range(low=1, high=20e9, value=1000, desc='time [ns]', label='NV Tau [ns]', mode='text',
                   auto_set=False, enter_set=True)
    rf_pi_delay = Range(low=1., high=1e6, value=50., desc='rf pi delay [ns]',
                        label='rf pi delay [ns]', mode='text', auto_set=False, enter_set=True)
    rf_t_pi = Range(low=1., high=1e6, value=50., desc='rf pi pulse length', label='rf pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    rf_t_pi_2 = Range(low=1., high=1e6, value=50., desc='second rf pi pulse length',
                      label='second rf pi [ns]',
                      mode='text', auto_set=False, enter_set=True)
    rf_power = Range(low=-100., high=25., value=-20, desc='rf power', label='rf power [dBm]',
                     mode='text', auto_set=False, enter_set=True)

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setOutput(self.rf_power, self.freq_center)
        self.rf._write('SOUR:DM:IQ:STAT ON')
        self.prepare_awg()

    def prepare_awg(self):
        sampling = 1.0e9
        freq_begin = self.freq_begin
        freq_end = self.freq_end
        freq_delta = self.freq_delta
        pi = self.rf_t_pi
        pi_2 = self.rf_t_pi_2
        freq_center = self.freq_center
        freq_list = freq_center - np.arange(freq_begin, freq_end, freq_delta)
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
            drive_y = Sin(0, (self.freq_center - self.freq) / sampling, np.pi / 2 + phase_1,
                          self.amp)
            zero = Idle(1)
            zeros = Idle(250)
            rf_delay = Idle(self.rf_pi_delay)
            t_blank = self.laser + self.NV_tau / 2. + self.mw_x_t_pi2 + self.sequence_delay
            self.waves = []
            self.waves_sum = []
            self.main_seq = Sequence('TEER_freq_2pi.SEQ')
            j = 0  # pts_keeper
            for i in range(len(freq_list)):
                pulse_temp_x = []
                pulse_temp_y = []

                # The pi pulse
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = pi
                drive_y.duration = pi
                drive_x.freq = freq_list[i] / sampling
                drive_y.freq = freq_list[i] / sampling
                x_name = 'X_RA_%03i_3.WFM' % i
                y_name = 'Y_RA_%03i_3.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [zero, drive_x, rf_delay, zeros]))
                self.waves.append(waveform.Waveform(y_name, [zero, drive_y, rf_delay, zeros]))

                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                sum_name_x = 'sum_x_%03i_1.WFM' % i
                sum_name_y = 'sum_y_%03i_1.WFM' % i
                self.waves_sum.append(waveform.Waveform(sum_name_x, pulse_temp_x))
                self.waves_sum.append(waveform.Waveform(sum_name_y, pulse_temp_y))
                self.main_seq.append(*self.waves_sum[-2:], wait=True)

            for i in range(len(freq_list)):
                pulse_temp_x = []
                pulse_temp_y = []

                # The pi pulse
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = pi
                drive_y.duration = pi
                drive_x.freq = (self.freq_center - self.freq) / sampling
                drive_y.freq = (self.freq_center - self.freq) / sampling
                x_name = 'X_RA_%03i_33.WFM' % i
                y_name = 'Y_RA_%03i_33.WFM' % i
                self.waves.append(waveform.Waveform(x_name, [zero, drive_x, rf_delay]))
                self.waves.append(waveform.Waveform(y_name, [zero, drive_y, rf_delay]))
                pulse_temp_x.extend(self.waves[j].pulse_seq)
                pulse_temp_y.extend(self.waves[j + 1].pulse_seq)
                j += 2

                # The freq sweeping pi
                drive_x.amp = 1
                drive_y.amp = 1
                drive_x.phase = 0
                drive_y.phase = np.pi / 2
                drive_x.duration = pi_2
                drive_y.duration = pi_2
                drive_x.freq = freq_list[i] / sampling
                drive_y.freq = freq_list[i] / sampling
                x_name = 'X_RA_%03i_44.WFM' % i
                y_name = 'Y_RA_%03i_44.WFM' % i
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
            self.AWG.load('TEER_freq_2pi.SEQ')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        freq_begin = self.freq_begin
        freq_end = self.freq_end
        freq_delta = self.freq_delta
        freq_center = self.freq_center
        freq_list = freq_center - np.arange(freq_end, freq_begin, -freq_delta)
        trigger_delay = self.trigger_delay

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        NV_tau = self.NV_tau
        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(freq_list)):
                sequence.append(([], decay_init))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append(([], 0.5 * NV_tau - trigger_delay - 100))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay))
                sequence.append((['microwave', 'rf'], mw_x_t_pi))
                sequence.append((['rf'], 0.5 * NV_tau))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append((['detect', 'aom'], laser))

            for i in range(len(freq_list)):
                sequence.append(([], decay_init))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append(([], 0.5 * NV_tau - trigger_delay - 100))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay))
                sequence.append((['microwave', 'rf'], mw_x_t_pi))
                sequence.append((['rf'], 0.5 * NV_tau))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append((['detect', 'aom'], laser))
            return sequence
        else:
            sequence = []
            # ADD SEQUENCE HERE
            return sequence

    get_set_items = Hahn3pi2_awg.get_set_items + ['NV_tau', 'rf_t_pi', 'rf_t_pi_2', 'rf_power',
                                                  'freq_begin', 'freq_delta', 'freq_end']

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
                                                   Item('reload', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-80,
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
                                            HGroup(Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_t_pi_2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_pi_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('freq_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('freq_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_center', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('freq', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('NV_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('trigger_delay', width=-80,
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
                                            label='analysis'),
                                     ),
                              ),
                       title='TEER Freq 2pi AWG Measurement',
                       )
