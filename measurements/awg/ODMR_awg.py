# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 15:53:19 2016

@author: kbxu
"""

# -*- coding: utf-8 -*-
"""
Created on Fri Sep 09 12:49:46 2016

@author: kbxu
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 07 15:17:09 2016

@author: kbxu
"""

"""
Classes to conduct a DEER  measurement.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
Alongside to recieve them from global_vars.py
See rabi.py as example.
TODO: On the fly evaluation, i.e. subtracting the two pulse sequences and evaluation of the latter.
"""

from traits.api import Range, Array
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from measurements.awg.hahn_echo_awg import Hahn3pi2_awg
from measurements.awg.rabi_awg import Rabi_awg
from measurements.pulsed import Pulsed
from .waveform import *


class ODMR_awg(Rabi_awg):
    """Defines a DEER_Rabi measurement with both pi/2 and 3pi/2 readout pulse."""

    sequence_delay = Range(low=0., high=1200., value=400.)
    rf_power = Range(low=-100., high=25., value=-20, desc='microwave power', label='rf power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    rf_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    freq_begin = Range(low=1, high=20e9, value=200e6, desc='frequency [Hz]', label='Freq Begin[Hz]',
                       mode='text', auto_set=False, enter_set=True,
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                         format_str='%.5e'))
    freq_delta = Range(low=1, high=20e9, value=1e6, desc='frequency [Hz]', label='Freq Delta [Hz]',
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                         format_str='%.5e'), mode='text', auto_set=False, enter_set=True)
    freq_end = Range(low=1, high=20e9, value=250e6, desc='frequency [Hz]', label='Freq End [Hz]',
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                       format_str='%.5e'), mode='text', auto_set=False, enter_set=True)
    frequencies = Array()

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setOutput(self.rf_power, self.freq_center)
        self.rf._write('SOUR:DM:IQ:STAT ON')
        self.prepare_awg()

    def apply_parameters(self):
        """Apply the current parameters and decide whether to keep previous data.

        Overwritten from measurements.pulsed to include changes on the frequency array
        :return: void
        """
        frequencies = np.arange(self.freq_begin, self.freq_end, self.freq_delta)

        if not self.keep_data or np.any(frequencies != self.frequencies):
            self.frequencies = frequencies

        Pulsed.apply_parameters(self)

    def prepare_awg(self):
        sampling = 1.0e9
        freq_begin = self.freq_begin
        freq_end = self.freq_end
        freq_delta = self.freq_delta
        pi = self.rf_t_pi
        freq_center = self.freq_center
        freq_list = freq_center - np.arange(freq_begin, freq_end, freq_delta)
        pi = int(pi * sampling / 1.0e9)

        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.tell('*WAI')
            self.AWG.delete_all()
            self.AWG.tell('*WAI')
            if self.phase:
                phase_1 = self.phase_1
            else:
                phase_1 = 0
            drive_x = Sin(0, (self.freq_center - self.frequencies[0]) / sampling, 0, self.amp)
            drive_y = Sin(0, (self.freq_center - self.frequencies[0]) / sampling,
                          np.pi / 2 + phase_1, self.amp)
            zero = Idle(1)
            zeros = Idle(250)
            self.waves = []
            self.main_seq = Sequence('DEER.SEQ')
            t_blank = self.laser + self.sequence_delay
            for i in range(len(freq_list)):
                drive_x.duration = pi
                drive_y.duration = pi
                drive_x.freq = freq_list[i] / sampling
                drive_y.freq = freq_list[i] / sampling
                x_name = 'X_RA_%03i.WFM' % i
                y_name = 'Y_RA_%03i.WFM' % i
                self.waves.append(Waveform(x_name, [zero, drive_x, zeros]))
                self.waves.append(Waveform(y_name, [zero, drive_y, zeros]))
                self.main_seq.append(*self.waves[-2:], wait=True)
            add_marker(self.waves, self.main_seq, t_blank)
            self.AWG.upload(self.waves)
            self.AWG.upload(self.main_seq)
            self.AWG.tell('*WAI')
            self.AWG.load('DEER.SEQ')
            self.AWG.tell('*WAI')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        laser = self.laser
        tau = self.tau

        trigger_delay = self.trigger_delay
        rf_t_pi = self.rf_t_pi
        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(self.frequencies)):
                sequence.append(([], decay_init))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay + rf_t_pi))
                sequence.append((['detect', 'aom'], laser))

            sequence += [(['sequence'], 100)]
            return sequence
        else:
            sequence = []
            # ENTER SEQUENCE HERE
            return sequence

    get_set_items = Hahn3pi2_awg.get_set_items + ['rf_t_pi', 'rf_power', 'freq_begin', 'freq_end',
                                                  'freq_delta']

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
                                                   ),
                                            HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_t_pi', width=-80,
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
                       title='ODMR_awg Measurement',
                       )
