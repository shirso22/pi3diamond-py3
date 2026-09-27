"""
Class for performing a Ramsey and Ramsey-DQT measurement to get T2* and estimate the nitrogen
concentration in the sample. Code is copied from hahn_echo.py and adjusted for the missing central
pi-pulse (and different naming)
"""

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from .rabi import Rabi


class Ramsey(Rabi):
    """Defines a Ramsey measurement with both pi/2 and 3pi/2 readout pulse."""

    # Make a double line plot
    double_sequence = True

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2

        decay_init = self.decay_init
        sequence = []
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], t),
                         (['microwave'], mw_x_t_pi2), (['detect', 'aom'], laser), ([], decay_init)]
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], t),
                         (['microwave'], mw_x_t_3pi2), (['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['sequence'], 100)]
        return sequence

    def _update_fit(self):
        """Fit with a Gaussian shape.

        :return: None.
        """
        pass

    get_set_items = Rabi.get_set_items + ['mw_x_t_pi2', 'mw_x_t_3pi2']

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
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(Item('mw_frequency', width=-80,
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
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              Item('contrast_plot', show_label=False, width=500, height=-300,
                                   resizable=True),
                              ),
                       title='Pi3diamond: Ramsey Measurement',
                       resizable=True
                       )


class RamseyDQT(Ramsey):
    """Defines a Ramsey measurement utilizing a mixed state between |-1> and |1>, in general
     called the double quantum transition by the community, because that is a cool and intriguing
     name.
     With both pi/2 and 3pi/2 readout pulse.
     """

    mw2_frequency = Range(low=1, high=20e9, value=2.8705e9, desc='microwave 2 frequency',
                          label='frequency 2 [Hz]', mode='text', auto_set=False, enter_set=True,
                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                            format_str='%.5e'))
    mw2_power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power 2 [dBm]',
                      mode='text', auto_set=False, enter_set=True)
    mw2_x_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='MW2 pi [ns]',
                       mode='text', auto_set=False, enter_set=True)

    interpulse_delay = Range(low=0., high=10000., value=15.0, desc='microwave power',
                             label='interpulse delay [dBm]', mode='text', auto_set=False,
                             enter_set=True)

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.microwave2.setOutput(self.mw2_power, self.mw2_frequency)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(None, self.mw_frequency)
        self.microwave2.setOutput(None, self.mw_frequency)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw2_x_t_pi = self.mw2_x_t_pi
        ip_delay = self.interpulse_delay

        decay_init = self.decay_init
        sequence = []
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi), ([], t),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi), ([], t),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_3pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['sequence'], 100)]
        return sequence

    get_set_items = Ramsey.get_set_items + ['mw_x_t_3pi2', 'mw2_frequency', 'mw2_power',
                                            'mw2_x_t_pi', 'interpulse_delay']

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
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('interpulse_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_frequency', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw2_frequency', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw2_power', width=-80),
                                                   Item('mw2_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
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
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('contrast_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: Ramsey DQT Measurement',
                       buttons=[],
                       resizable=True,
                       )
