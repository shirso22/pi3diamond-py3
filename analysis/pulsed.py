"""
This module provides analysis of pulsed measurements.

The first part provides simple numeric functions.

The second part provides Trait GUIs
"""

import numpy as np

from .fitting import find_edge
from tools.colormaps import viridis, navia


def spin_state(c, dt, T, t0=0.0, t1=-1.):
    """
    Compute the spin state from a 2D array of count data.
    
    Parameters:
    
        c    = count data
        dt   = time step
        t0   = beginning of integration window relative to the edge
        t1   = None or beginning of integration window for normalization relative to edge
        T    = width of integration window
        
    Returns:
    
        y       = 1D array that contains the spin state
        profile = 1D array that contains the pulse profile
        edge    = position of the edge that was found from the pulse profile
        
    If t1<0, no normalization is performed. If t1>=0, each data point is divided by
    the value from the second integration window and multiplied with the mean of
    all normalization windows.
    """

    profile = c.sum(0)
    edge = find_edge(profile)

    I = int(round(T / float(dt)))
    i0 = edge + int(round(t0 / float(dt)))
    y = np.empty((c.shape[0],))
    for i, slot in enumerate(c):
        y[i] = slot[i0:i0 + I].sum()
    if t1 >= 0:
        i1 = edge + int(round(t1 / float(dt)))
        y1 = np.empty((c.shape[0],))
        for i, slot in enumerate(c):
            y1[i] = slot[i1:i1 + I].sum()
        y = y / y1 * y1.mean()
    return y, profile, edge


#########################################
# Trait GUIs for pulsed fits
#########################################

from traits.api import Instance, Any, Str, Tuple, on_trait_change, Array
from traitsui.api import View, Item, Tabbed, VGroup, VSplit, InstanceEditor
from enable.api import ComponentEditor
from chaco.api import ArrayDataSource, LinePlot, LinearMapper, ArrayPlotData, PlotLabel, \
    PlotGraphicsContext
from tools.chaco_addons import SavePlot as Plot, SaveTool, ClickTool
from chaco.tools.api import PanTool, ZoomTool

import logging
from tools.utility import GetSetItemsMixin


def save_figure(plot, filename='Z:/python_data_temp/default_image.png'):
    """Function to save plotted data to an image file.

    We always use the full boundaries of the plotted graph.
    """
    gc = PlotGraphicsContext(plot.figure_container.outer_bounds, dpi=72)
    gc.render_component(plot)
    gc.save(plot)


