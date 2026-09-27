# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import threading

import numpy
from chaco.api import ArrayPlotData, PlotLabel
from enable.api import ComponentEditor
# enthought library imports
from traits.api import Instance, Range, Bool, Array, on_trait_change, String
from traitsui.api import Handler, View, Item, HGroup, Group, VGroup, Tabbed

from tools.chaco_addons import SavePlot as Plot
from tools.emod import Job
from tools.utility import GetSetItemsMixin


class StartThreadHandler(Handler):
    def init(self, info):
        info.object.start()
        # PY3-PORT: TraitsUI 6 requires Handler.init() to return a
        # bool. Falling off the end returns None and raises when the
        # view opens. True means "initialisation succeeded".
        return True


class PhotonTimeTrace(Job, GetSetItemsMixin):
    TraceLength = Range(low=10, high=10000, value=400, desc='Length of Count Trace',
                        label='Trace Length')
    SecondsPerPoint = Range(low=0.001, high=1, value=0.1, desc='Seconds per point [s]',
                            label='Seconds per point [s]')
    RefreshRate = Range(low=0.01, high=1, value=0.1, desc='Refresh rate [s]',
                        label='Refresh rate [s]')
    TotalCounts = String("")

    # trace data
    C0 = Array()
    C1 = Array()
    C2 = Array()
    C3 = Array()
    C4 = Array()
    C5 = Array()
    C6 = Array()
    C7 = Array()
    C0C1 = Array()
    T = Array()

    time = Array()
    c0 = Array()
    c1 = Array()
    c0c1 = Array()

    C0_list = []
    C1_list = []
    C0C1_list = []

    line_label = Instance(PlotLabel)
    line_data = Instance(ArrayPlotData)
    line_plot = Instance(Plot, editor=ComponentEditor())

    c_enable0 = Bool(True, label='C0', desc='enable channel 0')
    c_enable1 = Bool(True, label='C1', desc='enable channel 1')
    c_enable2 = Bool(False, label='C2', desc='enable channel 2')
    c_enable3 = Bool(False, label='C3', desc='enable channel 3')
    c_enable4 = Bool(False, label='C4', desc='enable channel 4')
    c_enable5 = Bool(False, label='C5', desc='enable channel 5')
    c_enable6 = Bool(False, label='C6', desc='enable channel 6')
    c_enable7 = Bool(False, label='C7', desc='enable channel 7')
    sum_enable = Bool(True, label='C0 + C1', desc='enable sum c0 + c1')
    record_data = Bool(False, label='RecordData', desc='Start/Stop saving')

    TracePlot = Instance(Plot)
    TraceData = Instance(ArrayPlotData)

    def __init__(self, time_tagger, **kwargs):
        super(PhotonTimeTrace, self).__init__(**kwargs)
        self.time_tagger = time_tagger
        self.on_trait_change(self._update_T, 'T', dispatch='ui')
        self.on_trait_change(self._update_C0, 'C0', dispatch='ui')
        self.on_trait_change(self._update_C1, 'C1', dispatch='ui')
        self.on_trait_change(self._update_C2, 'C2', dispatch='ui')
        self.on_trait_change(self._update_C3, 'C3', dispatch='ui')
        self.on_trait_change(self._update_C4, 'C4', dispatch='ui')
        self.on_trait_change(self._update_C5, 'C5', dispatch='ui')
        self.on_trait_change(self._update_C6, 'C6', dispatch='ui')
        # self.on_trait_change(self._update_C7, 'C7', dispatch='ui')
        self.on_trait_change(self._update_C0C1, 'C0C1', dispatch='ui')

        self._create_line_plot()
        self._create_counter()
        self.TracePlot.request_redraw()

    def _counts_to_string(self, counts):
        """Transforms a number into a String, whose format depends on the size of the number."""
        if 9.95e2 <= counts:
            string = ('%5.2f' % (counts / 1000.))[:5] + ' k'
        else:
            string = ('%5.1f' % counts)[:5]
        return string

    def _create_counter(self):
        self._counter0 = self.time_tagger.Counter(0, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter1 = self.time_tagger.Counter(1, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter2 = self.time_tagger.Counter(2, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter3 = self.time_tagger.Counter(3, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter4 = self.time_tagger.Counter(4, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter5 = self.time_tagger.Counter(5, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        self._counter6 = self.time_tagger.Counter(6, int(self.SecondsPerPoint * 1e12),
                                                  self.TraceLength)
        # self._counter7 = self.time_tagger.Counter(7, int(self.SecondsPerPoint*1e12), self.TraceLength) # ToDo: does not work when using channel 7

    def _C0_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C1_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C2_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C3_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C4_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C5_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C6_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C7_default(self):
        return numpy.zeros((self.TraceLength,))

    def _C0C1_default(self):
        return numpy.zeros((self.TraceLength,))

    def _T_default(self):
        return self.SecondsPerPoint * numpy.arange(self.TraceLength)

    def _update_T(self):
        self.TraceData.set_data('t', self.T)

    def _update_plot_title(self):
        self.TracePlot.title = self._counts_to_string(self.C0C1[-1])
        self.TotalCounts = self._counts_to_string(self.C0C1[-1])
        resize_param = int(self.TracePlot.width / 10 + self.TracePlot.height / 10)
        self.TracePlot.title_font.size = resize_param
        self.TracePlot.padding = [50, 10, resize_param, 10]
        self.TracePlot.request_redraw()

    def _update_C0(self):
        self.TraceData.set_data('y0', self.C0)
        if self.record_data:
            self.C0_list.append(self.C0[-1])
        self._update_plot_title()

    def _update_C1(self):
        self.TraceData.set_data('y1', self.C1)
        if self.record_data:
            self.C1_list.append(self.C1[-1])
        # self.TracePlot.request_redraw()

    def _update_C2(self):
        self.TraceData.set_data('y2', self.C2)
        # self.TracePlot.request_redraw()

    def _update_C3(self):
        self.TraceData.set_data('y3', self.C3)
        # self.TracePlot.request_redraw()

    def _update_C4(self):
        self.TraceData.set_data('y4', self.C4)
        # self.TracePlot.request_redraw()

    def _update_C5(self):
        self.TraceData.set_data('y5', self.C5)
        # self.TracePlot.request_redraw()

    def _update_C6(self):
        self.TraceData.set_data('y6', self.C6)
        # self.TracePlot.request_redraw()

    def _update_C7(self):
        self.TraceData.set_data('y7', self.C7)
        # self.TracePlot.request_redraw()

    def _update_C0C1(self):
        self.TraceData.set_data('y8', self.C0C1)
        if self.record_data:
            self.C0C1_list.append(self.C0C1[-1])
        # self.TracePlot.request_redraw()

    def _TraceLength_changed(self):
        self.C0 = self._C0_default()
        self.C1 = self._C1_default()
        self.C2 = self._C2_default()
        self.C3 = self._C3_default()
        self.C4 = self._C4_default()
        self.C5 = self._C5_default()
        self.C6 = self._C6_default()
        self.C7 = self._C7_default()
        self.C0C1 = self._C0C1_default()
        self.T = self._T_default()
        self._create_counter()

    def _SecondsPerPoint_changed(self):
        self.T = self._T_default()
        self._create_counter()

    def _TraceData_default(self):
        return ArrayPlotData(t=self.T, y0=self.C0, y1=self.C1, y2=self.C2, y3=self.C3, y4=self.C4,
                             y5=self.C5, y6=self.C6, y7=self.C7, y8=self.C0C1)

    def _TracePlot_default(self):
        return self._replot()

    @on_trait_change('c_enable0,c_enable1,c_enable2,c_enable3,c_enable4,c_enable5,c_enable6,sum_enable')
    def _replot(self):
        self.TracePlot = Plot(self.TraceData, resizable='hv')
        self.TracePlot.legend.align = 'll'

        n = 0
        if self.c_enable0:
            self.TracePlot.plot(('t', 'y0'), type='line', color='blue', name='C0',
                                line_width=2)
            n += 1
        if self.c_enable1:
            self.TracePlot.plot(('t', 'y1'), type='line', color='red', name='C1',
                                line_width=2)
            n += 1
        if self.c_enable2:
            self.TracePlot.plot(('t', 'y2'), type='line', color='green', name='C2',
                                line_width=2)
            n += 1
        if self.c_enable3:
            self.TracePlot.plot(('t', 'y3'), type='line', color='black', name='C3')
            n += 1
        if self.c_enable4:
            self.TracePlot.plot(('t', 'y4'), type='line', color='blue', name='C4')
            n += 1
        if self.c_enable5:
            self.TracePlot.plot(('t', 'y5'), type='line', color='red', name='C5')
            n += 1
        if self.c_enable6:
            self.TracePlot.plot(('t', 'y6'), type='line', color='green', name='C6')
            n += 1
        # if self.c_enable7:
        #    self.TracePlot.plot(('t','y7'), type='line', color='black', name='channel 7')
        if self.sum_enable:
            self.TracePlot.plot(('t', 'y8'), type='line', color='black', name='C0 + C1',
                                line_width=2)
            n += 1

        if n > 1:
            self.TracePlot.legend.visible = True
        else:
            self.TracePlot.legend.visible = False

        return self.TracePlot

    def _RecordData_default(self):
        return ArrayPlotData(T=self.time, C0=self.c0, C1=self.c1, C0C1=self.c0c1)

    def _RecordPlot_default(self):
        self.RecordPlot = Plot(self.RecordData, resizable='hv')
        self.RecordPlot.plot(('T', 'C0'), type='line', color='blue', name='C0', line_width=2)
        self.RecordPlot.plot(('T', 'C1'), type='line', color='blue', name='C1', line_width=2)
        self.RecordPlot.plot(('T', 'C0C1'), type='line', color='blue', name='C0C1', line_width=2)
        self.RecordPlot.legend.visible = True
        return self.RecordPlot

    @on_trait_change('record_data')
    def _record_data(self):
        if self.record_data:
            self.C0_list = []
            self.C1_list = []
            self.C0C1_list = []
        else:
            self.time = numpy.arange(0, len(self.C0_list))
            self.c0 = self.C0_list
            self.c1 = self.C1_list
            self.c0c1 = self.C0C1_list
            self._update_line_plot()

    def _create_line_plot(self):
        line_data = ArrayPlotData(time=numpy.ones(100), c0=numpy.ones(100),
                                  c1=numpy.ones(100), c0c1=numpy.ones(100))
        line_plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=32)
        line_plot.plot(('time', 'c0'), style='line', color='blue', name='C0')
        line_plot.plot(('time', 'c1'), style='line', color='red', name='C1')
        line_plot.plot(('time', 'c0c1'), style='line', color='black', name='C0+C1')
        line_plot.legend.visible = True

        line_plot.index_axis.title = 'Time'
        line_plot.value_axis.title = 'Fluorescence counts'
        line_label = PlotLabel(text='', hjustify='left', vjustify='bottom', position=[64, 128])
        line_plot.overlays.append(line_label)

        self.line_label = line_label
        self.line_data = line_data
        self.line_plot = line_plot

    def _update_line_plot(self):
        self.line_data.set_data('time', self.time)
        self.line_data.set_data('c0', self.c0)
        self.line_data.set_data('c1', self.c1)
        self.line_data.set_data('c0c1', self.c0c1)

    def _run(self):
        """Acquire Count Trace"""
        while True:
            threading.current_thread().stop_request.wait(self.RefreshRate)
            if threading.current_thread().stop_request.is_set():
                break

            self.C0 = self._counter0.getData() / self.SecondsPerPoint
            self.C1 = self._counter1.getData() / self.SecondsPerPoint
            self.C2 = self._counter2.getData() / self.SecondsPerPoint
            self.C3 = self._counter3.getData() / self.SecondsPerPoint
            self.C4 = self._counter4.getData() / self.SecondsPerPoint
            self.C5 = self._counter5.getData() / self.SecondsPerPoint
            self.C6 = self._counter6.getData() / self.SecondsPerPoint
            # self.C7 = self._counter7.getData() / self.SecondsPerPoint
            self.C0C1 = self.C0 + self.C1

    get_set_items = ["SecondsPerPoint", "RefreshRate", "TraceLength", 'C0_list', "C1_list", "C0C1_list"]

    traits_view = View(
        Group(
            # Group(
            #     Item("TotalCounts", style='readonly', width=100, height=100, show_label=False, springy=True, full_size=True),
            # ),
            HGroup(
                    Item('c_enable0'), Item('c_enable1'), Item('c_enable2'),
                    Item('c_enable3'), Item('c_enable4'), Item('c_enable5'),
                    Item('c_enable6'), Item('sum_enable'),
                    label="Channels",
                    show_border=True,
            ),
            Tabbed(
                VGroup(
                    Item('TracePlot', editor=ComponentEditor(), show_label=False),
                    label='Live Trace'
                ),
                VGroup(
                    Item('line_plot', width=0.1, show_label=False, resizable=True),
                    label='Recorded Trace',
                    show_border=True
                ),
            ),
            HGroup(
                Item("record_data"),
                Item('filename'),
                Item('save_button', enabled_when='record_data!=True', show_label=False),
            ),
            Item('TraceLength'),
            Item('SecondsPerPoint'),
            Item('RefreshRate'),
            show_border=True,
        ),
        title='Pi3diamond: Timetrace', width=1000, height=800, x=10, y=30, buttons=[], resizable=True,
        handler=StartThreadHandler
    )


if __name__ == '__main__':
    import logging

    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().info('Starting logger.')

    from tools.emod import JobManager

    JobManager().start()

    p = PhotonTimeTrace()
    p.edit_traits()
