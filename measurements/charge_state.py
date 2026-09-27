"""
This code is currently broken

small changes are required to adapt it to the new pulsed measurements (without hardware API).

See rabi.py as example.
"""

import numpy as np
from chaco.api import ArrayPlotData
from chaco.api import Plot
from traits.api import Range, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

# PY3-PORT: implicit relative import; Python 3 needs it explicit.
from .rabi import Rabi
from tools.chaco_addons import SavePlot as Plot, SaveTool


class ChargeStateDynamics(Rabi):
    """Defines a T1 measurement with pi pulse."""
    record_length = Float(default_value=400, desc='length of acquisition record [ns]',
                          label='record length [ns]', mode='text', auto_set=False, enter_set=True)
    bin_width = Range(low=0.1, high=100000000., value=1.0, desc='bin width [ns]', label='bin width [ns]',
                      mode='text', auto_set=False, enter_set=True)
    laser1_time = Range(low=0, high=1000000000, value=20, desc='green laser [ns]', label=' green laser [ns]', mode='text',
                        auto_set=False, enter_set=True)
    laser2_time = Range(low=0, high=1000000000, value=400, desc='orange laser [ns]', label=' orange laser [ns]',
                        mode='text',
                        auto_set=False, enter_set=True)

    double_sequence = False

    def generate_sequence(self):
        """
        Generate T1 Measurement sequence with and without applied pi pulse.

        Here we generate a logarithmic tau array, so we do not have to measure as many points at
        longer times between prepare and readout pulses, since this takes a lot of time!
        """
        laser1_time = self.laser1_time
        laser2_time = self.laser2_time

        decay_init = self.decay_init

        sequence = list()
        for _ in range(100):
            sequence.append((['aom', 'aom2'], laser1_time))
            sequence.append((['detect', 'aom2'], laser2_time - laser1_time))
            sequence.append((['aom'], laser1_time))
            # sequence.append(([], decay_init))
        sequence.append((['sequence'], 10))
        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'first'), color='blue', name='first', index_scale='log')
        plot.plot(('index', 'second'), color='green', name='second', index_scale='log')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    traits_view = View(
        VGroup(
            HGroup(
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('resubmit_button', show_label=False),
                Item('get_global_vars_button', show_label=False),
                Item('priority'),
                Item('state', style='readonly'),
                Item('run_time', style='readonly', format_str='%.f', width=-60),
                Item('stop_time', width=-60),
                Item('stop_counts', width=-60),
            ),
            HGroup(
                Item('filename', springy=True),
                Item('save_button', show_label=False),
                Item('load_button', show_label=False),
                Item('periodic_save'),
                Item('save_interval', enabled_when='not periodic_save'),
            ),
            Tabbed(
                VGroup(
                    HGroup(
                        Item('decay_init', width=-80, enabled_when='state != "run"'),
                        Item('laser1_time', width=-80, enabled_when='state != "run"'),
                        Item('laser2_time', width=-80, enabled_when='state != "run"'),
                    ),
                    label='acquisition'
                ),
                VGroup(
                    HGroup(
                        Item('record_length', width=-80, enabled_when='state != "run"'),
                        Item('bin_width', width=-80, enabled_when='state != "run"'),
                    ),
                    label='Acquisition'
                ),
                VGroup(
                    HGroup(
                        Item('integration_width'),
                        Item('position_signal'),
                        Item('position_normalize'),
                    ),
                    label='analysis'
                ),
            ),
            Tabbed(
                Item('line_plot', show_label=False, width=500, height=-300, resizable=True),
                Item('matrix_plot', show_label=False, width=500, height=-300, resizable=True),
                Item('pulse_plot', show_label=False, width=500, height=-300, resizable=True),
            ),
        ),
        title='Pi3diamond: Charge State Dynamics',
        resizable=True
    )

    get_set_items = Rabi.get_set_items + ['laser1_time', 'laser2_time']


if __name__ == '__main__':
    # from hardware.dummy import PulseGenerator, TimeTagger, Microwave
    # t1 = T1pi(analog_pulser, time_tagger, microwave,
    #           frequency=rabi.frequency,
    #           mw_power=rabi.mw_power,
    #           mw_x_t_pi=80
    #           )
    # t1.edit_traits()
    pass
