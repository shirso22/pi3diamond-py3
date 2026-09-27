# PY3-PORT: pickle.load(..., encoding='latin1') throughout this file.
# Python 2 pickled `str` as bytes; without an explicit codec every string
# in a historical .pys file comes back as bytes, or raises
# UnicodeDecodeError. latin-1 round-trips bytes 0-255 one-to-one, so numpy
# arrays and ASCII dict keys both survive. No-op for Python 3 pickles.
"""
This pulsed AFM code is an adaption of Thomas Haeberle's code for non-traits pi3diamond
to a more recent pi3diamond version based on enthought traits.
Most of the original code is intact, some has been replaced or commented out.

Authors: Thomas Haeberle (original version), Andreas Brunner, Lukas Schlipf, Amit Finkler
Changelog:
20-01-2016: Regrouping the display items; this extends the space for MW sequence list display
21-07-2016: Modifying Andreas's version to the Nanonis MPI-FKF one.
"""

import math
import os
import pickle
import sys
import threading
import time

import matplotlib
import numpy as np
import pylab
import wx
from pyface.api import FileDialog, OK
from traits.api import HasTraits, Instance, Float, String, Int, Bool, List, Button
from traitsui.api import Group, VGroup, NoButtons, Handler
from traitsui.api import View, Item, HGroup, TextEditor
from traitsui.editors import ListEditor
from traitsui.editors.check_list_editor import CheckListEditor  # , ListEditor
from traitsui.menu import OKButton, CancelButton
# PY3-PORT: moved out of the wx backend in TraitsUI 5.
from traitsui.basic_editor_factory import BasicEditorFactory
# PY3-PORT: moved out of the wx backend in TraitsUI 5.
from traitsui.editor import Editor
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvasAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
# We want matplotlib to use a wxPython backend
# matplotlib.use('WXAgg') # commented out as a test,
# this might be the one that creates the warning measurement, that it doesn't have any effect
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnchoredOffsetbox
from scipy import ndimage

from hardware.nanonis_lv_interface.nanonis import Nanonis
# from Pulsed import CalculatePulses as CalculatePulses
from measurements.pulsed import Pulsed, find_detection_pulses

if 'global_vars' in globals():
    pass  # a globally accessible variable (/object) called global_vars exists. We will use that
else:
    import global_vars

pin_switch_wait = 50  # delay time to make sure pin switches do not overlap between successive pulses
laser_prewait = 300  # delay time before laser pulses to make sure that the laser does not flash into the MW sequence


# CurrentMeasurement = None
# data = np.zeros((2, 2, 2)) # Needed to make them available globally?


