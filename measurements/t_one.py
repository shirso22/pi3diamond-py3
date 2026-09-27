"""
This code is currently broken

small changes are required to adapt it to the new pulsed measurements (without hardware API).

See rabi.py as example.
"""

import numpy as np
from chaco.api import ArrayPlotData
from traits.api import Range, Float, Array
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from .pulsed import Pulsed
from .pulsed import PulsedTau
from .rabi import Rabi
from tools.chaco_addons import SavePlot as Plot, SaveTool


class T1(PulsedTau):
    """Defines a T1 measurement."""

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False,
                  enter_set=True)
    decay_init = Float(default_value=1000.,
                       desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0.,
                       desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)

    aom_delay = Float(default_value=0.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        sequence = [(['aom'], laser)]
        for t in tau:
            sequence += [([], t), (['detect', 'aom'], laser)]
        sequence += [([], 1000)]
        sequence += [(['sequence'], 100)]
        return sequence

    get_set_items = PulsedTau.get_set_items + ['laser', 'decay_init', 'decay_read', 'aom_delay']

    traits_view = View(VGroup(HGroup(Item('submit_button', width=-60, show_label=False),
                                     Item('remove_button', width=-60, show_label=False),
                                     Item('resubmit_button', width=-60, show_label=False),
                                     Item('priority', width=-30),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(
                                  HGroup(Item('laser', width=-80, enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_read', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('aom_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(
                                      Item('tau_begin', width=-80, enabled_when='state != "run"'),
                                      Item('tau_end', width=-80, enabled_when='state != "run"'),
                                      Item('tau_delta', width=-80, enabled_when='state != "run"'),
                                  ),
                                  label='stimulation'),
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
                       title='Pi3diamond: T1 Measurement',
                       )


class SingletDecay(Rabi):
    double_sequence = False

    laser = Range(low=1., high=100000., value=3000., desc='laser [ns]', label='laser [ns]',
                  mode='text', auto_set=False,
                  enter_set=True)

    decay_init = Float(default_value=250.,
                       desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)

    tau_begin = Range(low=0., high=1e9, value=0., desc='tau begin [ns]', label='tau begin [ns]',
                      mode='text',
                      auto_set=False, enter_set=True)
    tau_end = Range(low=1., high=1e9, value=300., desc='tau end [ns]', label='tau end [ns]',
                    mode='text',
                    auto_set=False, enter_set=True)
    tau_delta = Range(low=1., high=1e6, value=100., desc='Number of points', label='Number of points',
                      mode='text',
                      auto_set=False, enter_set=True)

    def generate_sequence(self):
        """
        Generate T1 Measurement sequence without applied pi pulse.

        Here we generate a logarithmic tau array, so we do not have to measure as many points at
        longer times between prepare and readout pulses, since this takes a lot of time!
        """
        # HW-FIX: np.logspace() needs an int point count; tau_delta is a float
        # trait. NumPy used to tolerate a float and now raises TypeError.
        self.tau = np.logspace(np.log10(self.tau_begin), np.log10(self.tau_end + self.tau_delta),
                               int(self.tau_delta))
        tau = self.tau
        laser = self.laser

        decay_init = self.decay_init

        sequence = []
        for t in tau:
            sequence.append(([], t))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        sequence.append((['sequence'], 100))
        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  spin_state=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.plot(('index', 'spin_state'), type='scatter', marker="circle", marker_size=3, color='blue',index_scale='log')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    traits_view = View(
        VGroup(
            HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f',
                                          width=-60),
                                     Item('stop_time', width=-60),
                                     Item('stop_counts', width=-60),
                                     ),
                            HGroup(Item('filename', springy=True),
                                    Item('save_button', show_label=False),
                                    Item('load_button', show_label=False),
                                    Item('periodic_save'),
                                    Item('save_interval', enabled_when='not periodic_save'),
                                    ),
                              Tabbed(VGroup(HGroup(
                                    Item('laser', width=-80, enabled_when='state != "run"'),
                                    Item('decay_init', width=-80, enabled_when='state != "run"'),),
                                  HGroup(
                                      Item('tau_begin', width=-80, enabled_when='state != "run"'),
                                      Item('tau_end', width=-80, enabled_when='state != "run"'),
                                      Item('tau_delta', width=-80, enabled_when='state != "run"'),
                                      ),
                                  label='acquisition'),
                                  VGroup(HGroup(Item('record_length', width=-80,
                                                     enabled_when='state != "run"'),
                                                Item('bin_width', width=-80,
                                                     enabled_when='state != "run"'), ),
                                         label='detection'),
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
        title='Singlet decay',
        resizable=True
    )


class T1pi(Rabi):
    """Defines a T1 measurement with pi pulse."""

    double_sequence = True

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False,
                  enter_set=True)

    tau_delta = Range(low=1., high=1e6, value=50., desc='Number of points', label='number of points',
                      mode='text',
                      auto_set=False, enter_set=True)

    def generate_sequence(self):
        """
        Generate T1 Measurement sequence with and without applied pi pulse.
        
        Here we generate a logarithmic tau array, so we do not have to measure as many points at
        longer times between prepare and readout pulses, since this takes a lot of time!
        """
        self.tau = np.logspace(np.log10(self.tau_begin), np.log10(self.tau_end + self.tau_delta),
                               # PY3-PORT: logspace()'s third argument is `num`, the
                               # NUMBER OF POINTS, and must be an integer. tau_delta is
                               # Range(low=1., high=1e6, value=3.) -- a float trait. Old
                               # numpy accepted a float num with a deprecation warning;
                               # current numpy calls operator.index() and raises.
                               # int() preserves the old behaviour exactly (3.0 -> 3).
                               # NOTE: passing a *delta* as a point count looks like a
                               # pre-existing mistake. Preserved, not corrected -- a port
                               # should not silently change what the instrument does.
                               int(self.tau_delta))
        tau = self.tau
        laser = self.laser

        decay_init = self.decay_init
        mw_x_t_pi = self.mw_x_t_pi

        sequence = []
        for t in tau:
            sequence.append(([], t))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        for t in tau:
            sequence.append((['microwave'], mw_x_t_pi))
            sequence.append(([], t))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        sequence.append((['sequence'], 100))
        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'first'), color='blue', name='first', index_scale = 'log')
        plot.plot(('index', 'first'), type='scatter', marker="circle", marker_size=2, color='blue', index_scale = 'log')
        plot.plot(('index', 'second'), color='green', name='second', index_scale = 'log')
        plot.plot(('index', 'second'), type='scatter', marker="circle", marker_size=2, color='green', index_scale = 'log')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    traits_view = View(
        VGroup(
            HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f',
                                          width=-60),
                                     Item('stop_time', width=-60),
                                     Item('stop_counts', width=-60),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                                  Item('laser', width=-80, enabled_when='state != "run"'),
                                  Item('decay_init', width=-80, enabled_when='state != "run"'),
                                  Item('mw_x_t_pi', width=-80, enabled_when='state != "run"'), ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='acquisition'),
                                  VGroup(HGroup(Item('record_length', width=-80,
                                                     enabled_when='state != "run"'),
                                                Item('bin_width', width=-80,
                                                     enabled_when='state != "run"'), ),
                                         label='detection'),
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
        title='Pi3diamond: T1pi',
        resizable=True
    )

    get_set_items = Rabi.get_set_items + ['mw_x_t_pi']

class T1Swap(Rabi):
    """Defines a T1 measurement with three pulse sequences.

    Sequence 1:
        tau -> readout

    Sequence 2:
        MW pi -> tau -> readout

    Sequence 3:
        tau -> MW pi -> readout
    """

    double_sequence = True

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False,
                  enter_set=True)

    tau_delta = Range(low=1., high=1e6, value=50., desc='Number of points', label='number of points',
                      mode='text',
                      auto_set=False, enter_set=True)

    def generate_sequence(self):
        """
        Generate T1 measurement with three sequences:

        1. No MW:
               tau -> readout

        2. Pi pulse before tau:
               MW pi -> tau -> readout

        3. Pi pulse after tau:
               tau -> MW pi -> readout
        """

        # HW-FIX: np.logspace() needs an int point count; tau_delta is a float
        # trait. NumPy used to tolerate a float and now raises TypeError.
        self.tau = np.logspace(
            np.log10(self.tau_begin),
            np.log10(self.tau_end + self.tau_delta),
            int(self.tau_delta)
        )

        tau = self.tau
        laser = self.laser
        decay_init = self.decay_init
        mw_x_t_pi = self.mw_x_t_pi

        sequence = []

        # 1. No MW: tau -> readout
        for t in tau:
            sequence.append(([], t))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))

        # 2. Pi pulse before tau: MW -> tau -> readout
        for t in tau:
            sequence.append((['microwave'], mw_x_t_pi))
            sequence.append(([], t))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))

        # 3. Pi pulse after tau: tau -> MW -> readout
        for t in tau:
            sequence.append(([], t))
            sequence.append((['microwave'], mw_x_t_pi))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))

        sequence.append((['sequence'], 100))

        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(
            index=np.array((0, 1)),
            no_mw=np.array((0, 0)),
            pi_before=np.array((0, 0)),
            pi_after=np.array((0, 0)),
        )

        plot = Plot(
            line_data,
            padding=8,
            padding_left=64,
            padding_bottom=36
        )

        # No MW - blue
        plot.plot(('index', 'no_mw'), color='blue', name='no MW', index_scale = 'log')
        plot.plot(('index', 'no_mw'), type='scatter', marker="circle", marker_size=2,
                  color='blue', index_scale='log')

        # Pi before tau - green
        plot.plot(('index', 'pi_before'), color='green', name='pi before tau', index_scale = 'log')
        plot.plot(('index', 'pi_before'), type='scatter', marker="circle", marker_size=2,
                  color='green', index_scale='log')

        # Pi after tau - red
        plot.plot(('index', 'pi_after'), color='red', name='pi after tau', index_scale = 'log')
        plot.plot(('index', 'pi_after'), type='scatter', marker="circle", marker_size=2,
                  color='red', index_scale='log')

        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))

        self.line_data = line_data
        self.line_plot = plot

    def _update_line_plot_value(self):
        y = self.spin_state

        n = len(y) // 3

        no_mw = y[:n]
        pi_before = y[n:2 * n]
        pi_after = y[2 * n:3 * n]

        self.line_data.set_data('no_mw', no_mw)
        self.line_data.set_data('pi_before', pi_before)
        self.line_data.set_data('pi_after', pi_after)

    def _create_contrast_plot(self):
        contrast_data = ArrayPlotData(
            index=np.array((0, 1)),
            no_mw_minus_pi_before=np.array((0, 0)),
            no_mw_minus_pi_after=np.array((0, 0)),
        )

        plot = Plot(
            contrast_data,
            padding=8,
            padding_left=64,
            padding_bottom=36
        )

        # No MW - Pi before tau: black
        plot.plot(
            ('index', 'no_mw_minus_pi_before'),
            color='black',
            name='no MW - pi before tau',
            index_scale='log'
        )

        # No MW - Pi after tau: purple
        plot.plot(
            ('index', 'no_mw_minus_pi_after'),
            color='purple',
            name='no MW - pi after tau',
            index_scale = 'log'
        )

        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'contrast'
        plot.tools.append(SaveTool(plot))

        self.contrast_data = contrast_data
        self.contrast_plot = plot

    def _update_contrast_plot_value(self):
        y = self.spin_state

        n = len(y) // 3

        no_mw = y[:n]
        pi_before = y[n:2 * n]
        pi_after = y[2 * n:3 * n]

        contrast_1 = no_mw - pi_before
        contrast_2 = no_mw - pi_after

        self.contrast_data.set_data(
            'no_mw_minus_pi_before',
            contrast_1
        )

        self.contrast_data.set_data(
            'no_mw_minus_pi_after',
            contrast_2
        )

    def _on_tau_change(self):
        index = self.tau * 1e-3

        self.line_data.set_data('index', index)
        self.contrast_data.set_data('index', index)

    traits_view = View(
        VGroup(
            HGroup(
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('resubmit_button', show_label=False),
                Item('get_global_vars_button', show_label=False),
                Item('priority'),
                Item('state', style='readonly'),
                Item('run_time', style='readonly', format_str='%.f',
                     width=-60),
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
                        Item('mw_frequency', width=-120,
                             enabled_when='state != "run"'),
                        Item('mw_power', width=-60,
                             enabled_when='state != "run"'),
                        Item('laser', width=-80,
                             enabled_when='state != "run"'),
                        Item('decay_init', width=-80,
                             enabled_when='state != "run"'),
                        Item('mw_x_t_pi', width=-80,
                             enabled_when='state != "run"'),
                    ),

                    HGroup(
                        Item('tau_begin', width=-80,
                             enabled_when='state != "run"'),
                        Item('tau_end', width=-80,
                             enabled_when='state != "run"'),
                        Item('tau_delta', width=-80,
                             enabled_when='state != "run"'),
                    ),

                    label='acquisition'
                ),
                VGroup(HGroup(Item('record_length', width=-80,
                                   enabled_when='state != "run"'),
                              Item('bin_width', width=-80,
                                   enabled_when='state != "run"'), ),
                       label='detection'),

                VGroup(HGroup(Item('integration_width'),
                              Item('position_signal'),
                              Item('position_normalize'),
                    ),

                    label='analysis'
                ),
            ),

            Tabbed(
                Item(
                    'line_plot',
                    show_label=False,
                    width=500,
                    height=-300,
                    resizable=True
                ),

                Item(
                    'matrix_plot',
                    show_label=False,
                    width=500,
                    height=-300,
                    resizable=True
                ),

                Item(
                    'pulse_plot',
                    show_label=False,
                    width=500,
                    height=-300,
                    resizable=True
                ),

                Item(
                    'contrast_plot',
                    show_label=False,
                    width=500,
                    height=-300,
                    resizable=True
                ),
            ),
        ),

        title='Pi3diamond: T1Swap',
        resizable=True
    )

    get_set_items = Rabi.get_set_items + ['mw_x_t_pi']

if __name__ == '__main__':
    # from hardware.dummy import PulseGenerator, TimeTagger, Microwave
    # t1 = T1pi(analog_pulser, time_tagger, microwave,
    #           frequency=rabi.frequency,
    #           mw_power=rabi.mw_power,
    #           mw_x_t_pi=80
    #           )
    # t1.edit_traits()
    pass
