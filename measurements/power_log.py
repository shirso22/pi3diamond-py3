# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
from hardware.api import MicrowavePowerMeter
from traits.api import Array

from tools.emod import FreeJob


class PowerLog(FreeJob):
    time_trace = Array()

    measurement_interval = Range(low=1e-3, high=1e3, value=1.0)

    max_trace_length = Range(10, 10000000, 10000)

    def run(self):
        """Acquire the time trace."""
        try:
            self.state = 'run'
            # initialize time trace data with first data point
            self.time_trace = np.array((time.time(), MicrowavePowerMeter().get_power()), ndmin=2)

            while True:

                # wait for a stop request until taking next sata point
                threading.current_thread().stop_request.wait(self.measurement_interval)
                # abort the loop if stop signal is set
                if threading.current_thread().stop_request.is_set():
                    break
                # append a tuple (time,power) to the time trace data 
                self.time_trace = np.vstack((self.time_trace, (time.time(), MicrowavePowerMeter().get_power())))
            self.state = 'idle'
        except:
            logging.getLogger().exception('Error in power log.')
            self.state = 'error'

            # plotting

    def _create_plot(self):
        line_data = ArrayPlotData(frequency=np.array((0., 1.)), counts=np.array((0., 0.)))
        line_plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=32)
        line_plot.plot(('frequency', 'counts'), style='line', color='blue')
        line_plot.index_axis.title = 'Frequency [MHz]'
        line_plot.value_axis.title = 'Fluorescence counts'
        line_label = PlotLabel(text='', hjustify='left', vjustify='bottom', position=[64, 128])
        line_plot.overlays.append(line_label)
        self.line_label = line_label
        self.line_data = line_data
        self.line_plot = line_plot

    def run(self):
        """Acquire the time trace."""