class Generic_AFM_Pulsed(Pulsed):
    """ Defines a generic AFM measurement and contains its parameters.
        This merges the 'Experiment' and 'Generic_AFM_Pulsed' to match the
        style measurements are defined in the traits pi3diamond.
    """
    # global spin_state # spin state calculation from pulsed - to be overwritten
    title = 'Generic Pulsed AFM'
    # class Experiment(HasTraits):
    """ Object that contains the parameters that control the experiment,
    modified by the user.
    """
    DualPass = Bool(False)  # is the dualpass mode activated or not?
    frequency, power = [Float(2.87e9), Float(-20.0)]
    RFfreq, RFpower = [Float(250e6), Float(-20.0)]
    use_globals = Bool(True, desc='Use globals for frequency and power.', label='use globals')

    tau = Int(400)
    mwList = List(String, value=["[(['mw'], t_pi2), ([], tau), (['mw'], t_pi), ([], tau),(['mw'], t_pi2)]",
                                 "[(['mw'], t_pi2), ([   ], tau), (['mw'], t_pi), ([   ], tau), (['mw'], t_3pi2)]",
                                 "[(['mw'], t_pi2), ([   ], 200), (['mw'], t_pi), ([   ], 200), (['mw'], t_pi2)]",
                                 "[(['mw'], t_pi2), ([   ], 200), (['mw'], t_pi), ([   ], 200), (['mw'], t_3pi2)]"])

    x, y = [Int(128, label="X", desc="Pixels in X direction"), Int(128, label="Y", desc="Pixels in Y direction")]
    pixelsize = Float(0.0, desc="Size of Pixels [m]")

    # binwidth = Int(10) # use bin_width defined in 'Pulsed'
    # AcqTime = Int(1000) # use record_length defined in 'Pulsed'
    LaserOn, LaserWait = [Int(3000), Int(1200)]
    win_low, win_high = [Int(590), Int(790)]
    ref_low, ref_high = [Int(1500), Int(1700)]
    t_pi2, t_pi, t_3pi2 = [Float(0), Float(0), Float(0)]
    t_pi2_y, t_pi_y, t_3pi2_y = [Float(0), Float(0), Float(0)]

    add_button = Button("Add", tooltip="Appends the currently chosen sequence to the sequence list")
    delete_all_button = Button("Remove all", tooltip="Delete all sequences from the sequence list")
    sequences_keys = List(['Gopi_Fringe'])
    sequences = {'Gopi_Fringe': ["[(['mw'], t_pi), ([   ], tau)]"],
                 'FID': ["[(['mw'], t_pi2), ([   ], tau), (['mw'], t_pi2)]",
                         "[(['mw'], t_pi2), ([   ], tau), (['mw'], t_3pi2)]"],
                 'Hahn': ["[(['mw'], t_pi2), ([   ], tau), (['mw'], t_pi), ([   ], tau), (['mw'], t_pi2)]",
                          "[(['mw'], t_pi2), ([   ], tau), (['mw'], t_pi), ([   ], tau), (['mw'], t_3pi2)]",
                          "[(['mw'], t_pi2), ([   ], 200), (['mw'], t_pi), ([   ], 200), (['mw'], t_pi2)]",
                          "[(['mw'], t_pi2), ([   ], 200), (['mw'], t_pi), ([   ], 200), (['mw'], t_3pi2)]"],
                 'AWG-Gopi': ["[(['mw','rf'], tau), ([   ], 150)]"],
                 'T1-Pi_End': ["[([   ], tau), ([], t_pi), ([], 100)]", "[([   ], tau), (['mw'], t_pi), ([], 100)]",
                               "[([   ], 200), ([], t_pi), ([], 100)]", "[([   ], 200), (['mw'], t_pi), ([], 100)]"],
                 'T1-Pi_End_AWG': ["[([   ], tau), ([], 1000), ([], 100)]",
                                   "[([   ], tau), (['mw','rf'], 1000), ([], 100)]",
                                   "[([   ], 200), ([], 1000), ([], 100)]",
                                   "[([   ], 200), (['mw','rf'], 1000), ([], 100)]"],
                 }
    sync_with = List(['Attocube', 'Confocal'])

    def __init__(self, pulse_generator, time_tagger, microwave):
        Pulsed.__init__(self, pulse_generator, time_tagger)
        self.priority = 9
        self.AFM = True
        N_interleaved = self.mwList.__len__()  # number of interleaved sequences

        self.rf_freq = np.array((self.RFfreq,)).flatten()
        self.rf_power = self.RFpower
        self.Matrixz2d = np.zeros((len(self.rf_freq), N_interleaved))
        self.microwave = microwave

    def _add_button_fired(self):
        for element in self.sequences[self.sequences_keys[0]]:
            self.mwList.append(element)

    def _delete_all_button_fired(self):
        self.mwList = []

    def generate_sequence(self):
        """Generate sequence for generic measurement. I.e: wrap mwsequence with appropriate laser pulses. Substitutes 'Sequence()' from TH's code."""
        if self.use_globals:
            self.t_pi2, self.t_pi, self.t_3pi2 = [global_vars.mw_x_t_pi2, global_vars.mw_x_t_pi,
                                                  global_vars.mw_x_t_3pi2]
            self.t_pi2_y, self.t_pi_y, self.t_3pi2_y = [global_vars.mw_y_t_pi2, global_vars.mw_y_t_pi,
                                                        global_vars.mw_y_t_3pi2]
            self.ref_low, self.ref_high, self.win_low, self.win_high = int(global_vars.ref_low), int(
                global_vars.ref_high), int(global_vars.win_low), int(global_vars.win_high)
        t_pi2, t_pi, t_3pi2 = [self.t_pi2, self.t_pi, self.t_3pi2]
        t_pi2_y, t_pi_y, t_3pi2_y = [self.t_pi2_y, self.t_pi_y, self.t_3pi2_y]

        tau = self.tau  # to make the eval(str('tau')) work

        sequence = []

        for element in self.mwList:
            sequence.append(([], self.LaserWait))
            for pulse in eval(str(element)):
                sequence.append(pulse)
            sequence.append(([], laser_prewait))
            sequence.append((['aom', 'detect'], self.LaserOn))
        sequence.append(([], 200))
        sequence.append((['sequence'], 200))

        return sequence

    def apply_parameters(self):  # from Pulsed
        """Apply the current parameters and decide whether to keep previous data."""
        n_bins = int(self.record_length / self.bin_width)
        time_bins = self.bin_width * np.arange(n_bins)
        sequence = self.generate_sequence()
        n_laser = find_detection_pulses(sequence)

        if self.keep_data and sequence == self.sequence and np.all(
                time_bins == self.time_bins):  # if the sequence and time_bins are the same as previous, keep existing data
            self.old_count_data = self.count_data.copy()
        else:
            self.old_count_data = np.zeros((n_laser, n_bins))
            self.run_time = 0.0

        self.sequence = sequence
        self.time_bins = time_bins
        self.n_bins = n_bins
        self.n_laser = n_laser
        self.keep_data = False  # True # when job manager stops and starts the job, data should be kept. Only new submission should clear data.   

    def start_up(self):
        """Prepare MW and laser. Taken from Rabi."""
        self.pulse_generator.Night()
        if self.use_globals:
            self.power, self.frequency = global_vars.mw_power, global_vars.mw_frequency
        self.microwave.setOutput(self.power, self.frequency)

    def shut_down(self):
        """Shut down MW and laser. Taken from Rabi."""
        self.pulse_generator.Light()
        self.microwave.setOutput(None, self.frequency)

    traits_view = View(
        VGroup(HGroup(  # Item('submit_button',   show_label=False),
            # Item('remove_button',   show_label=False),
            # Item('resubmit_button', show_label=False),
            Item('priority', width=-40),
            Item('state', style='readonly'),
            Item('run_time', style='readonly', format_str='%.f'),
            # Item('stop_time', format_str='%.f'),
            # Item('stop_counts'),
        ),
            HGroup(Item('filename', springy=True),
                   Item('save_button', show_label=False),
                   Item('load_button', show_label=False)
                   ),
            HGroup(Item('bin_width', width=-80, enabled_when='state != "run"'),
                   Item('record_length', width=-80, enabled_when='state != "run"'),
                   ),
            Item('x', tooltip="Pixels in X direction", enabled_when='state != "run"'),
            Item('y', tooltip="Pixels in Y direction", enabled_when='state != "run"'),
            Item('DualPass', enabled_when='state != "run"'),
            Item('sync_with', show_label=True, editor=CheckListEditor(values=["Attocube", "Confocal"]),
                 style='simple', label='Sync with '),
            label='Basics'),
        Group(
            HGroup(Item('tau', width=-100, enabled_when='state != "run"')),
            VGroup(
                HGroup(
                    Item('sequences_keys', show_label=False, editor=CheckListEditor(values=list(sequences.keys())),
                         style='simple', label='Sequences'),
                    Item('add_button', show_label=False, style='custom',
                         tooltip="Adds the chosen sequence to the mw_list", enabled_when='state != "run"'),
                    Item('delete_all_button', show_label=False, style='custom', enabled_when='state != "run"'),
                ),
                Item('mwList', editor=ListEditor(rows=10), enabled_when='state != "run"'),
                scrollable=True),
            label='Sequence'  # , scrollable=True
        ),
        Group(
            HGroup(Item('use_globals', style='custom')),
            HGroup(
                Group(
                    Item('frequency', label='MW Freq', editor=TextEditor(format_str='%.4e', evaluate=float),
                         enabled_when='state != "run" and not use_globals'),
                    Item('power', label='MW Power', enabled_when='state != "run" and not use_globals'),
                ),
                Group(
                    Item('RFfreq', label='RF Freq', editor=TextEditor(format_str='%.4e', evaluate=float),
                         enabled_when='state != "run"'),
                    Item('RFpower', label='RF Power', enabled_when='state != "run"'),
                ),
            ),
            HGroup(
                Group(
                    Item('t_pi2', label='t_pi2', enabled_when='state != "run" and not use_globals'),
                    Item('t_pi', label='t_pi', enabled_when='state != "run" and not use_globals'),
                    Item('t_3pi2', label='t_3pi2', enabled_when='state != "run" and not use_globals'),
                ),
                Group(
                    Item('t_pi2_y', label='t_pi2_y', enabled_when='state != "run" and not use_globals'),
                    Item('t_pi_y', label='t_pi_y', enabled_when='state != "run" and not use_globals'),
                    Item('t_3pi2_y', label='t_3pi2_y', enabled_when='state != "run" and not use_globals'),
                ),
            ),
            Item('bin_width', width=-100, enabled_when='state != "run"'),
            Item('record_length', width=-100, enabled_when='state != "run"'),
            Item('LaserOn', width=-100, enabled_when='state != "run"'),
            Item('LaserWait', width=-100, enabled_when='state != "run"'),
            Group(
                Item('win_low', width=-100, label='low', enabled_when='state != "run" and not use_globals'),
                Item('win_high', width=-100, label='high', enabled_when='state != "run" and not use_globals'),
                label='AcqWindow',
                show_border=True,
            ),
            Group(
                Item('ref_low', label='low', enabled_when='state != "run"'),
                Item('ref_high', label='high', enabled_when='state != "run"'),
                label='RefWindow',
                show_border=True,
            ),
            label='MW and acquisition', springy=True
        ),
        kind='live',
    )


