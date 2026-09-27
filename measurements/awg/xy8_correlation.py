"""
Classes to conduct a XY-8 correlation measurement.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
alongside to recieve them from global_vars.py

Here we just add two simple xy8 correlation measurements and insert some time between them before
reading out!
"""

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, VSplit

from analysis.pulsed import PulsedToolDoubleTau
from measurements.awg.measurements_awg import upload_xy8_correlation
from measurements.awg.xy8_awg_pulsed import XY8_awg_pulsed


class XY8Correlation(XY8_awg_pulsed):
    """Defines a XY-8 measurement with both pi/2 and 3pi/2 readout pulse."""

    double_sequence = True

    order = Range(low=1, high=100, value=2, desc='# of pi pulse', label='Order',
                  mode='text', auto_set=False, enter_set=True)
    tau_xy8 = Range(low=1.0, high=10e6, value=5000, desc='tau of xy8 sequence', label='XY8 tau',
                    mode='text', auto_set=False, enter_set=True)

    def shut_down(self):
        """
        Do nothing on autofocus, since we have thermal drifts.
        """
        pass

    def prepare_awg(self):
        if self.tau_xy8 < self.order * 4 * (self.mw_x_t_pi + self.mw_y_t_pi):
            raise IOError('The delay between pulses is too short.'
                          'It has to be larger than the pulse_duration')
            self.shut_down()
        sampling = 1.0e9
        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.delete_all()
            upload_xy8_correlation(self.AWG, self.order, self.mw_x_t_pi, self.mw_x_t_pi2,
                                   self.mw_x_t_3pi2, self.mw_y_t_pi, self.tau_xy8, self.tau_begin,
                                   self.tau_delta, self.tau_end, self.laser, self.trigger_delay,
                                   self.decay_init)
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    get_set_items = XY8_awg_pulsed.get_set_items + ['tau_xy8']

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
                                            HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('order', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_y_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_xy8', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_center', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
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
                                            label='analysis'),
                                     ),
                              ),
                       title='XY-8 Correlation measurement',
                       )


class XY8CorrelationView(PulsedToolDoubleTau):
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=100,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=100,
                                          resizable=True),
                                     ),
                              ),
                       title='XY-8 Correlation AWG',
                       buttons=[], resizable=True
                       )
