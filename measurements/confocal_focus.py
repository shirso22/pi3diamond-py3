# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import logging
import threading
import time

import numpy
from chaco.api import PlotAxis, CMapImagePlot, ArrayPlotData, ColorBar, LinearMapper, DataLabel, PlotLabel
from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator
from chaco.tools.cursor_tool import CursorTool2D
from enable.api import ComponentEditor
from traits.api import (Trait, Instance, Property, Range, Bool, Array, Str, Enum, Button, on_trait_change,
                        cached_property)
from traitsui.api import Group, VSplit, HSplit, View, Item, HGroup, VGroup, EnumEditor, TextEditor

from analysis.gaussfitter import gaussfit
from tools.chaco_addons import SavePlot as Plot, SaveHPlotContainer as HPlotContainer, SaveTool, AspectZoomTool
from tools.colormaps import viridis, magma, inferno, lipari, navia
from tools.cron import CronDaemon, CronEvent
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin, GetSettableHistory as History
from tools.utility import warning


class Confocal(ManagedJob, GetSetItemsMixin):
    # overwrite default priority from ManagedJob (default 0)
    priority = 9

    resolution = Range(low=1, high=1000, value=100, desc='Number of point in long direction', label='resolution',
                       auto_set=False, enter_set=True)
    seconds_per_point = Range(low=1e-3, high=10, value=0.01, desc='Seconds per point [s]',
                              label='Seconds per point [s]', mode='text', auto_set=False, enter_set=True)
    bidirectional = Bool(True)
    return_speed = Range(low=1.0, high=100., value=10.,
                         desc='Multiplier for return speed of Scanner if mode is monodirectional', label='return speed',
                         mode='text', auto_set=False, enter_set=True)
    constant_axis = Enum('z', 'x', 'y',
                         label='constant axis',
                         desc='axis that is not scanned when acquiring an image',
                         editor=EnumEditor(values={'x': '1:x', 'y': '2:y', 'z': '3:z', }, cols=3), )

    # buttons
    history_back = Button(label='Back')
    history_forward = Button(label='Forward')
    reset_range = Button(label='reset range')
    reset_cursor = Button(label='reset position')

    # plot parameters
    thresh_high = Trait('auto', desc='High Limit of image plot',
                        editor=TextEditor(auto_set=False, enter_set=True, evaluate=float))
    thresh_low = Trait('auto', desc='Low Limit of image plot',
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=float))
    # colormap = Enum('Spectral','gray')
    show_labels = Bool(False)

    # scan data
    X = Array()
    Y = Array()
    image = Array()

    # plots
    plot_data = Instance(ArrayPlotData)
    scan_plot = Instance(CMapImagePlot)
    cursor = Instance(CursorTool2D)
    zoom = Instance(AspectZoomTool)
    figure = Instance(Plot)
    figure_container = Instance(HPlotContainer, editor=ComponentEditor())
    z_label_text = Str('z:0.0')
    cursor_position = Property(depends_on=['x', 'y', 'z', 'constant_axis'])

    get_set_items = ['constant_axis', 'X', 'Y', 'thresh_high', 'thresh_low', 'seconds_per_point',
                     'return_speed', 'bidirectional', 'history', 'image', 'z_label_text',
                     'resolution', 'x', 'x1', 'x2', 'y', 'y1', 'y2', 'z', 'z1', 'z2']

    def __init__(self, scanner, **kwargs):
        super(Confocal, self).__init__(**kwargs)
        self.imager = scanner

        # imager position
        self.add_trait('x', Range(low=scanner.get_x_range()[0], high=scanner.get_x_range()[1],
                                  value=0.5 * (scanner.get_x_range()[0] + scanner.get_x_range()[1]), desc='x [micron]',
                                  label='x [micron]', mode='slider'))
        self.add_trait('y', Range(low=scanner.get_y_range()[0], high=scanner.get_y_range()[1],
                                  value=0.5 * (scanner.get_y_range()[0] + scanner.get_y_range()[1]), desc='y [micron]',
                                  label='y [micron]', mode='slider'))
        self.add_trait('z', Range(low=scanner.get_z_range()[0], high=scanner.get_z_range()[1],
                                  value=0.5 * (scanner.get_z_range()[0] + scanner.get_z_range()[1]), desc='z [micron]',
                                  label='z [micron]', mode='slider'))

        # imagging parameters
        self.add_trait('x1',
                       Range(low=scanner.get_x_range()[0], high=scanner.get_x_range()[1],
                             value=scanner.get_x_range()[0],
                             desc='x1 [micron]', label='x1',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))
        self.add_trait('y1',
                       Range(low=scanner.get_y_range()[0], high=scanner.get_y_range()[1],
                             value=scanner.get_y_range()[0],
                             desc='y1 [micron]', label='y1',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))
        self.add_trait('z1',
                       Range(low=scanner.get_z_range()[0], high=scanner.get_z_range()[1],
                             value=scanner.get_z_range()[0],
                             desc='z1 [micron]', label='z1',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))
        self.add_trait('x2',
                       Range(low=scanner.get_x_range()[0], high=scanner.get_x_range()[1],
                             value=scanner.get_x_range()[1],
                             desc='x2 [micron]', label='x2',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))
        self.add_trait('y2',
                       Range(low=scanner.get_y_range()[0], high=scanner.get_y_range()[1],
                             value=scanner.get_y_range()[1],
                             desc='y2 [micron]', label='y2',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))
        self.add_trait('z2',
                       Range(low=scanner.get_z_range()[0], high=scanner.get_z_range()[1],
                             value=scanner.get_z_range()[1],
                             desc='z2 [micron]', label='z2',
                             editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str='%.2f')))

        self.X = numpy.linspace(scanner.get_x_range()[0], scanner.get_x_range()[-1], self.resolution + 1)
        self.Y = numpy.linspace(scanner.get_y_range()[0], scanner.get_y_range()[-1], self.resolution + 1)
        self.image = numpy.zeros((len(self.X), len(self.Y)))
        self._create_plot()
        self.figure.index_range.on_trait_change(self.update_axis_li, '_low_value', dispatch='ui')
        self.figure.index_range.on_trait_change(self.update_axis_hi, '_high_value', dispatch='ui')
        self.figure.value_range.on_trait_change(self.update_axis_lv, '_low_value', dispatch='ui')
        self.figure.value_range.on_trait_change(self.update_axis_hv, '_high_value', dispatch='ui')
        self.zoom.on_trait_change(self.check_zoom, 'box', dispatch='ui')
        self.on_trait_change(self.set_mesh_and_aspect_ratio, 'X,Y', dispatch='ui')
        self.on_trait_change(self.update_image_plot, 'image', dispatch='ui')
        self.sync_trait('cursor_position', self.cursor, 'current_position')
        self.sync_trait('thresh_high', self.scan_plot.value_range, 'high_setting')
        self.sync_trait('thresh_low', self.scan_plot.value_range, 'low_setting')
        self.on_trait_change(self.scan_plot.request_redraw, 'thresh_high', dispatch='ui')
        self.on_trait_change(self.scan_plot.request_redraw, 'thresh_low', dispatch='ui')
        self.history = History(length=20)
        self.history.put(self.copy_items(['constant_axis', 'X', 'Y', 'image', 'z_label_text', 'resolution']))
        self.labels = {}
        self.label_list = []

    # imager position

    @on_trait_change('x,y,z')
    def _set_imager_position(self):
        if self.state != 'run':
            self.imager.set_position(self.x, self.y, self.z)

    @cached_property
    def _get_cursor_position(self):
        if self.constant_axis == 'x':
            return self.z, self.y
        elif self.constant_axis == 'y':
            return self.x, self.z
        elif self.constant_axis == 'z':
            return self.x, self.y

    def _set_cursor_position(self, position):
        if self.constant_axis == 'x':
            self.z, self.y = position
        elif self.constant_axis == 'y':
            self.x, self.z = position
        elif self.constant_axis == 'z':
            self.x, self.y = position

    # image acquisition

    def _run(self):
        """Acquire a scan"""

        try:
            self.state = 'run'

            self.update_mesh()
            X = self.X
            Y = self.Y

            XP = X[::-1]

            self.image = numpy.zeros((len(Y), len(X)))

            """
            if not self.bidirectional:
                self.imager.initImageScan(len(X), len(Y), self.seconds_per_point, return_speed=self.return_speed)
            else:
                self.imager.initImageScan(len(X), len(Y), self.seconds_per_point, return_speed=None)
            """
            for i, y in enumerate(Y):
                if threading.current_thread().stop_request.is_set():
                    break
                if i % 2 != 0 and self.bidirectional:
                    XL = XP
                else:
                    XL = X
                YL = y * numpy.ones(X.shape)

                if self.constant_axis == 'x':
                    const = self.x * numpy.ones(X.shape)
                    Line = numpy.vstack((const, YL, XL))
                elif self.constant_axis == 'y':
                    const = self.y * numpy.ones(X.shape)
                    Line = numpy.vstack((XL, const, YL))
                elif self.constant_axis == 'z':
                    const = self.z * numpy.ones(X.shape)
                    Line = numpy.vstack((XL, YL, const))

                if self.bidirectional:
                    c = self.imager.scan_line(Line, self.seconds_per_point)
                else:
                    # start_time = time.time()
                    c = self.imager.scan_line(Line, self.seconds_per_point)
                    # print 'nominal time: '+str(self.seconds_per_point*Line.shape[1])
                    # print 'actual time: '+str(time.time() - start_time)
                    self.imager.scan_line(Line[:, ::-1], self.seconds_per_point / self.return_speed)
                if i % 2 != 0 and self.bidirectional:
                    self.image[i, :] = c[-1::-1]
                else:
                    self.image[i, :] = c[:]

                """
                self.imager.doImageLine(Line)
                self.image = self.imager.getImage()
                """
                self.trait_property_changed('image', self.image)

                if self.constant_axis == 'x':
                    self.z_label_text = 'x:%.2f' % self.x
                elif self.constant_axis == 'y':
                    self.z_label_text = 'y:%.2f' % self.y
                elif self.constant_axis == 'z':
                    self.z_label_text = 'z:%.2f' % self.z

            """
            # block at the end until the image is ready 
            if not threading.current_thread().stop_request.is_set(): 
                self.image = self.imager.getImage(1)
                self._image_changed()
            """

            self.imager.set_position(self.x, self.y, self.z)

            # save scan data to history
            self.history.put(self.copy_items(['constant_axis', 'X', 'Y', 'image', 'z_label_text', 'resolution']))

        finally:
            self.state = 'idle'

    # plotting

    def _create_plot(self):
        plot_data = ArrayPlotData(image=self.image)
        plot = Plot(plot_data, width=300, height=300, resizable='hv', aspect_ratio=1.0, padding=8, padding_left=32,
                    padding_bottom=32)
        plot.img_plot('image', colormap=navia, xbounds=(self.X[0], self.X[-1]), ybounds=(self.Y[0], self.Y[-1]),
                      name='image')
        image = plot.plots['image'][0]
        image.x_mapper.domain_limits = (self.imager.get_x_range()[0], self.imager.get_x_range()[1])
        image.y_mapper.domain_limits = (self.imager.get_y_range()[0], self.imager.get_y_range()[1])
        zoom = AspectZoomTool(image, enable_wheel=False)
        cursor = CursorTool2D(image, drag_button='left', color='white', marker_size=1.0, line_width=1.5)
        image.overlays.append(cursor)
        image.overlays.append(zoom)

        colormap = image.color_mapper
        colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                            color_mapper=colormap,
                            plot=plot,
                            orientation='v',
                            resizable='v',
                            width=16,
                            height=320,
                            padding=8,
                            padding_left=32)

        container = HPlotContainer()
        container.add(plot)
        container.add(colorbar)
        z_label = PlotLabel(text='z=0.0', color='red', hjustify='left', vjustify='bottom', position=[10, 10])
        container.overlays.append(z_label)
        container.tools.append(SaveTool(container))

        self.plot_data = plot_data
        self.scan_plot = image
        self.cursor = cursor
        self.zoom = zoom
        self.figure = plot
        self.figure_container = container
        self.sync_trait('z_label_text', z_label, 'text')

    def set_mesh_and_aspect_ratio(self):
        self.scan_plot.index.set_data(self.X, self.Y)
        x1 = self.X[0]
        x2 = self.X[-1]
        y1 = self.Y[0]
        y2 = self.Y[-1]

        self.figure.aspect_ratio = (x2 - x1) / float((y2 - y1))
        self.figure.index_range.low = x1
        self.figure.index_range.high = x2
        self.figure.value_range.low = y1
        self.figure.value_range.high = y2

    def check_zoom(self, box):
        li, lv, hi, hv = box
        if self.constant_axis == 'x':
            if not li < self.z < hi:
                self.z = 0.5 * (li + hi)
            if not lv < self.y < hv:
                self.y = 0.5 * (lv + hv)
        elif self.constant_axis == 'y':
            if not li < self.x < hi:
                self.x = 0.5 * (li + hi)
            if not lv < self.z < hv:
                self.z = 0.5 * (lv + hv)
        elif self.constant_axis == 'z':
            if not li < self.x < hi:
                self.x = 0.5 * (li + hi)
            if not lv < self.y < hv:
                self.y = 0.5 * (lv + hv)

    def center_cursor(self):
        i = 0.5 * (self.figure.index_range.low + self.figure.index_range.high)
        v = 0.5 * (self.figure.value_range.low + self.figure.value_range.high)
        if self.constant_axis == 'x':
            self.z = i
            self.y = v
        elif self.constant_axis == 'y':
            self.x = i
            self.z = v
        elif self.constant_axis == 'z':
            self.x = i
            self.y = v

    def _constant_axis_changed(self):
        self.update_mesh()
        self.image = numpy.zeros((len(self.X), len(self.Y)))
        self.update_axis()
        self.set_mesh_and_aspect_ratio()

    def update_image_plot(self):
        self.plot_data.set_data('image', self.image)

    """
    def _colormap_changed(self, new):
        data = self.figure.datasources['image']
        func = getattr(chaco.api,new)
        self.figure.color_mapper=func(DataRange1D(data))
        self.figure.request_redraw()
    """

    def _show_labels_changed(self, name, old, new):
        for item in self.scan_plot.overlays:
            if isinstance(item, DataLabel) and item.label_format in self.labels:
                item.visible = new
        self.scan_plot.request_redraw()

    def get_label_index(self, key):
        for index, item in enumerate(self.scan_plot.overlays):
            if isinstance(item, DataLabel) and item.label_format == key:
                return index
        return None

    def set_label(self, key, coordinates, **kwargs):

        plot = self.scan_plot

        if self.constant_axis == 'x':
            point = (coordinates[2], coordinates[1])
        elif self.constant_axis == 'y':
            point = (coordinates[0], coordinates[2])
        elif self.constant_axis == 'z':
            point = (coordinates[0], coordinates[1])

        defaults = {'component': plot,
                    'data_point': point,
                    'label_format': key,
                    'label_position': 'top right',
                    'bgcolor': 'transparent',
                    'text_color': 'white',
                    'border_visible': False,
                    'padding_bottom': 8,
                    'marker': 'cross',
                    'marker_color': 'white',
                    'marker_line_color': 'black',
                    'marker_line_width': 1,
                    'marker_size': 4,
                    'arrow_visible': False,
                    'clip_to_plot': False,
                    'visible': self.show_labels}

        defaults.update(kwargs)

        label = DataLabel(**defaults)

        index = self.get_label_index(key)
        if index is None:
            plot.overlays.append(label)
        else:
            plot.overlays[index] = label
        self.labels[key] = coordinates
        plot.request_redraw()

    def remove_label(self, key):
        plot = self.scan_plot
        index = self.get_label_index(key)
        plot.overlays.pop(index)
        plot.request_redraw()
        self.labels.pop(key)

    def remove_all_labels(self):
        plot = self.scan_plot
        new_overlays = []
        for item in plot.overlays:
            if not (isinstance(item, DataLabel) and item.label_format in self.labels):
                new_overlays.append(item)
        plot.overlays = new_overlays
        plot.request_redraw()
        self.labels.clear()

    @on_trait_change('constant_axis')
    def relocate_labels(self):
        for item in self.scan_plot.overlays:
            if isinstance(item, DataLabel) and item.label_format in self.labels:
                coordinates = self.labels[item.label_format]
                if self.constant_axis == 'x':
                    point = (coordinates[2], coordinates[1])
                elif self.constant_axis == 'y':
                    point = (coordinates[0], coordinates[2])
                elif self.constant_axis == 'z':
                    point = (coordinates[0], coordinates[1])
                item.data_point = point

    def update_axis_li(self):
        if self.constant_axis == 'x':
            self.z1 = self.figure.index_range.low
        elif self.constant_axis == 'y':
            self.x1 = self.figure.index_range.low
        elif self.constant_axis == 'z':
            self.x1 = self.figure.index_range.low

    def update_axis_hi(self):
        if self.constant_axis == 'x':
            self.z2 = self.figure.index_range.high
        elif self.constant_axis == 'y':
            self.x2 = self.figure.index_range.high
        elif self.constant_axis == 'z':
            self.x2 = self.figure.index_range.high

    def update_axis_lv(self):
        if self.constant_axis == 'x':
            self.y1 = self.figure.value_range.low
        elif self.constant_axis == 'y':
            self.z1 = self.figure.value_range.low
        elif self.constant_axis == 'z':
            self.y1 = self.figure.value_range.low

    def update_axis_hv(self):
        if self.constant_axis == 'x':
            self.y2 = self.figure.value_range.high
        elif self.constant_axis == 'y':
            self.z2 = self.figure.value_range.high
        elif self.constant_axis == 'z':
            self.y2 = self.figure.value_range.high

    def update_axis(self):
        self.update_axis_li()
        self.update_axis_hi()
        self.update_axis_lv()
        self.update_axis_hv()

    def update_mesh(self):
        if self.constant_axis == 'x':
            x1 = self.z1
            x2 = self.z2
            y1 = self.y1
            y2 = self.y2
        elif self.constant_axis == 'y':
            x1 = self.x1
            x2 = self.x2
            y1 = self.z1
            y2 = self.z2
        elif self.constant_axis == 'z':
            x1 = self.x1
            x2 = self.x2
            y1 = self.y1
            y2 = self.y2

        if (x2 - x1) >= (y2 - y1):
            self.X = numpy.linspace(x1, x2, self.resolution)
            self.Y = numpy.linspace(y1, y2, int(self.resolution * (y2 - y1) / (x2 - x1)))
        else:
            self.Y = numpy.linspace(y1, y2, self.resolution)
            self.X = numpy.linspace(x1, x2, int(self.resolution * (x2 - x1) / (y2 - y1)))

    # GUI buttons

    def _history_back_fired(self):
        self.stop()
        self.set_items(self.history.back())

    def _history_forward_fired(self):
        self.stop()
        self.set_items(self.history.forward())

    def _reset_range_fired(self):
        self.x1 = self.imager.get_x_range()[0]
        self.x2 = self.imager.get_x_range()[1]
        self.y1 = self.imager.get_y_range()[0]
        self.y2 = self.imager.get_y_range()[1]
        self.z1 = self.imager.get_z_range()[0]
        self.z2 = self.imager.get_z_range()[1]

    def _reset_cursor_fired(self):
        self.center_cursor()


    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('history_back', show_label=False),
                                     Item('history_forward', show_label=False),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Item('figure_container', show_label=False, resizable=True,
                                   enabled_when='state != "run"'
                                   ),
                              HGroup(Item('thresh_low', width=-80),
                                     Item('thresh_high', width=-80),
                                     Item('show_labels'),
                                     ),
                              HGroup(Item('resolution', enabled_when='state != "run"', width=-60),
                                     Item('x1', width=-60),
                                     Item('x2', width=-60),
                                     Item('y1', width=-60),
                                     Item('y2', width=-60),
                                     Item('z1', width=-60),
                                     Item('z2', width=-60),
                                     Item('reset_range', show_label=False),
                                     ),
                              HGroup(Item('constant_axis', style='custom', show_label=False,
                                          enabled_when='state != "run"'),
                                     Item('bidirectional', enabled_when='state != "run"'),
                                     Item('seconds_per_point', width=-80),
                                     Item('return_speed', width=-80),
                                     Item('reset_cursor', show_label=False),
                                     ),
                              Item('x', enabled_when='state != "run" or '
                                                     '(state == "run" and constant_axis == "x")'),
                              Item('y', enabled_when='state != "run" or '
                                                     '(state == "run" and constant_axis == "y")'),
                              Item('z', enabled_when='state != "run" or '
                                                     '(state == "run" and constant_axis == "z")'),
                              show_border=True,
                              label="Confocal"
                              ),
                       # title='Confocal',
                       # width=750, height=900,
                       buttons=[], resizable=True
                       )


