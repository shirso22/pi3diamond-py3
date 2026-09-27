# -*- coding: utf-8 -*-
"""
Created on Fri Jul 01 11:55:49 2016

@author: kbxu
"""

"""
Classes to conduct a Hahn measurement.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
Alongside to recieve them from global_vars.py
"""

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from measurements.awg.measurements_awg import upload_hahn_echo
from measurements.awg.rabi_awg_pulsed import Rabi_awg_pulsed


class Hahn3pi2_awg_pulsed(Rabi_awg_pulsed):
    """Defines a Hahn-Echo measurement with both pi/2 and 3pi/2 readout pulse."""

    double_sequence = True
    sequence_delay = Range(low=0., high=1200., value=400.)

    def prepare_awg(self):
        sampling = 1.0e9
        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.delete_all()
            upload_hahn_echo(self.AWG, self.mw_x_t_pi2, self.mw_x_t_pi, self.mw_x_t_3pi2, self.tau_begin,
                             self.tau_delta, self.tau_end, self.laser, self.trigger_delay, self.decay_init)
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    get_set_items = Rabi_awg_pulsed.get_set_items + ['mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2']

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
                                                   Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('trigger_delay', width=-80, enabled_when='state != "run"'),
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
                       title='Hahn-Echo Awg Pulsed Measurement',
                       )
