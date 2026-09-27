# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
This Module supplies monitoring of System Parameters including long term charts.

Monitor the pressure and the Temperature to extract Long term effects or sudden changes.
We define 3 Channels on the NI-Cards which we read out periodically and display in seperate Graphs. 
"""

import queue
import ctypes
import threading
import time

import numpy
from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator
from chaco.api import (ArrayPlotData, Plot, PlotAxis, add_default_grids, VPlotContainer)
from chaco.tools.api import PanTool, ZoomTool
from enable.api import ComponentEditor
# PY3-PORT: Traits 6.0 removed the Singleton* base classes.
from traits.api import Instance, Range, Array, Enum
from tools.ets_compat import SingletonHasTraits
from traitsui.api import (View, Item, HGroup, VGroup, EnumEditor)

from hardware.nidaq import AITask
from tools.utility import StoppableThread


class SystemMonitor(SingletonHasTraits):
    """Monitor various parameters of the system.
    
    Monitor voltages and calculate the respective parameter from them.
    Then display these values in a long term chart with user controlled readout interval.
    Additionally provide means to save periodically.
    """

    # class variables
    state = Enum('idle', 'run')
    time_data = Array()
    p_prep_data = Array()
    p_main_data = Array()
    t_room_data = Array()

    # measurement parameters
    t_update = Range(low=0.2, high=300, value=2.0, desc='Seconds between readout',
                     label='Seconds between readout', mode='text', auto_set=False, enter_set=True)
    n_data_points = Range(low=10, high=1000000, value=100, desc='Number of points in Line Plot',
                          label='Number of points in Line Plot', mode='text', auto_set=False,
                          enter_set=True)

    # visualization variables
    p_prep_plot_data = Instance(ArrayPlotData)
    p_main_plot_data = Instance(ArrayPlotData)
    t_room_plot_data = Instance(ArrayPlotData)
    plots = Instance(VPlotContainer)
    traits_view = View(VGroup(HGroup(
        Item('state', style='custom', show_label=False,
             editor=EnumEditor(values={'idle': '1:idle', 'run': '2:run'},
                               cols=2)
             )
    ),
        HGroup(Item('t_update', width=-60),
               Item('n_data_points', width=-60),
               ),
        Item('plots', editor=ComponentEditor(), show_label=False, width=400,
             height=600, resizable=True)
    ),
        title='System Monitor', buttons=[], resizable=True
    )

    def __init__(self, channel1, channel2, channel3, N, f):
        """Constructor. Initialze 3 Voltage readout channels on NICards.
        
        channel1 - channel for pressure in prep-chamber.
        channel2 - channel for pressure in main-chamber.
        channel3 - channel for temperature in room.
        """
        SingletonHasTraits.__init__(self)
        DAQmx_Val_RSE = ctypes.c_int32(10083)
        self.n_voltage = N
        self.f_voltage = f
        self.p_prep = AITask(channel1, N, f)
        self.p_main = AITask(channel2, N, f)
        self.t_room = AITask(channel3, N, f)
        self.on_trait_change(self._update_plot_indices, 'time_data', dispatch='ui')
        self.on_trait_change(self._update_plot_values, 'p_prep_data', dispatch='ui')
        self.on_trait_change(self._update_plot_values, 'p_main_data', dispatch='ui')
        self.on_trait_change(self._update_plot_values, 't_room_data', dispatch='ui')

    def _state_changed(self):
        """Function to kill and start the measurement thread on user input."""
        self._stop()
        if self.state == 'run':
            self._start()

    def _p_prep_plot_data_default(self):
        """Return default data for Plots."""
        return ArrayPlotData(time_data=self.time_data, p_prep_data=self.p_prep_data)

    def _p_main_plot_data_default(self):
        """Return default data for Plots."""
        return ArrayPlotData(time_data=self.time_data, p_main_data=self.p_main_data)

    def _t_room_plot_data_default(self):
        """Return default data for Plots."""
        return ArrayPlotData(time_data=self.time_data, t_room_data=self.t_room_data)

    def _plots_default(self):
        """Return Default Plots."""
        # plot p_prep
        p_prep_plot = Plot(self.p_prep_plot_data,
                           padding=8, padding_left=72, padding_bottom=32)
        p_prep_plot.plot(('time_data', 'p_prep_data'), style='line', color='blue', value_scale='log')
        p_prep_plot.index_axis = PlotAxis(p_prep_plot, orientation="bottom",
                                          tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        hgrid, vgrid = add_default_grids(p_prep_plot)
        vgrid.tick_generator = p_prep_plot.index_axis.tick_generator
        p_prep_plot.index_axis.title = 'time'
        p_prep_plot.value_axis.title = 'pressure prep-chamber'
        p_prep_plot.tools.append(PanTool(p_prep_plot, constrain=True, constrain_direction='x'))
        p_prep_plot.overlays.append(ZoomTool(p_prep_plot))
        # plot p_main
        p_main_plot = Plot(self.p_main_plot_data,
                           padding=8, padding_left=72, padding_bottom=32)
        p_main_plot.plot(('time_data', 'p_main_data'), style='line', color='red', value_scale='log')
        p_main_plot.index_axis = PlotAxis(p_main_plot, orientation="bottom",
                                          tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        hgrid, vgrid = add_default_grids(p_main_plot)
        vgrid.tick_generator = p_main_plot.index_axis.tick_generator
        p_main_plot.index_axis.title = 'time'
        p_main_plot.value_axis.title = 'pressure main-chamber'
        p_main_plot.tools.append(PanTool(p_main_plot, constrain=True, constrain_direction='x'))
        p_main_plot.overlays.append(ZoomTool(p_main_plot))
        # plot t_room
        t_room_plot = Plot(self.t_room_plot_data,
                           padding=8, padding_left=72, padding_bottom=32)
        t_room_plot.plot(('time_data', 't_room_data'), style='line', color='green')
        t_room_plot.index_axis = PlotAxis(t_room_plot, orientation="bottom",
                                          tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        hgrid, vgrid = add_default_grids(t_room_plot)
        vgrid.tick_generator = t_room_plot.index_axis.tick_generator
        t_room_plot.index_axis.title = 'time'
        t_room_plot.value_axis.title = 'room temperature'
        t_room_plot.tools.append(PanTool(t_room_plot, constrain=True, constrain_direction='x'))
        t_room_plot.overlays.append(ZoomTool(t_room_plot))
        # combine plots in container
        plots = VPlotContainer(p_prep_plot, p_main_plot, t_room_plot, bgcolor="lightblue")
        return plots

    def _time_data_default(self):
        """Return default time array."""
        t = time.time()
        return numpy.array([t for _ in range(self.n_data_points)])

    def _p_prep_data_default(self):
        """Return default p_prep_data array."""
        pp = self.read_p_prep()
        return numpy.array([pp for _ in range(self.n_data_points)])

    def _p_main_data_default(self):
        """Return default p_prep_data array."""
        pm = self.read_p_main()
        return numpy.array([pm for _ in range(self.n_data_points)])

    def _t_room_data_default(self):
        """Return default p_prep_data array."""
        tr = self.read_t_room()
        return numpy.array([tr for _ in range(self.n_data_points)])

    def _update_plot_indices(self):
        """Protected function for updating the x-Axis of the plots (time)"""
        self.p_prep_plot_data.set_data('time_data', self.time_data)
        self.p_main_plot_data.set_data('time_data', self.time_data)
        self.t_room_plot_data.set_data('time_data', self.time_data)

    def _update_plot_values(self):
        """Protected function for updating the y-Axis of the plots (pressure, temperature...)"""
        self.p_prep_plot_data.set_data('p_prep_data', self.p_prep_data)
        self.p_main_plot_data.set_data('p_main_data', self.p_main_data)
        self.t_room_plot_data.set_data('t_room_data', self.t_room_data)

    def _start(self, timeout=10.):
        """Determines what to do when the measurement is started.
        
        Starts a thread that targets run().
        """
        self._stop()
        self.thread = StoppableThread(target=self.run, timeout=timeout,
                                      name=self.__class__.__name__ +
                                           time.strftime('%y-%m-%d_%Hh%Mm%S', time.localtime()))
        self.thread.command_queue = queue.Queue()
        self.thread.start()

    def _stop(self, timeout=None):
        """Determines what to do when the measurement is stopped.
        
        Kills the thread which targets run().
        """
        if hasattr(self, 'thread'):
            self.thread.stop(timeout=timeout)

    def read_p_prep(self):
        """Readout Voltage of pressure gauge in prep chamber and calculate pressure."""
        self.p_prep.Start()
        self.p_prep.Wait()
        try:
            V = self.p_prep.Read()
        except Exception as e:
            print('Unexpected error in read_p_prep')
            print(str(e))
        V_mean = V.sum() / V.size
        p_prep = 10 ** (1.25 * V_mean - 12.75)
        self.p_prep.Stop()
        return p_prep

    def read_p_main(self):
        """Readout Voltage of pressure gauge in main chamber and calculate pressure."""
        self.p_main.Start()
        self.p_main.Wait()
        try:
            V = self.p_main.Read()
        except Exception as e:
            print('Unexpected error in read_p_main')
        V_mean = V.sum() / V.size
        p_main = 10 ** (1.25 * V_mean - 12.75)
        self.p_main.Stop()
        return p_main

    def read_t_room(self):
        """Readout Voltage of PT100 Temperature-sensor and calculate Temperature."""
        self.t_room.Start()
        self.t_room.Wait()
        try:
            V = self.t_room.Read()
        except Exception as e:
            print('Unexpected error in read_t_room')
        V_mean = V.sum() / V.size
        t_room = ((400.0 / 10.0) * V_mean) - 273.15
        self.t_room.Stop()
        return t_room

    def run(self):
        """Measurement loop, that periodically reads values and keeps the graph updated.
        
        This is the work loop that we run in a thread and which can be stopped and started using
        self.start() and self.stop().
        """
        self.time_data = self._time_data_default()
        self.p_prep_data = self._p_prep_data_default()
        self.p_main_data = self._p_main_data_default()
        self.t_room_data = self._t_room_data_default()
        while (True):
            try:
                if threading.current_thread().stop_request.is_set():
                    break
                self.time_data = numpy.hstack((time.time(), self.time_data[:-1]))
                self.p_prep_data = numpy.hstack((self.read_p_prep(), self.p_prep_data[:-1]))
                self.p_main_data = numpy.hstack((self.read_p_main(), self.p_main_data[:-1]))
                self.t_room_data = numpy.hstack((self.read_t_room(), self.t_room_data[:-1]))
            except Exception as e:
                print('Unexpected error in readout loop!')
            time.sleep(self.t_update)


if __name__ == '__main__':
    system_monitor = SystemMonitor('Dev1/ai2', 'Dev1/ai3', 'Dev1/ai4', 10, 100)
    system_monitor.configure_traits()

"""Skript to save SystemMonitor Files:
cd Z:\\python_data_temp
file = open('SystemMonitor1031-1103.txt', 'w')
file.write('System Monitor:' + '\n' + 'Room Temperature:' + '\t' + 'Pressure Prep Chamber:' +
           '\t' + 'Pressure Main Chamber:' + '\n')
for i in range(system_monitor.t_room_data.shape[0]):
    file.write(time.ctime(system_monitor.time_data[i]) + '\t' +
               str(system_monitor.t_room_data[i]) + '\t' +
               str(system_monitor.p_prep_data[i]) + '\t' +
               str(system_monitor.p_main_data[i]) + '\n')
file.write('\n')
file.close()

"""