class AutoFocus(ManagedJob, GetSetItemsMixin):
    # overwrite default priority from ManagedJob (default 0)
    priority = 9

    confocal = Instance(Confocal)

    size_xy = Range(low=0.5, high=10., value=1.2, desc='Size of XY Scan', label='Size XY [micron]', mode='slider',
                    auto_set=False, enter_set=True)
    size_z = Range(low=0.5, high=10., value=2., desc='Size of Z Scan', label='Size Z [micron]', mode='slider',
                   auto_set=False, enter_set=True)
    step_xy = Range(low=0.01, high=10., value=0.1, desc='Step of XY Scan', label='Step XY [micron]', mode='slider',
                    auto_set=False, enter_set=True)
    step_z = Range(low=0.01, high=10., value=0.01, desc='Step of Z Scan', label='Step Z [micron]', mode='slider',
                   auto_set=False, enter_set=True)
    seconds_per_point_xy = Range(low=1e-3, high=10, value=0.08, desc='Seconds per point for XY Scan',
                                 label='seconds per point XY [s]', mode='text', auto_set=False, enter_set=True)
    seconds_per_point_z = Range(low=1e-3, high=10, value=0.2, desc='Seconds per point for Z Scan',
                                label='seconds per point Z  [s]', mode='text', auto_set=False, enter_set=True)

    enable_xy = Bool(True)
    enable_z = Bool(True)

    fit_method_xy = Enum('Maximum', 'Gaussian', desc='Fit Method for XY Scan', label='XY Fit Method')
    fit_method_z = Enum('Maximum', 'Gaussian', desc='Fit Method for Z Scan', label='Z Fit Method')

    X = Array(value=numpy.array((0., 1.)))
    Y = Array(value=numpy.array((0., 1.)))
    Z = Array(value=numpy.array((-1., 1.)))

    data_xy = Array()
    data_z = Array(value=numpy.array((0, 0)))

    targets = Instance({}.__class__,
                       factory={}.__class__)  # Dict traits are no good for pickling, therefore we have to do it with an ordinary dictionary and take care about the notification manually
    target_list = Instance(list, factory=list,
                           args=([None],))  # list of targets that are selectable in current_target editor
    current_target = Enum(values='target_list')

    drift = Array(value=numpy.array(((0, 0, 0,),)))
    drift_time = Array(value=numpy.array((0,)))
    current_drift = Array(value=numpy.array((0, 0, 0)))

    focus_interval = Range(low=1, high=6000, value=10, desc='Time interval between automatic focus events',
                           label='Interval [m]', auto_set=False, enter_set=True)
    periodic_focus = Bool(False, label='Periodic focusing')

    target_name = Str(label='Name', desc='name to use when adding or removing targets')
    add_target_button = Button(label='Add Target', desc='add target with given name')
    remove_current_target_button = Button(label='Remove Current', desc='remove current target')
    remove_all_targets_button = Button(label='Remove All', desc='remove all targets')
    forget_drift_button = Button(label='Forget Drift', desc='forget the accumulated drift and reset drift plot')
    next_target_button = Button(label='Next Target', desc='switch to next available target')
    undo_button = Button(label='undo', desc='undo the movement of the stage')

    previous_state = Instance(())

    plot_data_image = Instance(ArrayPlotData)
    plot_data_line = Instance(ArrayPlotData)
    plot_data_drift = Instance(ArrayPlotData)
    figure_image = Instance(HPlotContainer, editor=ComponentEditor())
    figure_line = Instance(Plot, editor=ComponentEditor())
    figure_drift = Instance(Plot, editor=ComponentEditor())
    image_plot = Instance(CMapImagePlot)

    def __init__(self, scanner, confocal, pulse_generator, **kwargs):
        super(AutoFocus, self).__init__(**kwargs)
        self.imager = scanner
        self.confocal = confocal
        self.pulse_generator = pulse_generator
        self.on_trait_change(self.update_plot_image, 'data_xy', dispatch='ui')

        self.on_trait_change(self.update_plot_line_value, 'data_z', dispatch='ui')
        self.on_trait_change(self.update_plot_line_index, 'Z', dispatch='ui')
        self.on_trait_change(self.update_plot_drift_value, 'drift', dispatch='ui')
        self.on_trait_change(self.update_plot_drift_index, 'drift_time', dispatch='ui')

    @on_trait_change('next_target_button')
    def next_target(self):
        """Convenience method to switch to the next available target."""
        keys = list(self.targets.keys())
        key = self.current_target
        if len(keys) == 0:
            logging.getLogger().info('No target available. Add a target and try again!')
        elif not key in keys:
            self.current_target = keys[0]
        else:
            self.current_target = keys[(keys.index(self.current_target) + 1) % len(keys)]

    def _targets_changed(self, name, old, new):
        # HW-FIX: sorting a list that mixes str and None raises TypeError in
        # Python 3. It fired inside this Traits notification handler, which
        # swallows exceptions, so target_list was never rebuilt (the Current
        # Target dropdown never saw new targets) and _draw_targets() below was
        # never reached (no marker appeared). Python 2 sorted None first, which
        # is reproduced here.
        l = [None] + sorted(new.keys())  # rebuild target_list for Enum trait
        self.target_list = l
        self._draw_targets()  # redraw target labels

    def _current_target_changed(self):
        self._draw_targets()  # redraw target labels

    def _draw_targets(self):
        c = self.confocal
        c.remove_all_labels()
        c.show_labels = True
        for key, coordinates in self.targets.items():
            if key == self.current_target:
                c.set_label(key, coordinates, marker_color='red')
            else:
                c.set_label(key, coordinates)

    def check_laser_state_submit(self):
        """ Only submit an auto focus Job if the laser is on, DOESNT WORK, reverted to standard submit"""
        self.submit()

    def _periodic_focus_changed(self, new):
        if not new and hasattr(self, 'cron_event'):
            CronDaemon().remove(self.cron_event)
        if new:
            self.cron_event = CronEvent(self.check_laser_state_submit, min=list(range(0, 60, self.focus_interval)))
            CronDaemon().register(self.cron_event)

    def fit_xy(self):
        if self.fit_method_xy == 'Maximum':
            index = self.data_xy.argmax()
            xp = self.X[index % len(self.X)]
            # HW-FIX: `/` is a float in Python 3 and a float cannot index a
            # sequence. This is a row number, so it needs floor division.
            yp = self.Y[index // len(self.X)]
        elif self.fit_method_xy == 'Gaussian':
            c, a, center_x, center_y, width_x, width_y = gaussfit(self.data_xy, circ=1, rotate=0)
            # linear interpolation between the pixels
            # HW-FIX: numpy.floor/ceil return floats, which cannot index an
            # array. int() keeps the interpolation below unchanged.
            i0 = int(numpy.floor(center_x))
            i1 = int(numpy.ceil(center_x))
            x0 = self.X[i0]
            x1 = self.X[i1]
            xp = x0 + (center_x - i0) * (x1 - x0)
            i0 = int(numpy.floor(center_y))
            i1 = int(numpy.ceil(center_y))
            y0 = self.Y[i0]
            y1 = self.Y[i1]
            yp = y0 + (center_y - i0) * (y1 - y0)
        else:
            print('Not Implemented! Fix Me!')
        self.XYFitParameters = [xp, yp]
        self.xfit = xp
        self.yfit = yp
        return xp, yp

    def fit_z(self):
        if self.fit_method_z == 'Maximum':
            zp = self.Z[self.data_z.argmax()]
            self.zfit = zp
            return zp
        else:
            print('Not Implemented! Fix Me!')

    def add_target(self, key, coordinates=None):
        if coordinates is None:
            c = self.confocal
            coordinates = numpy.array((c.x, c.y, c.z))
        if self.targets == {}:
            self.forget_drift()
        if key in self.targets:
            if warning(
                    'A target with this name already exists.\nOverwriting will move all targets.\nDo you want to continue?'):
                self.current_drift = coordinates - self.targets[key]
                self.forget_drift()
            else:
                return
        else:
            coordinates = coordinates - self.current_drift
            self.targets[key] = coordinates
        # HW-FIX: the dict above was mutated IN PLACE, so old and new are the
        # same object. Traits 7 compares them, finds no change and drops the
        # notification entirely -- _targets_changed never runs, so the Enum is
        # never rebuilt and no marker is drawn. Passing a distinct old value
        # makes the notification fire. (Array traits are unaffected, which is
        # why the image and counts updates elsewhere still work.)
        self.trait_property_changed('targets', None,
                                    self.targets)  # trigger event such that Enum is updated and Labels are redrawn
        self.confocal.show_labels = True

    def remove_target(self, key):
        if not key in self.targets:
            logging.getLogger().info('Target cannot be removed. Target does not exist.')
            return
        self.targets.pop(key)  # remove target from dictionary
        # HW-FIX: the dict above was mutated IN PLACE, so old and new are the
        # same object. Traits 7 compares them, finds no change and drops the
        # notification entirely -- _targets_changed never runs, so the Enum is
        # never rebuilt and no marker is drawn. Passing a distinct old value
        # makes the notification fire. (Array traits are unaffected, which is
        # why the image and counts updates elsewhere still work.)
        self.trait_property_changed('targets', None,
                                    self.targets)  # trigger event such that Enum is updated and Labels are redrawn

    def remove_all_targets(self):
        self.targets = {}

    def forget_drift(self):
        targets = self.targets
        # reset coordinates of all targets according to current drift
        for key in targets:
            targets[key] += self.current_drift
        # trigger event such that target labels are redrawn
        # HW-FIX: in-place mutation -- see add_target(). Traits 7 drops a
        # notification whose old and new values are the same object.
        self.trait_property_changed('targets', None, self.targets)
        # set current_drift to 0 and clear plot
        self.current_drift = numpy.array((0., 0., 0.))
        self.drift_time = numpy.array((time.time(),))
        self.drift = numpy.array(((0, 0, 0),))

    def _add_target_button_fired(self):
        self.add_target(self.target_name)

    def _remove_current_target_button_fired(self):
        self.remove_target(self.current_target)

    def _remove_all_targets_button_fired(self):
        if warning('Remove all targets. Are you sure?'):
            self.remove_all_targets()

    def _forget_drift_button_fired(self):
        if warning('Forget accumulated drift. Are you sure?'):
            self.forget_drift()

    def _run(self):

        logging.getLogger().debug("trying run.")

        try:
            self.state = 'run'
            if self.current_target is None:
                self.focus()
            else:  # focus target
                coordinates = self.targets[self.current_target]
                confocal = self.confocal
                confocal.x, confocal.y, confocal.z = coordinates + self.current_drift
                current_coordinates = self.focus()
                self.current_drift = current_coordinates - coordinates
                self.drift = numpy.append(self.drift, (self.current_drift,), axis=0)
                self.drift_time = numpy.append(self.drift_time, time.time())
                logging.getLogger().debug('Drift: %.2f, %.2f, %.2f' % tuple(self.current_drift))
        finally:
            self.state = 'idle'

    def focus_xy(self):
        safety = 0
        imager = self.imager

        xp = self.confocal.x
        yp = self.confocal.y
        zp = self.confocal.z

        xmin = numpy.clip(xp - 0.5 * self.size_xy, imager.get_x_range()[0] + safety, imager.get_x_range()[1] - safety)
        xmax = numpy.clip(xp + 0.5 * self.size_xy, imager.get_x_range()[0] + safety, imager.get_x_range()[1] - safety)
        ymin = numpy.clip(yp - 0.5 * self.size_xy, imager.get_y_range()[0] + safety, imager.get_y_range()[1] - safety)
        ymax = numpy.clip(yp + 0.5 * self.size_xy, imager.get_y_range()[0] + safety, imager.get_y_range()[1] - safety)
        X = numpy.arange(xmin, xmax, self.step_xy)
        Y = numpy.arange(ymin, ymax, self.step_xy)
        ZL = zp * numpy.ones(X.shape)

        self.X = X
        self.Y = Y

        XP = X[::-1]

        self.data_xy = numpy.zeros((len(Y), len(X)))
        # self.image_plot.index.set_data(X, Y)

        for i, y in enumerate(Y):
            if threading.current_thread().stop_request.is_set():
                break
            if i % 2 != 0:
                XL = XP
            else:
                XL = X
            YL = y * numpy.ones(X.shape)
            Line = numpy.vstack((XL, YL, ZL))

            c = imager.scan_line(Line, self.seconds_per_point_xy)  # changed scanLine to scan_line
            if i % 2 == 0:
                self.data_xy[i, :] = c[:]
            else:
                self.data_xy[i, :] = c[-1::-1]

            self.trait_property_changed('data_xy', self.data_xy)
        else:
            xp, yp = self.fit_xy()

        self.confocal.x = xp
        self.confocal.y = yp

        logging.getLogger().info('Focus x,y: %.2f, %.2f' % (xp, yp))

    def focus_z(self):

        safety = 0
        imager = self.imager

        xp = self.confocal.x
        yp = self.confocal.y
        zp = self.confocal.z

        Z = numpy.hstack((numpy.arange(zp, zp - 0.5 * self.size_z, -self.step_z),
                          numpy.arange(zp - 0.5 * self.size_z, zp + 0.5 * self.size_z, self.step_z),
                          numpy.arange(zp + 0.5 * self.size_z, zp, -self.step_z)))
        Z = numpy.clip(Z, imager.get_z_range()[0] + safety, imager.get_z_range()[1] - safety)

        X = xp * numpy.ones(Z.shape)
        Y = yp * numpy.ones(Z.shape)

        if not threading.current_thread().stop_request.is_set():
            Line = numpy.vstack((X, Y, Z))
            data_z = imager.scan_line(Line, self.seconds_per_point_z)  # changed scanLine to scan_line

            self.Z = Z
            self.data_z = data_z

            zp = self.fit_z()

        self.confocal.z = zp

        logging.getLogger().info('Focus z: %.2f' % zp)

    def focus(self):
        """
        Focuses around current position in x, y, and z-direction.
        """

        self.previous_state = ((self.confocal.x,
                                self.confocal.y,
                                self.confocal.z), self.current_target)

        if self.enable_xy:
            self.focus_xy()

        if self.enable_z:
            self.focus_z()

        return self.confocal.x, self.confocal.y, self.confocal.z

    def undo(self):
        if self.previous_state is not None:
            coordinates, target = self.previous_state
            self.confocal.x, self.confocal.y, self.confocal.z = coordinates
            if target is not None:
                self.drift_time = numpy.delete(self.drift_time, -1)
                self.current_drift = self.drift[-2]
                self.drift = numpy.delete(self.drift, -1, axis=0)
            self.previous_state = None
        else:
            logging.getLogger().info('Can undo only once.')

    def _undo_button_fired(self):
        self.remove()
        self.undo()

    def _plot_data_image_default(self):
        return ArrayPlotData(image=numpy.zeros((2, 2)))

    def _plot_data_line_default(self):
        return ArrayPlotData(x=self.Z, y=self.data_z)

    def _plot_data_drift_default(self):
        return ArrayPlotData(t=self.drift_time, x=self.drift[:, 0], y=self.drift[:, 1], z=self.drift[:, 2])

    def _figure_image_default(self):
        plot = Plot(self.plot_data_image, resizable='hv', aspect_ratio=1.0, padding=8,
                    padding_left=32,
                    padding_bottom=32)
        plot.img_plot('image', colormap=lipari, name='image')
        plot.aspect_ratio = 1
        plot.index_mapper.domain_limits = (self.imager.get_x_range()[0], self.imager.get_x_range()[1])
        plot.value_mapper.domain_limits = (self.imager.get_y_range()[0], self.imager.get_y_range()[1])
        # container = HPlotContainer()
        image = plot.plots['image'][0]
        colormap = image.color_mapper
        colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                            color_mapper=colormap,
                            plot=plot,
                            orientation='v',
                            resizable='v',
                            width=16,
                            # height=320,
                            padding=10, )
        # padding_left=32)
        container = HPlotContainer()
        container.add(plot)
        container.add(colorbar)
        container.tools.append(SaveTool(container))
        return container

    def _figure_line_default(self):
        plot = Plot(self.plot_data_line, width=100, height=100, padding=8, padding_left=64, padding_bottom=32)
        plot.plot(('x', 'y'), color='blue')
        plot.index_axis.title = 'z [micron]'
        plot.value_axis.title = 'PL (cps)'
        plot.tools.append(SaveTool(plot))
        return plot

    def _figure_drift_default(self):
        plot = Plot(self.plot_data_drift, width=100, height=100, padding=8, padding_left=64, padding_bottom=32)
        plot.plot(('t', 'x'), type='line', color='blue', name='x')
        plot.plot(('t', 'y'), type='line', color='red', name='y')
        plot.plot(('t', 'z'), type='line', color='green', name='z')
        bottom_axis = PlotAxis(plot,
                               orientation="bottom",
                               tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        plot.index_axis = bottom_axis
        plot.index_axis.title = 'Time'
        plot.value_axis.title = 'Drift [micron]'
        plot.legend.visible = True
        plot.tools.append(SaveTool(plot))
        return plot

    def _image_plot_default(self):
        return self.figure_image.components[0].plots['image'][0]

    def update_plot_image(self):
        self.plot_data_image.set_data('image', self.data_xy)

    def update_plot_line_value(self):
        self.plot_data_line.set_data('y', self.data_z)

    def update_plot_line_index(self):
        self.plot_data_line.set_data('x', self.Z)

    def update_plot_drift_value(self):
        if len(self.drift) == 1:
            self.plot_data_drift.set_data('x', numpy.array(()))
            self.plot_data_drift.set_data('y', numpy.array(()))
            self.plot_data_drift.set_data('z', numpy.array(()))
        else:
            self.plot_data_drift.set_data('x', self.drift[:, 0])
            self.plot_data_drift.set_data('y', self.drift[:, 1])
            self.plot_data_drift.set_data('z', self.drift[:, 2])

    def update_plot_drift_index(self):
        if len(self.drift_time) == 0:
            self.plot_data_drift.set_data('t', numpy.array(()))
        else:
            self.plot_data_drift.set_data('t', self.drift_time - self.drift_time[0])

    traits_view = View(
        Group(
            HGroup(
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('priority'),
                Item('state', style='readonly'),
                Item('undo_button', show_label=False),
            ),
            HGroup(
                Item('filename', springy=True),
                Item('save_button', show_label=False),
                Item('load_button', show_label=False)
            ),
            Group(
                VGroup(
                    HGroup(
                        Item('target_name'),
                        Item('add_target_button', show_label=False),
                        Item('remove_all_targets_button', show_label=False),
                        Item('forget_drift_button', show_label=False),
                    ),
                    HGroup(
                        Item('current_target'),
                        Item('next_target_button', show_label=False),
                        Item('remove_current_target_button', show_label=False),
                    ),
                    HSplit(
                        Group(
                            Item('periodic_focus'),
                            Item('focus_interval', enabled_when='not periodic_focus'),
                        ),
                        Group(
                            Item('enable_xy'),
                            Item('enable_z'),
                        ),
                    ),
                    label='Tracking',
                ),
                VSplit(
                    HSplit(
                        Group(
                            Item('seconds_per_point_xy'),
                            Item('seconds_per_point_z'),
                        ),
                        Group(
                            Item('fit_method_xy'),
                            Item('fit_method_z'),
                        ),
                    ),
                    Group(
                        Item('size_xy'),
                        Item('step_xy'),
                        Item('size_z'),
                        Item('step_z'),
                    ),
                    label='Settings',
                ),
                layout='tabbed'
            ),
            Group(
                Item('figure_image', show_label=False, resizable=True),
                Item('figure_line', show_label=False, resizable=True),
                Item('figure_drift', show_label=False, resizable=True),
            ),
            show_border=True,
            label="Auto Focus",
        ),
    )

    get_set_items = ['confocal', 'targets', 'current_target', 'current_drift', 'drift', 'drift_time', 'periodic_focus',
                     'size_xy', 'size_z', 'step_xy', 'step_z', 'seconds_per_point_xy', 'seconds_per_point_z',
                     'enable_xy', 'enable_z', 'fit_method_xy', 'fit_method_z',
                     'data_xy', 'data_z', 'X', 'Y', 'Z', 'focus_interval']
    get_set_order = ['confocal', 'targets']


class ConfocalFocus(Confocal, AutoFocus):
    confocal = Instance(Confocal)
    auto_focus = Instance(AutoFocus)

    def __init__(self, scanner, pulse_generator, **kwargs):
        # Calling the base class inits explicitly does not appear to work
        # Confocal.__init__(self, scanner, **kwargs)
        # AutoFocus.__init__(self, scanner, confocal, pulse_generator,  **kwargs)

        self.confocal = Confocal(scanner)
        self.auto_focus = AutoFocus(scanner, self.confocal, pulse_generator)

        try:
            if scanner.setup == 'rt':
                self.auto_focus.load('defaults/auto_focus_rt.pys')
            elif scanner.setup == 'cryo':
                self.auto_focus.load('defaults/auto_focus_cryo.pys')
        except IOError:
            pass


        self.confocal.X = numpy.linspace(
            scanner.get_x_range()[0],
            scanner.get_x_range()[1],
            self.confocal.resolution + 1
        )
        self.confocal.Y = numpy.linspace(
            scanner.get_y_range()[0],
            scanner.get_y_range()[1],
            self.confocal.resolution + 1
        )

        if self.confocal.constant_axis == 'x':
            self.confocal.z_label_text = 'x:%.2f' % self.confocal.x
        elif self.confocal.constant_axis == 'y':
            self.confocal.z_label_text = 'y:%.2f' % self.confocal.y
        elif self.confocal.constant_axis == 'z':
            self.confocal.z_label_text = 'z:%.2f' % self.confocal.z

        self.confocal.set_mesh_and_aspect_ratio()

    traits_view = View(
        HSplit(
            Item("confocal", style="custom", show_label=False),
            Item("auto_focus", style="custom", show_label=False),
        ),
        title='Pi3diamond: Confocal Focus',
        width=600, height=700,
        buttons=[],
        resizable=True,
    )
