"""
pi3diamond: A Python package to perform magnetometry using NV centers.

GitLab repository: https://gitlab.com/diamond_afm/pi3diamond

Diamond AFM, Kern Group, MPI for Solid State Physics
"""

import matplotlib as mpl

mpl.use('TkAGG')

import logging.handlers
import os

# Logging
logdir = "log/"
logfile = "diamond_log.txt"

if not os.path.isdir(logdir):
    os.makedirs("log")

# New log file every sunday
file_handler = logging.handlers.TimedRotatingFileHandler(logdir + logfile, 'W6')
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(module)s.%(funcName)s - %(levelname)s "
                                            "- %(message)s"))
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stream_handler)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().info('Starting logger.')

from tools import emod
emod.JobManager().start()

from tools import cron
cron.CronDaemon().start()

from tools.utility import StoppableThread
import threading


def shutdown(timeout=1.0):
    """Terminate all threads."""
    cron.CronDaemon().stop()
    emod.JobManager().stop()
    for t in threading.enumerate():
        if isinstance(t, StoppableThread):
            t.stop(timeout=timeout)


# Hardware
from hardware import TimeTagger as time_tagger

time_tagger._Tagger_setSerial('11130000UV')
p = time_tagger.Counter(0, int(1e12), 10)

from hardware.custom_pulse_generator import CustomPulseGenerator as PulseGenerator

pulse_generator = PulseGenerator(serial='fQWpZoZxWc',
                                 channel_map={'detect': 0, 'mw': 1, 'microwave': 1, 'mw_x': 1,
                                              'rf': 2, 'sequence': 3, 'mwy': 4, 'mw_y': 4, 'aom': 5,
                                              'ch5': 5, 'ch6': 6, 'awgTrigger': 6, 'microwave2': 7,
                                              'mw2': 7, 'aom2': 8})
pulse_generator.Night()

"""
# To switch between the RT and Cryo stage

1. Switch the Confocal Scanner
    RT Setup:
        Confocal x - Piezosystems Jena Input MOD 2
        Confocal y - Piezosystems Jena Input MOD 1
        Confocal z - Piezosystems Jena Input MOD 3
        NANONIS AUX CHANNEL (Confocal z): GAIN 1
        setup='rt'
        invert_x=True
    Cryo Setup:
        Confocal x - PI Piezocontroller 'lower pin'
        Confocal y - PI Piezocontroller 'upper pin'
        Confocal z - NANONIS AUX Output to 'Relais Box' GAIN 40
        setup='cryo'
        invert_x=False
2. Flip Mirror
"""

# Initialize hardware backend
from hardware.nidaq import Scanner
from hardware.labbrick_controller import LabBrick
from hardware.microwave_sources import SMIQ
from hardware.laser import IBeamSmart
from hardware.huebner_orange_laser import CoboltLaser
from hardware.power_meter import PM100D
from hardware.vector_magnet import Magnet
from hardware.awg import AWG

laser = IBeamSmart()
laser.enable_ch2()
laser.off()

# ORANGE-LASER (594 nm Cobolt, gated by pulse generator channel 8 = 'aom2').
# Left unconstructed, as in the lab branch: the driver defaults to COM5, which
# Cobolt Monitor holds while it is running -- only one process can own that
# port. Uncomment to drive the laser from pi3diamond instead.
# laser2 = CoboltLaser()
# laser2.open_connection()
# laser2.turn_off()
laser2 = None

scanner = Scanner(CounterIn='/Dev1/Ctr1',
                  CounterOut='/Dev1/Ctr0',
                  TickSource='/Dev1/PFI2',
                  AOChannels='/Dev1/ao0:2',
                  invert_x=True,
                  setup='rt')

from pyvisa import ResourceManager, VisaIOError

rm = ResourceManager()

autodetect_resources = True

# A dictionary with a `pretty` name and the full name
names = {'powermeter': 'Thorlabs,PM100D,P0008676,2.4.0\n',
         'smiq': 'Rohde&Schwarz,SMIQ03B,100961/0003,5.93HX \n',
         'magnet': 'LTC2609,Cls,D2604,01,01,DC,DC936,---------------\n'}

if autodetect_resources:
    # Generate a dictionary with the full names and addresses of HW devices
    instruments = {}

    logging.getLogger().info('Scanning hardware resources.')

    for address in rm.list_resources():
        try:
            inst = rm.open_resource(address, open_timeout=1)
            inst.timeout = 50
            name = inst.query("*IDN?")
        except VisaIOError:
            pass
        else:
            instruments[name] = address

    # Compare the generated dictionary with the predefined values
    # Raise a warning in case of mismatch
    for key, name in list(names.items()):
        if name not in list(instruments.keys()):
            logging.getLogger().warning("WARNING: Resource '{}' not found".format(key))
else:
    logging.warning("WARNING: Autodetect resources is off. {} will not be automatically detected.".format(list(names.keys())))

from hardware.nidaq import PulseTrainCounterIn

counter = PulseTrainCounterIn('/dev1/ctr1', None, '/dev1/pfi2', '/dev1/pfi0')


microwave = LabBrick('LSG-402-2')
microwave2 = LabBrick('LSG-402')


try:
    rf = SMIQ(instruments[names['smiq']])
except Exception:
    rf = None

try:
    vector_magnet = Magnet(instruments[names['magnet']])
except Exception:
    vector_magnet = None

try:
    pm100d = PM100D(instruments[names['powermeter']])
except Exception:
    pm100d = None

try:
    awg = AWG(address={'gpib': 'GPIB0::1::INSTR', 'ftp': '169.254.237.87', "port": "4001",
                       'socket': ('169.254.237.87', 4001)}, host="AWG", user='OEM', passwd='awg')
except Exception:
    awg = None


# Measurements
from hardware.nidaq import PulseTrainCounterOut

counter_deer = PulseTrainCounterOut('/dev1/ctr0', '/dev1/ctr1', '/dev1/pfi2')

from tools.manager import Manager

manager = Manager(laser=laser, laser2=laser2, pulse_generator=pulse_generator, time_tagger=time_tagger,
                  scanner=scanner, counter=counter, microwave=microwave, microwave2=microwave2,
                  rf=rf, pm=pm100d, vector_magnet=vector_magnet, awg=awg)

manager.edit_traits()