class PulsedTool(GetSetItemsMixin):
    """
    Base class for a pulsed analysis. Provides calculation of spin state
    and plotting.
    Derive from this to create analysis tools for pulsed measurements.
    """

    # the measurement to analyze
    measurement = Any(editor=InstanceEditor)

    # plotting
    matrix_data = Instance(ArrayPlotData)
    line_data = Instance(ArrayPlotData)
    pulse_data = Instance(ArrayPlotData)
    matrix_plot = Instance(Plot, editor=ComponentEditor())
    pulse_plot = Instance(Plot, editor=ComponentEditor())
    line_plot = Instance(Plot, editor=ComponentEditor())

    get_set_items = ['__doc__', 'measurement']

    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-200,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-200,
                                          resizable=True),
                                     ),
                              ),
                       title='Pulsed Tool',
                       buttons=[],
                       resizable=True,
                       height=-640
                       )

    def __init__(self, **kwargs):
        super(PulsedTool, self).__init__(**kwargs)
        self._create_matrix_plot()
        self._create_pulse_plot()
        self._create_line_plot()
        self.on_trait_change(self._update_matrix_index, 'measurement.time_bins,measurement.n_laser',
                             dispatch='ui')
        self.on_trait_change(self._update_matrix_value, 'measurement.count_data', dispatch='ui')
        self.on_trait_change(self._update_pulse_index, 'measurement.time_bins', dispatch='ui')
        self.on_trait_change(self._update_pulse_value, 'measurement.pulse', dispatch='ui')
        self.on_trait_change(self._update_line_plot_value, 'measurement.spin_state', dispatch='ui')
        self.on_trait_change(self._on_edge_change, 'measurement.edge', dispatch='ui')

    # plotting
    def _create_matrix_plot(self):
        matrix_data = ArrayPlotData(image=np.zeros((2, 2)))
        plot = Plot(matrix_data, width=500, height=500, resizable='hv', padding=8, padding_left=48,
                    padding_bottom=36)
        plot.index_axis.title = 'time [ns]'
        plot.value_axis.title = 'laser pulse #'
        plot.img_plot('image',
                      xbounds=(0, 1),
                      ybounds=(0, 1),
                      colormap=navia)[0]
        plot.tools.append(SaveTool(plot))
        self.matrix_data = matrix_data
        self.matrix_plot = plot

    def _create_pulse_plot(self):
        pulse_data = ArrayPlotData(x=np.array((0., 0.1, 0.2)), y=np.array((0, 1, 2)))
        plot = Plot(pulse_data, padding=8, padding_left=64, padding_bottom=36)
        line = plot.plot(('x', 'y'), style='line', color='blue', name='data')[0]
        plot.index_axis.title = 'time [ns]'
        plot.value_axis.title = 'intensity'
        edge_marker = LinePlot(index=ArrayDataSource(np.array((0, 0))),
                               value=ArrayDataSource(np.array((0, 1e9))),
                               color='red',
                               index_mapper=LinearMapper(range=plot.index_range),
                               value_mapper=LinearMapper(range=plot.value_range),
                               name='marker')
        plot.add(edge_marker)
        plot.tools.append(SaveTool(plot))
        self.pulse_data = pulse_data
        self.pulse_plot = plot

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)), spin_state=np.array((0, 0)), )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.plot(('index', 'spin_state'), type='scatter', marker="circle", marker_size=3, color='blue')
        plot.index_axis.title = 'pulse #'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_matrix_index(self):
        if self.measurement is not None:
            self.matrix_plot.components[0].index.set_data(
                (self.measurement.time_bins[0], self.measurement.time_bins[-1]),
                (0.0, float(self.measurement.n_laser)))

    def _update_matrix_value(self):
        if self.measurement is not None:
            s = self.measurement.count_data.shape
            if not s[0] * s[1] > 1000000:
                self.matrix_data.set_data('image', self.measurement.count_data)

    def _update_pulse_index(self):
        if self.measurement is not None:
            self.pulse_data.set_data('x', self.measurement.time_bins)

    def _update_pulse_value(self):
        if self.measurement is not None:
            self.pulse_data.set_data('y', self.measurement.pulse)

    def _on_edge_change(self):
        if self.measurement is not None:
            y = self.measurement.edge
            self.pulse_plot.components[1].index.set_data(np.array((y, y)))

    def _update_line_plot_value(self):
        if self.measurement is not None:
            y = self.measurement.spin_state
            n = len(y)
            old_index = self.line_data.get_data('index')
            if old_index is not None and len(old_index) != n:
                self.line_data.set_data('index', np.arange(n))
            self.line_data.set_data('spin_state', y)

    def save_matrix_plot(self, filename):
        save_figure(self.matrix_plot, filename)

    def save_line_plot(self, filename):
        save_figure(self.line_plot, filename)


class PulsedToolTau(PulsedTool):
    """
    Analysis of a pulsed measurement with a 'tau' as index-data.
    """

    # overwrite __init__ such that change of 'tau' causes plot update 
    def __init__(self, **kwargs):
        super(PulsedToolTau, self).__init__(**kwargs)
        self.on_trait_change(self._on_tau_change, 'measurement.tau', dispatch='ui')

    # overwrite the line_plot such that the x-axis label is time 
    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)), spin_state=np.array((0, 0)), )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    # overwrite this one to throw out setting of index data according to length of spin_state
    def _update_line_plot_value(self):
        y = self.measurement.spin_state
        self.line_data.set_data('spin_state', y)

    # provide method for update of tau
    def _on_tau_change(self):
        self.line_data.set_data('index', self.measurement.tau * 1e-3)

    # overwrite this to change the window title
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     ),
                              ),
                       title='Pulsed Analysis Tau',
                       buttons=[], resizable=True
                       )


