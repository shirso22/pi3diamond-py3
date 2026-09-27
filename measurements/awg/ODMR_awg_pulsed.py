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

from measurements.awg.measurements_awg import upload_odmr
from measurements.awg.rabi_awg_pulsed import Rabi_awg_pulsed
from measurements.pulsed import Pulsed
from .waveform import *


class ODMR_awg_pulsed(Rabi_awg_pulsed):
    """Defines a DEER_Rabi measurement with both pi/2 and 3pi/2 readout pulse."""

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

        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.tell('*WAI')
            self.AWG.delete_all()
            self.AWG.tell('*WAI')
            upload_odmr(self.AWG, self.mw_x_t_pi, self.freq_begin, self.freq_delta, self.freq_end,
                        self.freq_center, self.laser, self.trigger_delay, self.decay_init)
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        laser = self.laser
        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(self.frequencies)):
                sequence.append(([], decay_init))
                sequence.append((['detect', 'aom'], laser))
            sequence += [(['sequence'], 100)]
            return sequence
        else:
            sequence = []
            # ENTER SEQUENCE HERE
            return sequence

    get_set_items = Rabi_awg_pulsed.get_set_items + ['mw_x_t_pi', 'rf_power', 'freq_begin', 'freq_end',
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
                                                   Item('mw_x_t_pi', width=-80,
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
                       title='ODMR_awg_pulsed Measurement',
                       )
