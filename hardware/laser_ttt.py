import numpy as np
from traits.api import HasTraits, Range
from traitsui.api import View, Item

from hardware.nidaq import AOTask


class Laser(HasTraits):
    ao_channel = Str('/Dev1/ao3')
    voltage_min = Float(0.)
    voltage_max = Float(5.)

    voltage = Range(low='voltage_min', high='voltage_max', value='voltage_min', desc='output voltage',
                    label='Voltage [V]')

    def __init__(self, **kwargs):
        HasTraits.__init__(self, **kwargs)
        self._create_task()
        self.update_voltage(self.voltage)
        self.on_trait_change(self.update_voltage, 'voltage')

    def _create_task(self):
        self.ao_task = AOTask(Channels=self.ao_channel, range=(self.voltage_min, self.voltage_max))

    def update_voltage(self, new):
        self.ao_task.Write(np.array((new,)))

    view = View(Item('voltage'),
                title='Laser', width=400, buttons=[], resizable=True)


if __name__ == '__main__':
    laser = Laser()
    laser.edit_traits()
