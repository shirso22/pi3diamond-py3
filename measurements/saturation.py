# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import logging

import numpy as np
from chaco.api import ArrayPlotData
from chaco.tools.api import PanTool, ZoomTool
from enable.api import ComponentEditor
from traits.api import Range, Array, Instance, on_trait_change
from traitsui.api import View, Item, HGroup, VGroup, Group

from tools.chaco_addons import SavePlot as Plot, SaveTool
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin


class SaturationScan(ManagedJob, GetSetItemsMixin):
    power_begin = Range(low=0.1, high=30., value=3, label='Begin [mW]', mode='text', auto_set=False,
                        enter_set=True)
    power_end = Range(low=0., high=100., value=25., label='End [mW]', mode='text', auto_set=False,
                      enter_set=True)
    power_delta = Range(low=0., high=5., value=0.5, label='Delta [mW]', mode='text', auto_set=False,
                        enter_set=True)
    seconds_per_point = Range(low=1e-3, high=1000., value=0.25, desc='Seconds per point', label='Seconds per point',
                              mode='text', auto_set=False, enter_set=True)

    power = Array()
    rate = Array()

    plot_data = Instance(ArrayPlotData)
    plot = Instance(Plot)

    get_set_items = ['__doc__', 'power_begin', 'power_end', 'power_delta', 'seconds_per_point',
                     'power', 'rate']

    def __init__(self, time_tagger, laser, **kwargs):
        super(SaturationScan, self).__init__(**kwargs)
        self.time_tagger = time_tagger
        self.laser = laser
        self._create_plot()

    def _run(self):
        try:
            self.state = 'run'
            power = np.arange(self.power_begin, self.power_end, self.power_delta)
            rate = np.zeros_like(power)

            counter_0 = self.time_tagger.Countrate(0)
            counter_1 = self.time_tagger.Countrate(1)

            init_power = self.laser.get_power()

            self.laser.set_power(0)
            self.thread.stop_request.wait(2)

            for idx, pow in enumerate(power):
                self.laser.set_power(pow)
                counter_0.clear()
                counter_1.clear()
                self.thread.stop_request.wait(self.seconds_per_point)

                if self.thread.stop_request.is_set():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    self.state = 'idle'
                    break

                rate[idx] = counter_0.getData() + counter_1.getData()
            else:
                self.state = 'done'

            del counter_0
            del counter_1

            self.laser.set_power(init_power)
            self.power = power
            self.rate = rate

        finally:
            self.state = 'idle'

    def _create_plot(self):
        plot_data = ArrayPlotData(power=np.array(()), rate=np.array(()), )
        plot = Plot(plot_data, padding=8, padding_left=64, padding_bottom=64)
        plot.plot(('power', 'rate'), color='blue')
        plot.index_axis.title = 'Power [mW]'
        plot.value_axis.title = 'Rate [kcps]'
        plot.tools.append(SaveTool(plot))
        plot.tools.append(PanTool(plot))
        plot.tools.append(ZoomTool(plot))
        self.plot_data = plot_data
        self.plot = plot
        self.line_plot = plot

    @on_trait_change("power")
    def _update_index(self, new):
        self.plot_data.set_data('power', new)

    @on_trait_change("rate")
    def _update_value(self, new):
        self.plot_data.set_data('rate', new * 1e-3)

    traits_view = View(
        VGroup(
            HGroup(
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('priority'),
                Item('state', style='readonly'),
            ),
            HGroup(
                Item('filename', springy=True),
                Item('save_button', show_label=False),
                Item('load_button', show_label=False)
            ),
            HGroup(
                Group(
                    Item('power_begin'),
                    Item('power_end'),
                    Item('power_delta'),
                    show_border=True
                ),
                Group(
                    Item('seconds_per_point'),
                    show_border=True
                )
            ),
            VGroup(
                Item('plot', editor=ComponentEditor(), show_label=False, resizable=True),
                show_border=True
            ),
            show_border=True
        ),
        title='Pi3diamond: SaturationScan', buttons=[], resizable=True, width=700, height=600,
    )


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().info('Starting logger.')

    import hardware.dummy

    time_tagger = hardware.dummy.TimeTagger()
    laser = hardware.dummy.Laser()
    power_meter = hardware.dummy.PowerMeter()

    from tools.emod import JobManager

    JobManager().start()

    saturation = Saturation(time_tagger, laser, power_meter)
    saturation.edit_traits()