class _MPLFigureEditor(Editor):
    scrollable = True

    def init(self, parent):
        self.control = self._create_canvas(parent)
        self.set_tooltip()

    def update_editor(self):
        pass

    def _create_canvas(self, parent):
        """ Create the MPL canvas. """
        # The panel lets us add additional controls.
        panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        # matplotlib commands to create a canvas
        mpl_control = FigureCanvas(panel, -1, self.value)
        sizer.Add(mpl_control, 1, wx.LEFT | wx.TOP | wx.GROW)
        toolbar = NavigationToolbar2Wx(mpl_control)
        sizer.Add(toolbar, 0, wx.EXPAND)
        self.value.canvas.SetMinSize((10, 10))
        return panel


class MPLFigureEditor(BasicEditorFactory):
    klass = _MPLFigureEditor


class AnchoredScaleBar(AnchoredOffsetbox):
    # -*- coding: utf-8 -*-
    # -*- mode: python -*-
    # Adapted from mpl_toolkits.axes_grid2
    # LICENSE: Python Software Foundation (http://docs.python.org/license.html)
    def __init__(self, transform, sizex=0, sizey=0, labelx=None, labely=None, loc=4, pad=0.3, borderpad=0.3, sep=2,
                 font_size=None, prop=None, thickness=1, **kwargs):
        """
        Draw a horizontal and/or vertical bar with the size in data coordinate
        of the give axes. A label will be drawn underneath (center-aligned).
         
        - transform : the coordinate frame (typically axes.transData)
        - sizex,sizey : width of x,y bar, in data units. 0 to omit
        - labelx,labely : labels for x,y bars; None to omit
        - loc : position in containing axes
        - pad, borderpad : padding, in fraction of the legend font size (or prop)
        - sep : separation between labels and bars in points.
        - **kwargs : additional arguments passed to base class constructor
        """
        from matplotlib.patches import Rectangle
        from matplotlib.offsetbox import AuxTransformBox, VPacker, HPacker, TextArea
        bars = AuxTransformBox(transform)
        if sizex:
            bars.add_artist(Rectangle((0, 0), sizex, thickness, ec="white", fc="white", fill=True))
        if sizey:
            bars.add_artist(Rectangle((0, 0), 0, sizey, fc="none"))

        if sizex and labelx:
            bars = VPacker(children=[bars, TextArea(labelx, textprops=dict(color="white", size=font_size),
                                                    minimumdescent=False)], align="center", pad=0, sep=sep)
        if sizey and labely:
            bars = HPacker(children=[TextArea(labely), bars], align="center", pad=0, sep=sep)

        AnchoredOffsetbox.__init__(self, loc, pad=pad, borderpad=borderpad, child=bars,
                                   prop=prop, frameon=False, **kwargs)


class Image_properties(HasTraits):
    cmaplist = sorted(m for m in pylab.cm.datad if not m.endswith("_r"))
    colormap = List('afmhot')
    ticknumber = Int(7)
    scale_bar = Bool(False)
    scale_bar_length = Int(100, desc="length of scalebar in nm")
    thickness = Float(1.0, desc="thickness of scalebar in pixels")
    scale_bar_position_list = ['lower_left', 'lower_right', 'upper_left', 'upper_right']
    scale_bar_position = List('lower_right')
    padding = Float(1.20, desc='padding around bar and text')
    hide_axes = Bool(False)
    interpolationlist = ['none', 'nearest', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming',
                         'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos']
    interpolationmethod = List('nearest')
    colorbar = Bool(False)

    view = View(Group(Item('colormap', editor=CheckListEditor(values=cmaplist), style='simple', label='Colormap'),
                      # Item('ticknumber', label = 'Number of Ticks'),
                      Item('scale_bar'),
                      Item('scale_bar_length', label='Length of Scale-Bar'),
                      Item('thickness', label='thickness of scalebar in pixels'),
                      Item('scale_bar_position', editor=CheckListEditor(values=scale_bar_position_list), style='simple',
                           label='scale bar position'),
                      Item('padding', label='padding around bar and text'),
                      Item('hide_axes'),
                      Item('interpolationmethod', editor=CheckListEditor(values=interpolationlist), style='simple',
                           label='Interpolation method'),
                      # Item('colorbar'),
                      ),
                buttons=[OKButton, CancelButton],
                )


class Postprocessing(HasTraits):
    """ Postprocessing and display of the acquired data.
    """
    npulses = Int(0, label="Number of Pulses: 0 ")
    process = String('0', label="Process",
                     desc="Type in which Pulses should be added up or substracted. E.g. (0-1)/(2*3+4)")
    lower_bound = Float(0, label="Lower Bound")
    upper_bound = Float(1, label="Upper Bound")
    auto_bound = Bool(True)

    low_pass = Bool(False)
    lowpass_order = Int(1)

    file_dir = String("")
    file_name = String("")
    file_increment = Int(0)

    view = View(Group(HGroup(Item('npulses', style='readonly'),
                             Item('process',
                                  tooltip="Type in which Pulses should be added up or substracted.E.g. (0-1)/(2*3+4)\n The even numbers correspond to the detection window, the odd ones to the reference window.",
                                  width=-300),
                             ),
                      HGroup(Item('lower_bound', width=-60),
                             Item('upper_bound', width=-60),
                             Item('auto_bound'),
                             ),
                      HGroup(Item('low_pass'),
                             Item('lowpass_order',
                                  tooltip="An order of 0 corresponds to convolution with a Gaussion kernel. 1,2 or 3 correspond to convolution with the first, second or third derivatives of a Gaussian. No higher derivatives are implemented.",
                                  width=-90),
                             ),
                      HGroup(Item('file_dir', width=-300),
                             Item('file_increment', width=-60),
                             Item('file_name', width=250),
                             ),
                      ),
                )

    def update_npulses(self):
        """ Reads out the number of Pulses available and displays them next to the Process-String
        """
        self.npulses = data.shape[2] - 1

    def set_bounds(self, image):
        """ Sets the bounds to the Maximum and Minimum Values, respectively.
        --- obsolete ---
        """
        temp = image.copy()
        for y in range(temp.shape[0]):
            for x in range(temp.shape[1]):
                if temp[y, x] > self.upper_bound:
                    temp[y, x] = self.upper_bound
                if temp[y, x] < self.lower_bound:
                    temp[y, x] = self.lower_bound
        return temp

    def get_order(self):
        """ Reads in the process string and splits it up into numbers and operators, makes a list out of it and returns it.
        """
        order_list = np.array([])
        tmp = ""
        for character in self.process:
            if character.isdigit():
                tmp += character
            elif character == " ":
                pass
            else:
                if len(tmp) > 0:
                    order_list = np.append(order_list, tmp)
                order_list = np.append(order_list, character)
                tmp = ""
        if len(tmp) > 0:
            order_list = np.append(order_list, tmp)
        return order_list