# from measurments.cpmg import CPMG3pi2

class PulsedToolDoubleTau(PulsedToolTau):
    """
    Analysis of a pulsed measurement with a 'tau' as index-data,
    two subsequent pulsed sequences and bright / dark reference
    measurement at the end of the sequence.
    """

    # def __init__(self, **kwargs):
    #    super(PulsedToolDoubleTau, self).__init__(**kwargs)

    # overwrite the line_plot such that the bright and dark state
    # as well as reference lines are plotted 
    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'first'), color='blue', name='first')
        plot.plot(('index', 'second'), color='green', name='second')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    # overwrite this one to provide splitting up of spin_state array
    # and setting of bright and dark state data
    def _update_line_plot_value(self):
        y = self.measurement.spin_state
        n = len(y) // 2
        first = y[:n]
        second = y[n:2 * n]
        try:
            self.line_data.set_data('first', first)
            self.line_data.set_data('second', second)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    # overwrite this to change the window title
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     ),
                              ),
                       title='Pulsed Measurement',
                       buttons=[], resizable=True
                       )

class PulsedToolTripleTau(PulsedToolTau): #change from 03.09.2026
    """
    Analysis tool for three tau-dependent pulse sequences.

    Sequence 1:
        tau -> readout
    Sequence 2:
        tau -> MW -> readout
    Sequence 3:
        MW -> tau -> readout
    """

    def _create_line_plot(self):

        line_data = ArrayPlotData(
            index=np.array((0, 1)),
            first=np.array((0, 0)),
            second=np.array((0, 0)),
            third=np.array((0, 0))
        )

        plot = Plot(
            line_data,
            padding=8,
            padding_left=64,
            padding_bottom=36
        )

        plot.plot(
            ('index', 'first'),
            color='blue',
            name='T1'
        )

        plot.plot(
            ('index', 'second'),
            color='red',
            name='tau-MW'
        )

        plot.plot(
            ('index', 'third'),
            color='green',
            name='MW-tau'
        )

        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'

        plot.tools.append(SaveTool(plot))

        self.line_data = line_data
        self.line_plot = plot

    def _create_contrast_plot(self):

        contrast_data = ArrayPlotData(
            index=np.array((0, 1)),
            contrast_1=np.array((0, 0)),
            contrast_2=np.array((0, 0))
        )

        plot = Plot(
            contrast_data,
            padding=8,
            padding_left=64,
            padding_bottom=36
        )

        plot.plot(
            ('index', 'contrast_1'),
            color='black',
            name='T1 - tau-MW'
        )

        plot.plot(
            ('index', 'contrast_2'),
            color='red',
            name='T1 - MW-tau'
        )

        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'contrast'

        plot.tools.append(SaveTool(plot))

        self.contrast_data = contrast_data
        self.contrast_plot = plot

    def _update_line_plot_value(self):

        y = self.measurement.spin_state

        n = len(y) // 3

        first = y[:n]
        second = y[n:2*n]
        third = y[2*n:3*n]

        self.line_data.set_data('first', first)
        self.line_data.set_data('second', second)
        self.line_data.set_data('third', third)

    def _update_contrast_plot_value(self):

        y = self.measurement.spin_state

        n = len(y) // 3

        first = y[:n]
        second = y[n:2*n]
        third = y[2*n:3*n]

        contrast_1 = first - second
        contrast_2 = first - third

        self.contrast_data.set_data(
            'contrast_1',
            contrast_1
        )

        self.contrast_data.set_data(
            'contrast_2',
            contrast_2
        )

    def _on_tau_change(self):

        index = self.measurement.tau * 1e-3

        self.line_data.set_data(
            'index',
            index
        )

        self.contrast_data.set_data(
            'index',
            index
        )

    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('contrast_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     ),
                              ),
                       title='Pulsed Measurement',
                       buttons=[], resizable=True
                       )

