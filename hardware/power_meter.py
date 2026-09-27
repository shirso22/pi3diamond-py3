# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Readout and visualization of a Powermeter.
"""

import logging
import threading

import pyvisa as visa
from traits.api import HasTraits, Float, Range
from traitsui.api import View, Item

from tools.emod import FreeJob


class PM100D(FreeJob, HasTraits):
    """Provides control of thorlabs powermeter PM100D.
    
    This Class communicates with a Thorlabs PM100D via the visa protocol. The address of the
    instrument can be found via the supplied software by Thorlabs (which uses LabVIEW, found on 
    a USB Stick)
    """

    power = Float(desc='Power [mW]', label='Power [mW]')
    refresh_interval = Range(low=0.1, high=10, value=1., desc='Refresh interval [s]',
                             label='Refresh interval [s]')
    traits_view = View(Item('power', style='readonly'),
                       Item('refresh_interval'),
                       Item('start_button', show_label=False),
                       Item('stop_button', show_label=False),
                       title='Laser Power', width=400, buttons=[], resizable=True)

    def __init__(self, visa_address):
        self.rm = visa.ResourceManager()
        self.visa_address = visa_address
        self.instr = self.rm.open_resource(self.visa_address)

    def _write(self, string):
        try:  # if the connection is already open, this will work
            self.instr.write(string)
        except:  # else we attempt to open the connection and try again
            try:  # silently ignore possible exceptions raised by del
                del self.instr
            except Exception:
                pass
            self.instr = self.rm.open_resource(self.visa_address)
            self.instr.write(string)

    def _ask(self, str):
        try:
            val = self.instr.ask(str)
        except:
            self.instr = self.rm.open_resource(self.visa_address)
            val = self.instr.ask(str)
        return val

    def _run(self):
        """continuously retrieve the power.
        Note that we readout 10% of the power via a cubic beamsplitter.
        """
        try:
            self.state = 'run'
        except Exception as e:
            logging.getLogger().exception(e)
            raise
        else:
            while True:
                threading.current_thread().stop_request.wait(self.refresh_interval)
                if threading.current_thread().stop_request.is_set():
                    break
                try:
                    self.power = self.getPower()
                except Exception as e:
                    logging.getLogger().exception(e)
                    raise
        finally:
            self.state = 'idle'

    def getPower(self):
        # in mW and we get 0.1 due to the beamsplitter
        return float(self._ask('read?')) * 1e3

    def __del__(self):
        self.instr.close()
