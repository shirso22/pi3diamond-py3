# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
This is a module used to provide a visualization and customization tools for editing
global_variables.py, a module which provides certain global variables and shares them across all
modules that use these on a regular basis.
"""

import threading

import numpy as np
from traits.api import HasTraits, Range
from traitsui.api import Handler, View, HGroup, Group, Item, TextEditor

import global_vars
from tools.emod import Job
from tools.utility import GetSetItemsMixin


class StartThreadHandler(Handler):
    def init(self, info):
        info.object.start()
        # PY3-PORT: TraitsUI 6 requires Handler.init() to return a
        # bool. Falling off the end returns None and raises when the
        # view opens. True means "initialisation succeeded".
        return True


class GlobalVarsEditor(Job, GetSetItemsMixin):
    win_low = Range(low=1., high=50000., value=600., desc='measurement window low value',
                    label='win_low [ns]', mode='text', auto_set=False, enter_set=True,
                    editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                      format_str='%.2f'))
    win_high = Range(low=1., high=50000., value=900., desc='measurement window high value',
                     label='win_high [ns]', mode='text', auto_set=False, enter_set=True,
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                       format_str='%.2f'))
    ref_low = Range(low=1., high=50000., value=2700., desc='reference window low value',
                    label='ref_low [ns]', mode='text', auto_set=False, enter_set=True,
                    editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                      format_str='%.2f'))
    ref_high = Range(low=1., high=50000., value=2900., desc='reference window high value',
                     label='ref_high [ns]', mode='text', auto_set=False, enter_set=True,
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                       format_str='%.2f'))
    pixel_count = Range(low=0, high=10000, value=0, desc='no. of pixels', label='no. of pixels',
                        mode='text', auto_set=False, enter_set=True,
                        editor=TextEditor(auto_set=False, enter_set=True, evaluate=int))
    line_count = Range(low=0, high=10000, value=0, desc='no. of lines', label='no. of lines',
                       mode='text', auto_set=False, enter_set=True,
                       editor=TextEditor(auto_set=False, enter_set=True, evaluate=int))
    mw_frequency = Range(low=1, high=20e9, value=2.500e9, desc='microwave frequency',
                         label='frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%.4e'))
    mw_power = Range(low=-100., high=25., value=-10, desc='microwave power', label='power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    mw_x_t_pi2 = Range(low=1., high=1e6, value=50., desc='pi/2 x pulse length', label='pi/2 x [ns]',
                       mode='text', auto_set=False, enter_set=True)
    mw_x_t_pi = Range(low=1., high=1e6, value=100., desc='pi x pulse length', label='pi x [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mw_x_t_3pi2 = Range(low=1., high=1e6, value=150., desc='3pi/2 x pulse length',
                        label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    mw_y_t_pi2 = Range(low=1., high=1e6, value=50., desc='pi/2 y pulse length', label='pi/2 y [ns]',
                       mode='text', auto_set=False, enter_set=True)
    mw_y_t_pi = Range(low=1., high=1e6, value=100., desc='pi pulse length', label='pi y [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mw_y_t_3pi2 = Range(low=1., high=1e6, value=150., desc='3pi/2 pulse length',
                        label='3pi/2 y [ns]', mode='text', auto_set=False, enter_set=True)

    def __init__(self, **kwargs):
        HasTraits.__init__(self, **kwargs)

    def update_values(self):
        gv = global_vars
        vars = [gv.win_low, gv.win_high, gv.ref_low, gv.ref_high, gv.pixel_count, gv.line_count,
                gv.mw_x_t_pi2, gv.mw_x_t_pi, gv.mw_x_t_3pi2, gv.mw_y_t_pi2, gv.mw_y_t_pi,
                gv.mw_y_t_3pi2]
        if True in np.isnan(vars[:-1]):
            return  # Traits' Ranges don't like to be set to NaN
        try:
            self.win_low, self.win_high, self.ref_low, self.ref_high, self.pixel_count, \
            self.line_count, self.mw_x_t_pi, self.mw_x_t_pi, self.mw_x_t_3_pi2, self.mw_y_t_pi, \
            self.mw_y_t_pi, self.mw_y_t_3_pi2
        except:
            pass

    def _win_low_changed(self, new):
        global_vars.win_low = new

    def _win_high_changed(self, new):
        global_vars.win_high = new

    def _ref_low_changed(self, new):
        global_vars.ref_low = new

    def _ref_high_changed(self, new):
        global_vars.ref_high = new

    def _pixel_count_changed(self, new):
        global_vars.pixel_count = new

    def _line_count_changed(self, new):
        global_vars.line_count = new

    def _mw_frequency_changed(self, new):
        global_vars.mw_frequency = new

    def _mw_power_changed(self, new):
        global_vars.mw_power = new

    def _mw_x_t_pi2_changed(self, new):
        global_vars.mw_x_t_pi2 = new

    def _mw_x_t_pi_changed(self, new):
        global_vars.mw_x_t_pi = new

    def _mw_x_t_3pi2_changed(self, new):
        global_vars.mw_x_t_3pi2 = new

    def _mw_y_t_pi2_changed(self, new):
        global_vars.mw_y_t_pi2 = new

    def _mw_y_t_pi_changed(self, new):
        global_vars.mw_y_t_pi = new

    def _mw_y_t_3pi2_changed(self, new):
        global_vars.mw_y_t_3pi2 = new

    def _run(self):
        while True:
            threading.current_thread().stop_request.wait(1.0)
            if threading.current_thread().stop_request.is_set():
                break
            self.update_values()

    get_set_items = ['win_low', 'win_high', 'ref_low', 'ref_high', 'pixel_count', 'line_count',
                     'mw_frequency', 'mw_power', 'mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2',
                     'mw_y_t_pi2', 'mw_y_t_pi', 'mw_y_t_3pi2']

    traits_view = View(
        Group(
            Item('mw_frequency', width=-70),
            Item('mw_power', width=-60),
            HGroup(
                Item('mw_x_t_pi2', width=-60),
                Item('mw_x_t_pi', width=-60),
                Item('mw_x_t_3pi2', width=-60),
            ),
            HGroup(
                Item('mw_y_t_pi2', width=-60),
                Item('mw_y_t_pi', width=-60),
                Item('mw_y_t_3pi2', width=-60),
            ),
        ),
        title='global variables',
        buttons=[],
        resizable=True,
    )

    # traits_view = View(VGroup(HGroup(Item('win_low', width=-60),
    #                                  Item('win_high', width=-60)
    #                                  ),
    #                           HGroup(Item('ref_low', width=-60),
    #                                  Item('ref_high', width=-60)
    #                                  ),
    #                           HGroup(Item('pixel_count', width=-60),
    #                                  Item('line_count', width=-60)
    #                                  ),
    #                           HGroup(Item('mw_frequency', width=-70),
    #                                  Item('mw_power', width=-60)
    #                                  ),
    #                           HGroup(Item('mw_x_t_pi2', width=-60),
    #                                  Item('mw_x_t_pi', width=-60),
    #                                  Item('mw_x_t_3pi2', width=-60),
    #                                  ),
    #                           HGroup(Item('mw_y_t_pi2', width=-60),
    #                                  Item('mw_y_t_pi', width=-60),
    #                                  Item('mw_y_t_3pi2', width=-60),
    #                                  ),
    #                           ),
    #                    title='global variables', buttons=[], resizable=True,
    #                    handler=StartThreadHandler
    #                    )