class ControlPanel(HasTraits):
    """ This object is the core of the traitsUI interface. Its view is
    the right panel of the application, and it hosts the method for
    interaction between the objects and the GUI.
    """
    # running = Bool(False)  # if True, the measurement is running. Who would have thought?
    # replaced by self.experiment.state == 'run'

    # bla = figure1
    # bla = self.figure1
    pulse_generator = None
    time_tagger = None
    microwave = None
    experiment = Instance(Generic_AFM_Pulsed, (pulse_generator, time_tagger, microwave))
    postprocessing = Instance(Postprocessing, ())
    image_properties = Instance(Image_properties, ())
    file_wildcard = String("pyd-File (*.pyd)|*.pyd|All files|*")

    calculate = Button("Calculate", desc="Calculates the Picture with the above settings")
    start_stop_acquisition = Button("Start/Stop acquisition",
                                    desc="Starts MW and Lasersequence and then bins the data to the appropriate Pixels")
    autorefresh = Bool(False,
                       desc="Enables an autorefresh of the currently recorded data, using the Postprocessing settings")
    night = Bool(True, desc="If set, Laser is turned off after measurement")
    save_data = Button("Save Data", desc="Saves the raw data and the current figures")
    load_data = Button("Load Data", desc="Load saved raw data for further processing")
    screen_dump = Button("Screen Dump", tooltip="Saves the current figures")
    image_prop = Button("Image Properties")

    get_rabi = Button("Get Rabi Data", desc="Loads an existing rabi-measurement to get t_pi2, t_pi, t_3pi2")

    results_string = String()
    auto_bound = Button("Auto")

    """def __init__(self,pulse_generator=None, time_tagger=None, microwave=None, figure1=None, figure2=None, figure3=None, figure4=None):
        self.experiment = Generic_AFM_Pulsed(pulse_generator, time_tagger, microwave)
        self.figure1, self.figure2, self.figure3, self.figure4 = [figure1, figure2, figure3, figure4]
    """

    def _start_stop_acquisition_fired(self):
        """ Callback of the "start stop acquisition" button. This starts or stops the measurement, including the AFM.
        """
        global data
        if self.experiment.state == 'run':
            ### running: stop the measurement & scanner, get & save data ###
            self.experiment._remove_button_fired()  # self.mes.Stop()
            self.experiment.state = 'idle'  # running = False
            self.getData()
            if self.experiment.sync_with[0] == "Attocube":
                nanonis.stop_scan()
            else:  # sync_with == 'Confocal'
                pass
                if confocal.ScanAction.isChecked():
                    confocal.ScanAction.trigger()
            if self.night:
                pass
                # self.mes.setNight()  # switches off the Laser after the measurement
            self._calculate_fired()
            self.add_line("Measurement stopped")
            self.postprocessing.file_increment += 1
            self._save_data_fired()
            self.add_line("Saving number is:" + str(self.postprocessing.file_increment))
            self.add_line("")
            # self.experiment.mes_running = self.running
        else:
            ### not running: update params and start measurement ###
            self.experiment.generate_sequence()  # will assign global variables!
            if self.experiment.t_pi == 0:
                print("load rabi data first")
                return
            self.experiment.state = 'run'  # running = True
            self.get_Pixels()
            if self.experiment.DualPass:
                ### DualPass: a 'lift' mode, where each line scan is followed by a repetition with some height offset.
                ### self.y: helper variable for the Generic_AFM_Pulsed measurement set up beneath.
                ### Since the time tagger setup procedure is implemented in pulsed.py in my case,
                ### using 'line_count', we set this global variable instead.
                ### was (TH's version): self.y = 2*self.experiment.y 
                global_vars.line_count = 2 * self.experiment.y
            else:
                self.y = self.experiment.y

            """self.mes = Generic_AFM_Pulsed(self.experiment.MWfreq, self.experiment.MWpower, 150e6, -10,
                                          self.experiment.bin_width, self.experiment.rabi_period,
                                          self.experiment.rabi_offset, 100, 0, self.experiment.record_length,
                                          self.experiment.LaserOn, self.experiment.LaserWait, self.experiment.mwList,
                                          self.experiment.x, self.y, self.experiment.win_low, self.experiment.win_high,
                                          self.experiment.ref_low, self.experiment.ref_high, self.experiment.tau)
            """
            self.experiment._submit_button_fired()  # self.mes.Start()
            # self.experiment.mes_running = self.running
            self.add_line("Measurement started")
            i = 0
            for element in self.experiment.mwList:
                self.add_line("MWsequence " + str(2 * i) + ": " + str(element))
                i += 1
            self.add_line("Microwave sequence currently used")
            self.autorefresh_handler()

    def _calculate_fired(self):
        """ Executes the current postprocessing routines"""
        self.postprocessing.update_npulses()
        self.order_list = self.postprocessing.get_order()
        self.image = np.zeros((data.shape[0], data.shape[1]))
        tmp = data.copy()
        order_string = ""
        for element in self.order_list:
            if element.isdigit():
                order_string += "tmp[:,:," + element + "]"
            else:
                order_string += element
        try:
            self.image = eval(order_string)
            # set empty data points to median of the existing data points
            self.image[np.isinf(self.image)] = np.median(self.image[-np.isinf(self.image)])
            self.image[np.isnan(self.image)] = np.median(self.image[-np.isnan(self.image)])
        except:
            # print "Unexpected error:", sys.exc_info()[0]
            # print "Setting image to zeros..."
            self.image = np.zeros((data.shape[0], data.shape[1]))

        if self.experiment.sync_with[0] == 'Confocal':
            xx = .5 * (self.image[:, ::2] + self.image[:, 1::2])
            self.image = xx.copy()

        self.image_show(self.image)

    def _get_rabi_fired(self):
        """ Loads a rabi measurment to determine t_pi2, t_pi and t_3pi2."""
        """self.get_Pixels()
        dialog = FileDialog(action="open", wildcard=self.file_wildcard)
        dialog.open()
        if dialog.return_code == OK:
            path = os.path.join(dialog.directory, dialog.filename)
            f = open(path, 'rb')
            self.rb = pickle.load(f, encoding='latin1')
            f.close()
            self.experiment.t_pi2, self.experiment.t_pi, self.experiment.t_3pi2 = #CalculatePulses('pi2', self.rb.RabiPeriod, self.rb.Rabix0)
            self.experiment.rabi_period = self.rb.RabiPeriod
            self.experiment.rabi_offset = self.rb.Rabix0
            self.experiment.MWfreq = self.rb.freq
            self.experiment.MWpower = self.rb.power
        """
        pass

    def _auto_bound_fired(self):
        """ determines the min/max bounds of the pictures"""
        self._calculate_fired()
        try:
            self.postprocessing.upper_bound = self.image.max()
            self.postprocessing.lower_bound = self.image.min()
        except AttributeError:
            print("AttributeError: Most probably there is no data loaded")
        except:
            print("Unexpected error:", sys.exc_info()[0])
        self._calculate_fired()

    def _save_data_fired(self):
        """ Callback of the "save_data" button.
        """
        if (self.postprocessing.file_dir == "") or (self.postprocessing.file_name == ""):
            dialog = FileDialog(action="save as", wildcard=self.file_wildcard)
            dialog.open()
            if dialog.return_code == OK:
                self.postprocessing.file_dir = dialog.directory
                self.postprocessing.file_name = dialog.filename
            else:
                return
        self._save_to_file()

    def _load_data_fired(self):
        """ Callback of the "load_data" button.
        """
        dialog = FileDialog(action="open", wildcard=self.file_wildcard)
        dialog.open()
        if dialog.return_code == OK:
            self.filedir = dialog.directory
            self.filename = dialog.filename
            self._load_from_file()
            self._calculate_fired()

    def _screen_dump_fired(self):
        """ Saves all the current pictures with the measurement number and the chosen postprocessing parameters"""
        if (self.postprocessing.file_dir == "") or (self.postprocessing.file_name == ""):
            self._save_data_fired()
        else:
            self._save_to_file(False)

    def _image_prop_fired(self):
        """ changes the properties of the images"""
        # self.image_properties.edit_traits()
        result = self.image_properties.configure_traits(kind='modal')
        if result:
            self._calculate_fired()

    def _save_to_file(self, saveall=True):
        """ Save data to the file `self.filedir`+`self.filename`.
        Additionally, all the parameters of the measurement are saved in an extra file.
        Is also used to save only the current pictures (when saveall = False).
        """

        # data = self.data

        def save_binary(data_to_save, save_path):
            """ Little helper function to open file, save data in binary via pickle, and close file again
            """
            fil = open(save_path, 'wb')
            pickle.dump(data_to_save, fil, 1)  # protocol version 1, compatible with older python versions.
            fil.close()

        if not os.path.isdir(self.postprocessing.file_dir):
            os.makedirs(self.postprocessing.file_dir)

        if saveall:
            # This gets executed when the data acquisition is finished.
            # saveall is False if only the postprocessed pictures are to be saved
            path = os.path.join(self.postprocessing.file_dir,
                                str(self.postprocessing.file_increment).zfill(3) + "_" + self.postprocessing.file_name)
            while os.path.isfile(path):
                self.postprocessing.file_increment += 1
                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(
                                        3) + "_" + self.postprocessing.file_name)
            save_binary(data, path)
            # f = open(path, 'wb')
            # pickle.dump(data, f, 1) # protocol version 1, should make it compatible with older python versions.
            # f.close()

            # save the raw data of the single images for further processing (bwd, fwd scan...)
            if self.experiment.DualPass:
                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_fwd.pyd")
                save_binary(data[::2, :data.shape[1] // 2],
                            path)  # selecting only the forth-direction and every other row

                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_bwd.pyd")
                save_binary(data[::2, data.shape[1] // 2:], path)  # selecting only the back-direction

                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_fwd_dual_pass.pyd")
                save_binary(data[1::2, :data.shape[1] // 2], path)

                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_bwd_dual_pass.pyd")
                save_binary(data[1::2, data.shape[1] // 2:], path)
            else:
                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_fwd.pyd")
                save_binary(data[:, :data.shape[1] // 2], path)  # selecting only the forth-direction

                path = os.path.join(self.postprocessing.file_dir,
                                    str(self.postprocessing.file_increment).zfill(3) + "_" +
                                    self.postprocessing.file_name.split(".")[0] + "_bwd.pyd")
                save_binary(data[:, data.shape[1] // 2:], path)  # selecting only the back-direction

            # save text file with measurement parameters
            path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                                self.postprocessing.file_name.split(".")[0] + "_parameters.txt")
            f = open(path, 'w')
            f.write("X: " + str(self.experiment.x) + "\n")
            f.write("Y: " + str(self.experiment.y) + "\n")
            self.Origin = nanonis.get_scan_offset()
            if not self.Origin == -1:  # [0] == 'DYB_Ok, No error': should change to nanonis jargon
                f.write("\nAFM Origin:\n    x: " + str(int(self.Origin[0] / 1e12)) + " nm\n    y: " + str(
                    int(self.Origin[1] / 1e12)) + " nm\n")
            else:
                f.write("Origin: not available\n")
            f.write("\nPixelSize: " + str(self.experiment.pixelsize * 1e9) + " nm\n")
            self.SampleTime = nanonis.get_sample_time()
            if not self.SampleTime == -1:  # [0] == 'DYB_Ok, No error': should change to nanonis jargon
                f.write("Sample Time: " + str(int(self.SampleTime * 1000)) + " ms\n")
            else:
                f.write("Sample Time: not available\n")

            f.write("MWfreq: " + str(self.experiment.frequency) + "\n")
            f.write("MWpower: " + str(self.experiment.power) + "\n")
            f.write("tau: " + str(self.experiment.tau) + "\n\n")
            i = 0
            for element in self.experiment.mwList:
                f.write("MWsequence " + str(2 * i) + ": " + str(element) + "\n")
                i += 1
            f.write("\nSettings:\n")
            f.write("Binwidth: " + str(self.experiment.bin_width) + "\n")
            f.write("Acq time: " + str(self.experiment.record_length) + "\n")
            f.write("Laser on: " + str(self.experiment.LaserOn) + "\n")
            f.write("Laser wait: " + str(self.experiment.LaserWait) + "\n")
            f.write("\nAcqWindow:\n")
            f.write("low: " + str(self.experiment.win_low) + "\n")
            f.write("high: " + str(self.experiment.win_high) + "\n")
            f.write("\nRefWindow:\n")
            f.write("low: " + str(self.experiment.ref_low) + "\n")
            f.write("high: " + str(self.experiment.ref_high) + "\n")
            f.write("\nRabiData:\n")
            # f.write("Rabi Period: " + str(self.experiment.rabi_period) + "\n")
            # f.write("Rabi Offset: " + str(self.experiment.rabi_offset) + "\n")
            f.write("t_pi2: " + str(self.experiment.t_pi2) + "\n")
            f.write("t_pi: " + str(self.experiment.t_pi) + "\n")
            f.write("t_3pi2: " + str(self.experiment.t_3pi2) + "\n")
            f.close()
            # save parameters to data file
            path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                                self.postprocessing.file_name.split(".")[0] + "_parameters.pyp")
            # workaround needed since time_tagger can not be pickled!
            # tt = self.experiment.time_tagger
            # self.experiment.time_tagger = None
            # save_binary(self.experiment, path) # TODO: MAKE THIS ALIVE AGAIN!!!
            # self.experiment.time_tagger = tt            
            # f = open(path, 'wb')
            # pickle.dump(self.experiment, f,1 )
            # f.close()

        def set_ticklabels(x, pos):
            return '%.2f' % (x * self.experiment.pixelsize * 1e6)

        formatter = matplotlib.ticker.FuncFormatter(set_ticklabels)
        colormap = self.image_properties.colormap[0]
        interpolationmethod = self.image_properties.interpolationmethod[0]

        if self.postprocessing.auto_bound:
            min = None
            max = None
        else:
            min = self.postprocessing.lower_bound
            max = self.postprocessing.upper_bound

        def save_png(image, save_path, figsize=(6.0, 6.0)):
            """ All the images are replotted to increase the plotsize and thus the resolution
            """
            fig1 = Figure(figsize=figsize)  # fig1 = matplotlib.pylab.figure(figsize=figsize)
            canvas = FigureCanvasAgg(fig1)
            fig1.add_subplot(111)
            if self.image_properties.scale_bar:
                self.add_scalebar(fig1.axes[0], save=True)
            colorbarimage = fig1.axes[0].imshow(image, aspect=self.aspectratio, origin='lower', cmap=colormap, vmin=min,
                                                vmax=max, interpolation=interpolationmethod)
            fig1.axes[0].xaxis.set_major_formatter(formatter)
            fig1.axes[0].yaxis.set_major_formatter(formatter)
            fig1.axes[0].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            fig1.axes[0].yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            fig1.tight_layout()
            # if self.image_properties.colorbar:
            # fig1.colorbar(colorbarimage) # trial of adding colorbars
            canvas.print_figure(save_path)  # fig1.savefig(save_path)
            # matplotlib.pylab.close()

        path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                            self.postprocessing.file_name.split(".")[0] + "_" + self.postprocessing.process.replace('/',
                                                                                                                    'div') + "_fwd.png")
        path.replace('*', 'times')

        save_png(self.image1, path)

        path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                            self.postprocessing.file_name.split(".")[0] + "_" + self.postprocessing.process.replace('/',
                                                                                                                    'div') + "_bwd.png")
        path.replace('*', 'times')
        # self.figure2.savefig(path)
        save_png(self.image2, path)

        if self.experiment.DualPass:
            path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                                self.postprocessing.file_name.split(".")[0] + "_" + self.postprocessing.process.replace(
                '/', 'div') + "_fwd_dual_pass.png")
            path.replace('*', 'times')
            # self.figure3.savefig(path)
            save_png(self.image3, path)
            path = os.path.join(self.postprocessing.file_dir, str(self.postprocessing.file_increment).zfill(3) + "_" +
                                self.postprocessing.file_name.split(".")[0] + "_" + self.postprocessing.process.replace(
                '/', 'div') + "_bwd_dual_pass.png")
            path.replace('*', 'times')
            # self.figure4.savefig(path)
            save_png(self.image4, path)

        self.saved = True

    def _load_from_file(self):
        """Load data from the file `self.filedir`+`self.filename`."""
        global data
        path = os.path.join(self.filedir, self.filename)
        f = open(path, 'rb')
        data = pickle.load(f, encoding='latin1')
        f.close()
        path = os.path.join(self.filedir, self.filename.split(".")[0] + "_parameters.pyp")
        # This try part is needed to be able to load data which was acquired prior to the implementation of the binary parameter file
        try:
            f = open(path, 'rb')
            self.experiment = pickle.load(f, encoding='latin1')
            f.close()
            self.postprocessing.file_increment = int(self.filename.split("_")[0])
            self.postprocessing.file_name = self.filename[4:]
            self.postprocessing.file_dir = self.filedir
            # self.experiment.mes_running = False
        except:
            print("no parameters file found, parameters not updated")
            pass

    def getData(self):
        """ gets data from the timetagger
        """
        global data
        data = self.experiment.count_data  # data = self.mes.getData()
        if self.experiment.state == 'run':
            self._calculate_fired()
        # else:
        # return data

    def add_line(self, string):
        """ Adds a line to the textbox display.
        """
        self.results_string = (string + "\n" + self.results_string)[0:1000]

    def add_scalebar(self, ax, matchx=True, matchy=False, hidex=True, hidey=True, clear=True, save=False, **kwargs):
        """ Add scalebars to axes
         
        Adds a set of scale bars to *ax*, matching the size to the ticks of the plot
        and optionally hiding the x and y axes
         
        - ax : the axis to attach ticks to
        - matchx,matchy : if True, set size of scale bars to spacing between ticks
        if False, size should be set using sizex and sizey params
        - hidex,hidey : if True, hide x-axis and y-axis of parent
        - **kwargs : additional arguments passed to AnchoredScaleBars
         
        Returns created scalebar object
        """

        scale_bar_pixel_length = self.image_properties.scale_bar_length / (self.experiment.pixelsize * 1.e9)

        r = ax.get_figure().canvas.get_renderer()
        t = ax.text(0, 0, str(self.image_properties.scale_bar_length) + " nm", color='white', ha='center',
                    weight='bold', transform=ax.transAxes, alpha=0)
        bb = t.get_window_extent(renderer=r)
        dbox = bb.transformed(ax.transData.inverted())

        text_width = int(math.ceil(dbox.width))
        text_height = int(math.ceil(dbox.height))

        white_patch_length = pylab.maximum(scale_bar_pixel_length, text_width) * self.image_properties.padding
        white_patch_height = (self.image_properties.thickness + text_height) * self.image_properties.padding

        if self.image_properties.scale_bar_position[0] == 'lower_left':
            white_patch_pos = (int(math.ceil(0.01 * self.experiment.x)), int(math.ceil(0.01 * self.experiment.y)))
        elif self.image_properties.scale_bar_position[0] == 'lower_right':
            white_patch_pos = (int(self.experiment.x - math.ceil(0.01 * self.experiment.x) - white_patch_length),
                               int(math.ceil(0.01 * self.experiment.y)))
        elif self.image_properties.scale_bar_position[0] == 'upper_left':
            white_patch_pos = (int(math.ceil(0.01 * self.experiment.x)),
                               int(self.experiment.y - math.ceil(0.01 * self.experiment.y) - white_patch_height))
        elif self.image_properties.scale_bar_position[0] == 'upper_right':
            white_patch_pos = (int(self.experiment.x - math.ceil(0.01 * self.experiment.x) - white_patch_length),
                               int(self.experiment.y - math.ceil(0.01 * self.experiment.y) - white_patch_height))

        scale_bar_pos = (
            white_patch_pos[0] + white_patch_length / 2. - scale_bar_pixel_length / 2.,
            white_patch_pos[1] + text_height)
        scale_bar_height = self.image_properties.thickness

        label_text_position_x = white_patch_pos[0] + white_patch_length / 2.
        label_text_position_y = white_patch_pos[1] + (self.image_properties.thickness + text_height) * (
                self.image_properties.padding - 1.) / 2.

        # print label_text_position_x
        # print label_text_position_y

        ax.add_patch(
            pylab.Rectangle(white_patch_pos, white_patch_length, white_patch_height, color='white', alpha=0.70))
        ax.add_patch(pylab.Rectangle(scale_bar_pos, scale_bar_pixel_length, scale_bar_height, color='black'))
        ax.text(label_text_position_x, label_text_position_y,
                str(int(round(scale_bar_pixel_length * self.experiment.pixelsize * 1e9))) + " nm", color='black',
                ha='center', weight='bold')

        ax.xaxis.set_visible(not self.image_properties.hide_axes)
        ax.yaxis.set_visible(not self.image_properties.hide_axes)

    def image_show(self, image):
        """ Plots an image on the canvas in a thread safe way.
        The back and forth pictures are seperated and flipped to match the AFM-pictures
        """
        try:
            if self.experiment.DualPass:
                self.image1 = image[::2, :image.shape[1] / 2]  # selecting only the forth-direction and every other row
                self.image2 = image[::2, image.shape[1] / 2:]  # selecting only the back-direction
                self.image3 = image[1::2, :image.shape[1] / 2]
                self.image4 = image[1::2, image.shape[1] / 2:]
            else:
                self.image1 = image[:, :image.shape[1] / 2]  # selecting only the forth-direction
                self.image2 = image[:, image.shape[1] / 2:]  # selecting only the back-direction

            if self.postprocessing.low_pass:
                if self.postprocessing.auto_bound:
                    self.image1 = ndimage.gaussian_filter(self.image1, self.postprocessing.lowpass_order)
                    self.image2 = ndimage.gaussian_filter(self.image2, self.postprocessing.lowpass_order)
                    if self.experiment.DualPass:
                        self.image3 = ndimage.gaussian_filter(self.image3, self.postprocessing.lowpass_order)
                        self.image4 = ndimage.gaussian_filter(self.image4, self.postprocessing.lowpass_order)
                else:
                    self.image1 = ndimage.gaussian_filter(
                        self.image1.clip(self.postprocessing.lower_bound, self.postprocessing.upper_bound),
                        self.postprocessing.lowpass_order)
                    self.image2 = ndimage.gaussian_filter(
                        self.image2.clip(self.postprocessing.lower_bound, self.postprocessing.upper_bound),
                        self.postprocessing.lowpass_order)
                    if self.experiment.DualPass:
                        self.image3 = ndimage.gaussian_filter(
                            self.image3.clip(self.postprocessing.lower_bound, self.postprocessing.upper_bound),
                            self.postprocessing.lowpass_order)
                        self.image4 = ndimage.gaussian_filter(
                            self.image4.clip(self.postprocessing.lower_bound, self.postprocessing.upper_bound),
                            self.postprocessing.lowpass_order)

            self.aspectratio = 1.0

            def set_ticklabels(x, pos):  # probably obsolete
                return '%.2f' % (x * self.experiment.pixelsize * 1e6)  # pm to um

            formatter = matplotlib.ticker.FuncFormatter(set_ticklabels)
            colormap = self.image_properties.colormap[0]
            interpolationmethod = self.image_properties.interpolationmethod[0]

            if self.postprocessing.auto_bound:
                min = None
                max = None
            else:
                if self.postprocessing.low_pass:
                    min = None
                    max = None
                else:
                    min = self.postprocessing.lower_bound
                    max = self.postprocessing.upper_bound

            self.figure1.axes[0].images = []
            self.figure1.axes[0].cla()
            self.image1[-1, 0] = np.mean(self.image1[:-1, :])  # skip defective first pixel
            colorbarimage = self.figure1.axes[0].imshow(self.image1, aspect=self.aspectratio, origin='lower',
                                                        cmap=colormap, vmin=min, vmax=max,
                                                        interpolation=interpolationmethod)
            self.figure1.axes[0].xaxis.set_major_formatter(formatter)
            self.figure1.axes[0].yaxis.set_major_formatter(formatter)
            self.figure1.axes[0].xaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            self.figure1.axes[0].yaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            if self.image_properties.scale_bar:
                self.add_scalebar(self.figure1.axes[0])

            self.figure1.tight_layout()
            # if self.image_properties.colorbar:
            #     self.figure1.colorbar(colorbarimage) # trial of adding colorbars
            wx.CallAfter(self.figure1.canvas.draw)

            self.image2 = self.image2[:, ::-1]  # flipping the image sideways
            self.figure2.axes[0].images = []
            self.figure2.axes[0].cla()
            colorbarimage = self.figure2.axes[0].imshow(self.image2, aspect=self.aspectratio, origin='lower',
                                                        cmap=colormap, vmin=min, vmax=max,
                                                        interpolation=interpolationmethod)
            self.figure2.axes[0].xaxis.set_major_formatter(formatter)
            self.figure2.axes[0].yaxis.set_major_formatter(formatter)
            self.figure2.axes[0].xaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            self.figure2.axes[0].yaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
            if self.image_properties.scale_bar:
                self.add_scalebar(self.figure2.axes[0])

            self.figure2.tight_layout()
            # if self.image_properties.colorbar:
            #     self.figure2.colorbar(colorbarimage) # trial of adding colorbars
            wx.CallAfter(self.figure2.canvas.draw)

            if self.experiment.DualPass:
                self.figure3.axes[0].images = []
                if self.image_properties.scale_bar:
                    self.add_scalebar(self.figure3.axes[0])
                colorbarimage = self.figure3.axes[0].imshow(self.image3, aspect=self.aspectratio, origin='lower',
                                                            cmap=colormap, vmin=min, vmax=max,
                                                            interpolation=interpolationmethod)
                self.figure3.axes[0].xaxis.set_major_formatter(formatter)
                self.figure3.axes[0].yaxis.set_major_formatter(formatter)
                self.figure3.axes[0].xaxis.set_major_locator(
                    matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
                self.figure3.axes[0].yaxis.set_major_locator(
                    matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
                self.figure3.tight_layout()
                # if self.image_properties.colorbar:
                #     self.figure3.colorbar(colorbarimage) # trial of adding colorbars
                wx.CallAfter(self.figure3.canvas.draw)

                self.image4 = self.image4[:, ::-1]  # flipping the image sideways
                self.figure4.axes[0].images = []
                if self.image_properties.scale_bar:
                    self.add_scalebar(self.figure4.axes[0])
                colorbarimage = self.figure4.axes[0].imshow(self.image4, aspect=self.aspectratio, origin='lower',
                                                            cmap=colormap, vmin=min, vmax=max,
                                                            interpolation=interpolationmethod)
                self.figure4.axes[0].xaxis.set_major_formatter(formatter)
                self.figure4.axes[0].yaxis.set_major_formatter(formatter)
                self.figure4.axes[0].xaxis.set_major_locator(
                    matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
                self.figure4.axes[0].yaxis.set_major_locator(
                    matplotlib.ticker.MaxNLocator(self.image_properties.ticknumber))
                self.figure4.tight_layout()
                # if self.image_properties.colorbar:
                #     self.figure4.colorbar(colorbarimage) # trial of adding colorbars
                wx.CallAfter(self.figure4.canvas.draw)
        except:
            print("error:", sys.exc_info()[0])
            raise

    def autorefresh_handler(self):
        autorefreshthread = threading.Thread(target=self.refresh_image)
        autorefreshthread.start()

    def refresh_image(self):
        """ Refreshes the image in an 1 s interval
        """
        time.sleep(5)  # Give the optical side time for setup
        if not self.experiment.state == 'run':
            print('returning')
            return
        if self.experiment.sync_with[0] == "Confocal":
            print("starting confocal scan")
            confocal.ScanAction.trigger()
        if self.experiment.sync_with[0] == "Attocube":
            res = nanonis.start_scan()  # The AFM-Scan is started at this point, since we want to give the optical side time to set itself up. In this thread the sleep(10) doesn't freeze the program
            print(res)
            print('scanner started')
            time.sleep(2)
        while self.experiment.state == 'run':
            if self.autorefresh:
                self.getData()
            if self.experiment.sync_with[0] == 'Attocube':
                if nanonis.get_scan_state() == 0 and self.experiment.state == 'run':
                    # scan finished!
                    self._start_stop_acquisition_fired()
                    break
            if self.experiment.sync_with[0] == 'Confocal':
                if not confocal.ScanAction.isChecked() and self.experiment.state == 'run':
                    self._start_stop_acquisition_fired()
                    break
            time.sleep(0.5)

    def get_Pixels(self):
        if self.experiment.sync_with[0] == 'Confocal':
            self.experiment.x = confocal.ResolutionControl.value()
            self.experiment.y = confocal.ResolutionControl.value() / 2
            x0, x1 = confocal.Navigation.axes.get_xlim()
            self.experiment.pixelsize = (x1 - x0) / confocal.ResolutionControl.value() * 1e-6
        else:  # sync_with == 'Attocube'
            px = nanonis.get_scan_pixels()
            self.experiment.x, self.experiment.y, self.experiment.pixelsize = px
            global_vars.pixel_count, global_vars.line_count = px[0:-1]
            """i = 0
            while 1:
                print self.pix[0]
                if self.pix[0] == 'DYB_Ok, No error':               # This whole while loop is a workaround for a timeout-problem
                    self.experiment.x = self.pix[1]                 # This occurs when a series of pictures is taken at different sites
                    self.experiment.y = self.pix]                 # The workaround simple skips the process of getting the momentary pixel and linecounts from the ASC500
                    self.experiment.pixelsize = self.pix[3]         # and sticks to the old ones. This could lead to problems if the pixelcount has been changed inbetween
                    break
                time.sleep(1)
                i += 1
                if i > 10:
                    print "asc500 readout failed, continuing with prior settings"
                    break
            del self.pix  
            """

    traits_view = View(Group(
        Group(
            HGroup(Item('start_stop_acquisition', show_label=False,
                        tooltip="Starts MW and Lasersequence and then bins the data to the appropriate Pixels"),
                   Item('autorefresh', show_label=True,
                        tooltip="Enables an autorefresh of the currently recorded data, using the Postprocessing settings"),
                   Item('night', show_label=True, tooltip="If set, Laser is turned off after measurement"),
                   ),
            # Item('running', style='readonly'),
            Item('results_string', show_label=False, springy=True, style='custom'),
            label="Control", dock='tab',
        ),
        Group(
            Item('experiment', style='custom', show_label=False),  # , springy=True),
            # Item('get_rabi', show_label=False, style='custom',
            # tooltip="Loads an existing rabi-measurement to get Tpi2, Tpi, T3pi2",
            # enabled_when="not running"),
            label='Experiment'  # , dock='tab',
        ),
        Group(
            Item('postprocessing', style='custom', show_label=False, dock="tab"),
            HGroup(
                Item('auto_bound', show_label=False, style='custom'),
                Item('calculate', show_label=False, style='custom'),
            ),
            HGroup(
                Item('screen_dump', show_label=False, tooltip="Saves the current figures"),
                Item('save_data', show_label=False, tooltip="Saves the raw data and the current figures",
                     enabled_when="not running"),
                Item('load_data', show_label=False, tooltip="Load saved raw data for further processing",
                     enabled_when="not running"),
                Item('image_prop', show_label=False, tooltip="change the image properties, such as colormap"),
            ),
            label="Postprocessing", dock='tab',
        ),
        layout='tabbed',
        # springy=True,
    ),
        kind='live',
        # icon = "icons/PulsedAFM.png", # doesn't work
    )


class MainWindowHandler(Handler):
    def close(self, info, is_OK):
        # print "Result of attempt to disconnect ASC500: " + asc500.server_disconnect() # disconnect is not sensible, yet, because it doesn't reconnect when the window is opened again.
        return True


class MainWindow(HasTraits):
    """ The main window, here go the instructions to create and destroy the application.
    """

    figure1 = Instance(Figure)
    figure2 = Instance(Figure)
    figure3 = Instance(Figure)
    figure4 = Instance(Figure)

    panel = Instance(ControlPanel, [None, None, None])

    def __init__(self, pulse_gen=None, time_tag=None, mw=None):  # , master):
        global data
        global nanonis
        nanonis = Nanonis()
        try:
            nanonis.connect()
        except:
            print('error connecting to nanonis')
        self.pulse_gen, self.time_tag, self.microwave = [pulse_gen, time_tag, mw]
        # self.panel = ControlPanel(pulse_gen, time_tag, mw, self.figure1, self.figure2, self.figure3, self.figure4)
        # global confocal

        self.panel.experiment.state = 'idle'  # running = False  # das muesste nach unten
        data = np.zeros((2, 2, 2))
        # asc500 = ASC500_Client.ASC500_Handler()
        # confocal = master
        self.panel.image_properties.colormap = ['afmhot']  # das muesste nach unten
        self.panel.image_properties.scale_bar_position = ['lower_right']  # das muesste nach unten
        self.panel.image_properties.interpolationmethod = ['none']  # das muesste nach unten
        # self.asc500_local = asc500

    def _figure1_default(self):
        figure1 = Figure()
        figure1.add_subplot(111)
        return figure1

    def _figure2_default(self):
        figure2 = Figure()
        figure2.add_subplot(111)
        return figure2

    def _figure3_default(self):
        figure3 = Figure()
        figure3.add_subplot(111)
        return figure3

    def _figure4_default(self):
        figure4 = Figure()
        figure4.add_subplot(111)
        return figure4

    def _panel_default(self):
        # self.panel = ControlPanel()
        # self.panel.figure1 = self.figure1
        # self.panel.figure2 = self.figure2
        # self.panel.figure3 = self.figure3
        # self.panel.figure4 = self.figure4
        # self.panel.running = False
        # self.panel.image_properties.colormap = ['gray']
        # return self.panel
        cp = ControlPanel(figure1=self.figure1, figure2=self.figure2, figure3=self.figure3,
                          figure4=self.figure4)  # this is some sort of __init__ for the panel
        cp.experiment = Generic_AFM_Pulsed(self.pulse_gen, self.time_tag, self.microwave)
        return cp

    view = View(HGroup(Group(
        HGroup(
            Item('figure1', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            Item('figure2', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            label='Contact', show_border=True,
        ),
        HGroup(
            Item('figure3', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            Item('figure4', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            label='Lift', show_border=True,
        ),
    ),
        # Item('panel', style="custom", springy=True, resizable=True,),
        Item('panel', style="custom", springy=True, resizable=True, ),
        show_labels=False,
    ),
        resizable=True,
        height=0.75, width=0.75,
        handler=MainWindowHandler(),
        buttons=NoButtons,
        kind='live',
        title="PulsedAFM",
        # icon = "icons/PulsedAFM.png", # doesn't work
    )
    """
    view = View(HSplit(Group(
        HGroup(
            Item('figure1', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            Item('figure2', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            label='Contact', show_border=True,
            ),
        HGroup(
            Item('figure3', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            Item('figure4', editor=MPLFigureEditor(), dock='vertical', show_label=False),
            label='Lift', show_border=True,
            ),
        ),
        # Item('panel', style="custom", springy=True, resizable=True,),
        Item('panel', style="custom", springy=True, resizable=True,),
        show_labels=False,
        ),
        resizable=True,
        height=0.75, width=0.75,
        handler=MainWindowHandler(),
        buttons=NoButtons,
        kind='live',
        title="PulsedAFM",
        # icon = "icons/PulsedAFM.png", # doesn't work
        )
    """


if __name__ == '__main__':
    mwin = MainWindow()
    mwin.edit_traits()
