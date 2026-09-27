import logging
import time

import numpy as np
from traits.api import Trait, Range
from traitsui.api import View, Item, Group, HGroup, VGroup, VSplit

from .confocal_focus import AutoFocus


def eval_none_float(s):
    if s == 'None':
        val = None
    else:
        val = float(s)
    return val


class AutoFocusDim(AutoFocus):
    """
    Auto focus tool with dimming of laser.
    """

    # wait = Range(low=0.0, high=60.0, value=1.0, desc='wait after changing laser voltage', label='wait', editor=TextEditor(auto_set=False, enter_set=True, evaluate=float) )

    def __init__(self, confocal, laser):
        super(AutoFocusDim, self).__init__(confocal)
        self.laser = laser
        self.add_trait('voltage',
                       Trait(None, None, Range(low=float(self.laser.voltage_min),
                                               high=float(self.laser.voltage_max),
                                               value=float(self.laser.voltage),
                                               desc='can be None or Float. If Float, use this voltage for the laser during focusing.',
                                               label='laser voltage')
                             )
                       )

    def _run(self):

        logging.getLogger().debug("trying run.")

        try:
            self.state = 'run'
            if self.voltage is not None:
                prev_voltage = self.laser.voltage
                self.laser.voltage = self.voltage
            if self.current_target is None:
                self.focus()
            else:  # focus target
                coordinates = self.targets[self.current_target]
                confocal = self.confocal
                confocal.x, confocal.y, confocal.z = coordinates + self.current_drift
                current_coordinates = self.focus()
                self.current_drift = current_coordinates - coordinates
                self.drift = np.append(self.drift, (self.current_drift,), axis=0)
                self.drift_time = np.append(self.drift_time, time.time())
                logging.getLogger().debug('Drift: %.2f, %.2f, %.2f' % tuple(self.current_drift))
            if self.voltage is not None:
                self.laser.voltage = prev_voltage
                time.sleep(0.1)
        finally:
            self.state = 'idle'

    get_set_items = AutoFocus.get_set_items + ['voltage']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('undo_button', show_label=False),
                                     ),
                              Group(VGroup(HGroup(Item('target_name'),
                                                  Item('add_target_button', show_label=False),
                                                  Item('remove_all_targets_button', show_label=False),
                                                  Item('forget_drift_button', show_label=False),
                                                  ),
                                           HGroup(Item('current_target'),
                                                  Item('next_target_button', show_label=False),
                                                  Item('remove_current_target_button', show_label=False),
                                                  ),
                                           HGroup(Item('periodic_focus'),
                                                  Item('focus_interval', enabled_when='not periodic_focus'),
                                                  ),
                                           label='tracking',
                                           ),
                                    VGroup(Item('size_xy'),
                                           Item('step_xy'),
                                           Item('size_z'),
                                           Item('step_z'),
                                           HGroup(Item('seconds_per_point_xy'),
                                                  Item('seconds_per_point_z'),
                                                  ),
                                           Item('voltage'),
                                           label='Settings',
                                           springy=True,
                                           ),
                                    layout='tabbed'
                                    ),
                              VSplit(Item('figure_image', show_label=False, resizable=True),
                                     Item('figure_line', show_label=False, resizable=True),
                                     Item('figure_drift', show_label=False, resizable=True),
                                     ),
                              ),
                       title='Auto Focus', width=500, height=700, buttons=[], resizable=True
                       )


# testing

if __name__ == '__main__':
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().info('Starting logger.')

    from tools.emod import JobManager

    JobManager().start()

    from tools.cron import CronDaemon

    CronDaemon().start()

    from measurements.confocal_focus import Confocal
    from hardware.api import Laser

    a = AutoFocusDim(Confocal(), Laser())
    a.edit_traits()