class FitToolTau(PulsedToolTau):
    """
    Base class for PulsedTool with a tau and fit.
    """

    # fit results
    fit_result = Tuple()
    label_text = Str('')

    # add fit results to the get_set_items
    get_set_items = PulsedToolTau.get_set_items + ['fit_result', 'label_text']

    # overwrite __init__ to trigger update events
    def __init__(self, **kwargs):
        super(FitToolTau, self).__init__(**kwargs)
        self.on_trait_change(self._update_fit, 'measurement.spin_state', dispatch='ui')
        self.on_trait_change(self._on_fit_result_change, 'fit_result', dispatch='ui')
        self.on_trait_change(self._on_label_text_change, 'label_text', dispatch='ui')

    def _update_fit(self):
        pass

    # overwrite the line_plot to include fit and text label
    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  spin_state=np.array((0, 0)),
                                  fit=np.array((0, 0)))
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.plot(('index', 'fit'), color='red', name='fit')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.overlays.insert(0, PlotLabel(text=self.label_text, hjustify='left', vjustify='bottom',
                                          position=[64, 32]))
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _on_fit_result_change(self, new):
        pass

    def _on_label_text_change(self, new):
        self.line_plot.overlays[0].text = new


class PulsedToolDoubleTauLog(PulsedToolDoubleTau):
    """This class plots a double sequence measurement with a logarithmic tau scale.
    
    Use for T1 measurements.
    """

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

    # overwrite this to change the window title
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     ),
                              ),
                       title='Logarithmic Pulsed Measurement',
                       buttons=[], resizable=True
                       )


class InteractiveFit(PulsedToolTau):
    """Class to interactively load and fit measurements that have two distinct sequences.
    
    """

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  difference=np.array((0, 0))
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'first'), color='blue', name='first')
        plot.plot(('index', 'second'), color='green', name='second')
        plot.plot(('index', 'difference'), color='red', name='difference')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    # overwrite this one to provide splitting up of spin_state array
    # and setting of bright and dark state data 
    def _update_line_plot_value(self):
        y = self.measurement.spin_state
        n = len(y) // 2
        first = y[:n]
        second = y[n:2 * n]
        difference = (first - second) + (first.max() + second.min()) / 2.
        try:
            self.line_data.set_data('first', first)
            self.line_data.set_data('second', second)
            self.line_data.set_data('difference', difference)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    # overwrite this to change the window title
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     ),
                              ),
                       title='Interactive Fit',
                       buttons=[], resizable=True
                       )


