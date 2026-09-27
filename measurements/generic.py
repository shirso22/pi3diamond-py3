"""
Classes to conduct a generic measurement. This measurement has a tau variable that is swept and
two strings can be supplied by the user that are interpreted as microwave sequences giving an
arbitrary handle on the measurements.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
Alongside to recieve them from global_vars.py. See rabi.py as example.
TODO: Something I am sure
"""

from traits.api import Range, String
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from .deer_correlation import DarkSpin_Hahn
from .pulsed import sequence_remove_zeros


class Generic_Pulsed(DarkSpin_Hahn):
    """This class can run user-string defined sequences.

    This includes both NV- and DEER- sequences.
    """
    double_sequence = True

    nu = Range(low=0., high=100000., value=100., desc='fixed variable for sequence',
               label='nu [ns]', mode='text', auto_set=False, enter_set=True)
    seq_delay = Range(low=0., high=1000000, value=0., desc='added delay at sequence ending',
                      label='seq delay [ns]', mode='text', auto_set=False, enter_set=True)
    seq = String(desc='Sequence', label="Sequence",
                 value="[(['mw_y'], t_pi2_y), (['mw_x'], tau),(['mw_y'], t_3pi2_y)]", mode='text')
    iseq = String(desc='2nd Sequence', label="2nd Sequence",
                  value="[(['mw_y'], t_pi2_y), (['mw_x'], tau),(['mw_y'], t_pi2_y)]", mode='text')

    def generate_sequence(self):
        tau_array = self.tau
        laser = self.laser
        decay_init = self.decay_init
        seq_delay = self.seq_delay
        nu = self.nu

        # values that can be used for NV Center manipulation
        t_pi2, t_pi, t_3pi2 = self.mw_x_t_pi2, self.mw_x_t_pi, self.mw_x_t_3pi2
        t_pi2_x, t_pi_x, t_3pi2_x = self.mw_x_t_pi2, self.mw_x_t_pi, self.mw_x_t_3pi2
        t_pi2_y, t_pi_y, t_3pi2_y = self.mw_y_t_pi2, self.mw_y_t_pi, self.mw_y_t_3pi2

        # Values only relevant for DEER
        mw_tau = self.mw_tau
        rf_t_pi = self.rf_t_pi
        rf_pulse_delay = self.rf_pulse_delay
        tau_evo = self.tau_evo
        seq_offset_evo = self.seq_offset_evo
        rf_evo_t_pi2 = self.rf_evo_t_pi2
        rf_evo_t_pi = self.rf_evo_t_pi

        sequence = []
        for tau in tau_array:
            for pulse in eval(self.seq):
                sequence.append(pulse)
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        if self.iseq != "":
            for tau in tau_array:
                for pulse in eval(self.iseq):
                    sequence.append(pulse)
                sequence.append((['detect', 'aom'], laser))
                sequence.append(([], decay_init))
        sequence.append((['sequence'], 100))
        sequence.append(([], seq_delay))
        sequence = sequence_remove_zeros(sequence)
        return sequence

    get_set_items = DarkSpin_Hahn.get_set_items + ['seq', 'iseq']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(
                                  HGroup(Item('seq', springy=True,
                                              enabled_when='state != "run"'),
                                         Item('iseq', springy=True,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('mw_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('mw_power', width=-60, enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('n_sequences', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_y_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_pulse_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('seq_offset_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_evo_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_evo_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
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
                              ),
                       title='Pi3diamond: Generic Measurement',
                       buttons=[],
                       resizable=True,
                       )


if __name__ == '__main__':
    pass
