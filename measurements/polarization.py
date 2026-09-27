# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import logging

import numpy as np
from chaco.api import ArrayPlotData
from enable.api import ComponentEditor
from traits.api import Range, Array, Instance
from traitsui.api import View, Item, HGroup

from tools.chaco_addons import SavePlot as Plot, SaveTool
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin


class Polarization(ManagedJob, GetSetItemsMixin):
    """
    Record a polarization curve.
    
    written by: helmut.fedder@gmail.com
    last modified: 2012-10-25
    """
    seconds_per_point = Range(low=1e-4, high=100., value=1., desc='integration time for one point',
                              label='seconds per point', mode='text', auto_set=False, enter_set=True)
    angle_step = Range(low=1e-3, high=100., value=1., desc='angular step', label='angle step', mode='text',
                       auto_set=False, enter_set=True)

    angle = Array()
    intensity = Array()
    power = Array()

    plot = Instance(Plot)
    plot_data = Instance(ArrayPlotData)

    get_set_items = ['__doc__', 'seconds_per_point', 'angle_step', 'angle', 'intensity', 'power']

    def __init__(self, time_tagger, rotation_stage, power_meter=None, **kwargs):
        super(Polarization, self).__init__(**kwargs)
        self.time_tagger = time_tagger
        self.rotation_stage = rotation_stage
        self.power_meter = power_meter
        self._create_plot()
        self.on_trait_change(self._update_index, 'angle', dispatch='ui')
        self.on_trait_change(self._update_value, 'intensity', dispatch='ui')

    def _run(self):
        """Acquire data."""

        try:  # run the acquisition
            self.state = 'run'

            self.rotation_stage.go_home()

            self.angle = np.array(())
            self.intensity = np.array(())
            self.power = np.array(())

            c1 = self.time_tagger.Countrate(0)
            c2 = self.time_tagger.Countrate(1)

            for phi in np.arange(0., 360., self.angle_step):
                self.rotation_stage.set_angle(phi)
                c1.clear()
                c2.clear()
                self.thread.stop_request.wait(self.seconds_per_point)
                if self.thread.stop_request.is_set():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    self.state = 'idle'
                    break
                self.angle = np.append(self.angle, phi)
                self.intensity = np.append(self.intensity, c1.getData() + c2.getData())
                if self.power_meter:
                    self.power = np.append(self.power, self.power_meter.getPower())
                else:
                    self.power = np.append(self.power, -1)
            else:
                self.state = 'done'

        except:  # if anything fails, recover
            logging.getLogger().exception('Error in polarization.')
            self.state = 'error'
        finally:
            del c1
            del c2

    def _create_plot(self):
        plot_data = ArrayPlotData(angle=np.array(()), intensity=np.array(()), )
        plot = Plot(plot_data, padding=8, padding_left=64, padding_bottom=64)
        plot.plot(('angle', 'intensity'), color='blue')
        plot.index_axis.title = 'angle [deg]'
        plot.value_axis.title = 'intensity [count/s]'
        plot.tools.append(SaveTool(plot))
        self.plot_data = plot_data
        self.plot = plot

    def _update_index(self, new):
        self.plot_data.set_data('angle', new)

    def _update_value(self, new):
        self.plot_data.set_data('intensity', new)

    def save_plot(self, filename):
        save_figure(self.plot, filename)

    traits_view = View(HGroup(Item('submit_button', show_label=False),
                              Item('remove_button', show_label=False),
                              Item('priority'),
                              Item('state', style='readonly'),
                              ),
                       HGroup(Item('filename', springy=True),
                              Item('save_button', show_label=False),
                              Item('load_button', show_label=False)
                              ),
                       HGroup(Item('seconds_per_point'),
                              Item('angle_step'),
                              ),
                       Item('plot', editor=ComponentEditor(), show_label=False),
                       title='Polarization', width=640, height=640, buttons=[], resizable=True
                       )


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().info('Starting logger.')

    from tools.emod import JobManager

    JobManager().start()

    p = Polarization()
    p.edit_traits()