class PlotTool(GetSetItemsMixin):
    """Class to plot measurements with a tau variable.

    This class provides methods for plotting and evaluating the outcome of a measurement in the form
    of a spin_state(tau) graph. Additionally it is decided, if the measurements consists of two
    sequences, which are then plotted in different lines.
    To include in a measurement inherit from this and include the traits variables 'line_plot',
    'matrix_plot' and 'pulse_plot' in the view window.
    WARNING: This class will not run without a PulsedTau class.
    """

    # plotting
    matrix_data = Instance(ArrayPlotData)
    line_data = Instance(ArrayPlotData)
    pulse_data = Instance(ArrayPlotData)
    contrast_data = Instance(ArrayPlotData)

    matrix_plot = Instance(Plot, editor=ComponentEditor())
    pulse_plot = Instance(Plot, editor=ComponentEditor())
    line_plot = Instance(Plot, editor=ComponentEditor())
    contrast_plot = Instance(Plot, editor=ComponentEditor())
    click_tool = Instance(ClickTool)
    click_coords = Array(value=np.array((np.nan,)), label='[x, y]')

    double_sequence = True

    # Fitting
    fit_result = Tuple()
    label_text = Str('')

    get_set_items = ['__doc__']

    # Standalone view class. This needs to be overwritten for each inheriting class!
    traits_view = View(
        VGroup(
            Tabbed(
                Item('line_plot', show_label=False, width=500, height=-200, resizable=True),
                Item('matrix_plot', show_label=False, width=500, height=-200, resizable=True),
                Item('pulse_plot', show_label=False, width=500, height=-200, resizable=True),
            ),
        ),
        title='Pulsed Tool',
        buttons=[],
        resizable=True,
        height=-640
    )

    def __init__(self, **kwargs):
        super(PlotTool, self).__init__(**kwargs)
        self._create_matrix_plot()
        self._create_pulse_plot()
        self._create_line_plot()
        self._create_contrast_plot()

        # These attributes have to be found in the measurement class. See PulsedTau.
        self.on_trait_change(self._update_matrix_index, 'time_bins, n_laser', dispatch='ui')
        self.on_trait_change(self._update_matrix_value, 'count_data', dispatch='ui')

        self.on_trait_change(self._update_pulse_index, 'time_bins', dispatch='ui')
        self.on_trait_change(self._update_pulse_value, 'pulse', dispatch='ui')
        self.on_trait_change(self._on_edge_change, 'edge', dispatch='ui')

        self.on_trait_change(self._on_tau_change, 'tau', dispatch='ui')
        self.on_trait_change(self._update_line_plot_value, 'spin_state', dispatch='ui')
        self.on_trait_change(self._update_contrast_plot_value, 'spin_state', dispatch='ui')

        # If a Fit exists:
        self.on_trait_change(self._update_fit, 'spin_state', dispatch='ui')
        self.on_trait_change(self._on_fit_result_change, 'fit_result', dispatch='ui')
        self.on_trait_change(self._on_label_text_change, 'label_text', dispatch='ui')

    # plotting
    def _create_matrix_plot(self):
        matrix_data = ArrayPlotData(image=np.zeros((2, 2)))
        plot = Plot(matrix_data, width=500, height=500, resizable='hv', padding=8, padding_left=48,
                    padding_bottom=36)
        plot.index_axis.title = 'time [ns]'
        plot.value_axis.title = 'laser pulse #'
        plot.img_plot('image', xbounds=(0, 1), ybounds=(0, 1), colormap=viridis)[0]
        plot.tools.append(SaveTool(plot))
        plot.tools.append(PanTool(plot))
        plot.tools.append(ZoomTool(plot))

        self.matrix_data = matrix_data
        self.matrix_plot = plot

    def _create_pulse_plot(self):
        pulse_data = ArrayPlotData(x=np.array((0., 0.1, 0.2)), y=np.array((0, 1, 2)))
        plot = Plot(pulse_data, padding=8, padding_left=64, padding_bottom=36)
        line = plot.plot(('x', 'y'), style='line', color='blue', name='data')[0]
        plot.index_axis.title = 'time [ns]'
        plot.value_axis.title = 'intensity'
        edge_marker = LinePlot(index=ArrayDataSource(np.array((0, 0))),
                               value=ArrayDataSource(np.array((0, 1e9))),
                               color='red',
                               index_mapper=LinearMapper(range=plot.index_range),
                               value_mapper=LinearMapper(range=plot.value_range),
                               name='marker')
        plot.add(edge_marker)
        plot.tools.append(SaveTool(plot))
        plot.tools.append(PanTool(plot))
        plot.tools.append(ZoomTool(plot))
        self.pulse_data = pulse_data
        self.pulse_plot = plot

    def _create_line_plot(self):
        """Set up the line plot.

        Decide if its a double sequence and act accordingly.
        :return: None.
        """
        if self.double_sequence:
            line_data = ArrayPlotData(index=np.array((0, 1)),
                                      first=np.array((0, 0)),
                                      second=np.array((0, 0)),
                                      )
            plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
            plot.plot(('index', 'first'), color='blue', name='first')
            plot.plot(('index', 'first'), type='scatter', marker="circle", marker_size=2, color='blue')
            plot.plot(('index', 'second'), color='green', name='second')
            plot.plot(('index', 'second'), type='scatter', marker="circle", marker_size=2, color='green')
            plot.index_axis.title = 'time [micro s]'
            plot.value_axis.title = 'spin state'
            plot.tools.append(SaveTool(plot))
            plot.tools.append(PanTool(plot))
            plot.tools.append(ZoomTool(plot))
            self.click_tool = ClickTool(plot)
            plot.tools.append(self.click_tool)

            self.line_data = line_data
            self.line_plot = plot
        else:
            line_data = ArrayPlotData(index=np.array((0, 1)),
                                      spin_state=np.array((0, 0)),
                                      fit=np.array((0, 0)))
            plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
            plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
            plot.plot(('index', 'spin_state'), type='scatter', marker="circle", marker_size=3, color='blue')
            plot.plot(('index', 'fit'), color='red', name='fit')
            plot.index_axis.title = 'time [micro s]'
            plot.value_axis.title = 'spin state'
            plot.tools.append(SaveTool(plot))
            plot.tools.append(PanTool(plot))
            plot.tools.append(ZoomTool(plot))
            self.click_tool = ClickTool(plot)
            plot.tools.append(self.click_tool)

            self.line_data = line_data
            self.line_plot = plot

    def _create_contrast_plot(self):
        contrast_data = ArrayPlotData(index=np.array((0, 1)), contrast=np.array((0, 0)))
        plot = Plot(contrast_data, padding=8, padding_left=80, padding_bottom=48)
        plot.plot(('index', 'contrast'), color='blue', name='contrast')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'contrast'
        plot.tools.append(SaveTool(plot))
        plot.tools.append(PanTool(plot))
        plot.tools.append(ZoomTool(plot))
        self.contrast_data = contrast_data
        self.contrast_plot = plot

    def _update_matrix_index(self):
        self.matrix_plot.components[0].index.set_data(
            (self.time_bins[0], self.time_bins[-1]),
            (0.0, float(self.n_laser)))

    def _update_matrix_value(self):
        s = self.count_data.shape
        if not s[0] * s[1] > 1000000:
            self.matrix_data.set_data('image', self.count_data)

    def _update_pulse_index(self):
        self.pulse_data.set_data('x', self.time_bins)

    def _update_pulse_value(self):
        self.pulse_data.set_data('y', self.pulse)

    def _update_fit(self):
        """Container for Fit update.

        This has to be implemented separately for every class.
        :return: None.
        """
        pass

    def _on_fit_result_change(self, new):
        """Container for Fit update.

        This has to be implemented separately for every class.
        :return: None.
        """
        pass

    def _on_label_text_change(self, new):
        """Update Fit label displayed in graph.

        :param new: New text Label.
        :return: None.
        """
        self.line_plot.overlays[0].text = new
        self.contrast_plot.overlays[0].text = new

    def _on_edge_change(self):
        y = self.edge
        self.pulse_plot.components[1].index.set_data(np.array((y, y)))

    def _on_tau_change(self):
        """Handle tau changes

        :return: None.
        """
        self.line_data.set_data('index', self.tau * 1e-3)
        self.contrast_data.set_data('index', self.tau * 1e-3)

    def _update_line_plot_value(self):
        """Handle spin_state changes.

        Case sensitive on double sequence.
        :return: None.
        """
        if self.double_sequence:
            y = self.spin_state
            n = len(y) // 2
            first = y[:n]
            second = y[n:2 * n]
            try:
                self.line_data.set_data('first', first)
                self.line_data.set_data('second', second)
            except Exception as e:
                print(e)
        else:
            y = self.spin_state
            self.line_data.set_data('spin_state', y)

    def _update_contrast_plot_value(self):
        y = self.spin_state
        n = len(y) // 2
        first = y[:n]
        second = y[n:2 * n]
        contrast = first - second
        try:
            self.contrast_data.set_data('contrast', contrast)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    @on_trait_change("click_tool:click_coords")
    def _change_click_coords(self):
        self.click_coords = self.click_tool.click_coords

    def save_matrix_plot(self, filename):
        save_figure(self.matrix_plot, filename)

    def save_line_plot(self, filename):
        save_figure(self.line_plot, filename)

    def save_contrast_plot(self, filename):
        save_figure(self.contrast_plot, filename)

