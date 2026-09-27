"""
This module provides classes and methods to gain full control over the system. In principle it only
provides a container for already existing measurement routines and system monitoring. The
advancement of this class is, that we visualize and include handling tools.

TODO: Include an nv_property class, where all relevant spin characteristics of a certain NV are
saved and can be loaded into the measurement, to prevent user copying errors and save time.
"""

from traits.api import HasTraits, Instance, Button, Bool
from traitsui.api import View, Item, HSplit, Group

from global_vars_editor import GlobalVarsEditor
from hardware.laser import IBeamSmart
from hardware.huebner_orange_laser import CoboltLaser
from hardware.power_meter import PM100D
from hardware.vector_magnet import Magnet
from measurements.autocorrelation import Autocorrelation
from measurements.awg.rabi_awg_pulsed import Rabi_awg_pulsed
from measurements.confocal_focus import ConfocalFocus
from measurements.deer import DEER, DEEREvolutionRf, DEEREvolutionTau
from measurements.deer_correlation import DEER_correlation, DarkSpin_Hahn, DarkSpin_Rabi, \
    DarkSpin_T1
from measurements.deer_rabi import DEERRabi
from measurements.deer_spectroscopy import DEERSpectroscopy, DEERSpectroscopyDQT
from measurements.generic import Generic_Pulsed
from measurements.hahn_echo import Hahn, HahnDQT
from measurements.odmr import ODMR
from measurements.photon_time_trace import PhotonTimeTrace as TimeTrace
from measurements.rabi import Rabi
from measurements.ramsey import Ramsey, RamseyDQT
from measurements.saturation import SaturationScan
from measurements.charge_state import ChargeStateDynamics
from measurements.t_one import T1pi, SingletDecay, T1Swap
from measurements.xy_8 import Qdyne
from measurements.xy_8 import XY_8


class Manager(HasTraits):
    """Visualization class of various Hardware.

    To simplify life we provide a container for many relevant variables of the microscope, such as
    control over the magnet, Laser control ect. but also we include tools to easily open and close
    measurements.
    """

    # global variables hooks
    global_vars_editor = Instance(GlobalVarsEditor)

    # Hardware
    laser = Instance(IBeamSmart)
    laser2 = Instance(CoboltLaser)
    pm = Instance(PM100D)
    vector_magnet = Instance(Magnet)

    # NV
    time_trace = Instance(TimeTrace)
    autocorrelation = Instance(Autocorrelation)
    saturation = Instance(SaturationScan)
    confocal_focus = Instance(ConfocalFocus)
    odmr = Instance(ODMR)
    rabi = Instance(Rabi)
    rabi_awg = Instance(Rabi_awg_pulsed)
    t1pi = Instance(T1pi)
    singletdecay = Instance(SingletDecay)
    t1swap = Instance(T1Swap)
    charge = Instance(ChargeStateDynamics)
    hahn = Instance(Hahn)
    hahn_dqt = Instance(HahnDQT)
    xy8 = Instance(XY_8)
    qdyne = Instance(Qdyne)
    generic = Instance(Generic_Pulsed)
    ramsey = Instance(Ramsey)
    ramsey_dqt = Instance(RamseyDQT)

    # External Spin
    deer_spectroscopy = Instance(DEERSpectroscopy)
    deer_spectroscopy_dqt = Instance(DEERSpectroscopyDQT)
    deer_rabi = Instance(DEERRabi)
    deer_simple = Instance(DEER)
    deer_evolution_tau = Instance(DEEREvolutionTau)
    deer_evolution_rf = Instance(DEEREvolutionRf)

    # External Spin Correlation
    deer_correlation = Instance(DEER_correlation)
    darkspin_rabi = Instance(DarkSpin_Rabi)
    darkspin_t1 = Instance(DarkSpin_T1)
    darkspin_hahn = Instance(DarkSpin_Hahn)

    pg_state = Bool(False, label="State")
    # NV
    time_trace_button = Button(label='Timetrace', desc='Open time_trace measurement.')
    autocorrelation_button = Button(label='Autocorrelation', desc='Open Autocorrelation measurement.')
    saturation_button = Button(label='Saturation Scan', desc='Open Saturation measurement.')
    confocal_focus_button = Button(label='Confocal Focus', desc='Open Confocal measurement.')
    odmr_button = Button(label='ODMR', desc='Open ODMR measurement.')
    rabi_button = Button(label='Rabi', desc='Open rabi measurement.')
    rabi_awg_button = Button(label='Rabi (AWG)', desc='Open rabi measurement.')
    t1_button = Button(label='T1', desc='Open Lifetime measurement.')
    singletdecay_button = Button(label='Singlet decay', desc='Open state lifetime measurement.')
    t1swap_button = Button(label='T1Swap', desc='Open upgraded lifetime measurement.')
    charge_state_button = Button(label='Charge State', desc='Open Charge state measurement.')
    hahn_button = Button(label='Hahn', desc='Open Hahn measurement.')
    hahn_dqt_button = Button(label='Hahn (DQT)', desc='Open Hahn DQT measurement.')
    xy8_button = Button(label='XY8', desc='Open xy8 measurement.')
    qdyne_button = Button(label='Qdyne', desc='Open Qdyne measurement')
    ramsey_button = Button(label='Ramsey', desc='Open Generic measurement.')
    ramsey_dqt_button = Button(label='Ramsey (DQT)', desc='Open Generic measurement.')
    generic_button = Button(label='Generic', desc='Open Generic measurement.')

    # External Spin
    deer_spectroscopy_button = Button(label='DEER Spectroscopy',
                                      desc='Open DEER spectroscopy. Using full NV spin state evaluation.')
    deer_spectroscopy_dqt_button = Button(label='DEER Spectroscopy (DQT)',
                                          desc='Open DEER spectroscopy using double quantum transition.')
    deer_rabi_button = Button(label='DEER Rabi', desc='Open DEER Rabi.')
    deer_simple_button = Button(label='DEER Simple', desc='Open DEER signal reference.')
    deer_evolution_tau_button = Button(label='DEER Evolution Tau',
                                       desc='Open DEER signal evolution measurement.')
    deer_evolution_rf_button = Button(label='DEER Evolution RF',
                                      desc='Open DEER signal evolution rf measurement.')

    # External Spin Correlation
    deer_correlation_button = Button(label='DEER Correlation',
                                     desc='Open DEER correlation reference.')
    darkspin_rabi_button = Button(label='Dark Spin Rabi', desc='Open Correlation Rabi reference.')
    darkspin_t1_button = Button(label='Dark Spin T1', desc='Open Correlation T1 reference.')
    darkspin_hahn_button = Button(label='Dark Spin Hahn', desc='Open Correlation Hahn measurement.')

    traits_view = View(
        HSplit(
            Group(
                Group(
                    Item('time_trace_button', show_label=False),
                    Item('autocorrelation_button', show_label=False),
                    Item('saturation_button', show_label=False),
                    Item('confocal_focus_button', show_label=False),
                    Item('odmr_button', show_label=False),
                    Item('rabi_button', show_label=False),
                    Item('rabi_awg_button', show_label=False),
                    Item('t1_button', show_label=False),
                    Item('singletdecay_button', show_label=False),
                    Item('t1swap_button', show_label=False),
                    Item('charge_state_button', show_label=False),
                    Item('hahn_button', show_label=False),
                    Item('hahn_dqt_button', show_label=False),
                    Item('xy8_button', show_label=False),
                    Item('qdyne_button', show_label=False),
                    Item('ramsey_button', show_label=False),
                    Item('ramsey_dqt_button', show_label=False),
                    Item('generic_button', show_label=False),
                    label="NV",
                    show_border=True,
                ),
            ),
            Group(
                Group(
                    Item('deer_spectroscopy_button', show_label=False),
                    Item('deer_spectroscopy_dqt_button', show_label=False),
                    Item('deer_rabi_button', show_label=False),
                    Item('deer_simple_button', show_label=False),
                    Item('deer_evolution_tau_button', show_label=False),
                    Item('deer_evolution_rf_button', show_label=False),
                    label="External Spin",
                    show_border=True,
                ),
                Group(
                    Item('deer_correlation_button', show_label=False),
                    Item('darkspin_rabi_button', show_label=False),
                    Item('darkspin_t1_button', show_label=False),
                    Item('darkspin_hahn_button', show_label=False),
                    label="External Spin Correlation",
                    show_border=True,
                ),
            ),
            Group(
                Group(
                    Item('global_vars_editor', style='custom', show_label=False),
                    label="Global Variables Editor",
                    show_border=True,
                ),
                Group(
                    Item('pg_state'),
                    label="Pulse generator",
                    show_border=True,
                ),
                Group(
                    Item('laser', style='custom', show_label=False),
                    Item('pm', style='custom', show_label=False),
                    label="Green Laser",
                    show_border=True,
                ),
                Group(
                    Item('laser2', style='custom', show_label=False),
                    label="Orange Laser",
                    show_border=True,
                ),
                Group(
                    Item('vector_magnet', style='custom', show_label=False),
                    label="Vector Magnet",
                    show_border=True,
                )
            ),
        ),
        title='Pi3diamond: Manager',
        resizable=True,
    )

    def __init__(self, laser=None, laser2=None, pulse_generator=None, time_tagger=None, scanner=None, counter=None,
                 microwave=None, microwave2=None, rf=None, pm=None, vector_magnet=None, awg=None):

        super(Manager, self).__init__()

        self.laser = laser
        self.laser2 = laser2
        self.pulse_generator = pulse_generator
        self.time_tagger = time_tagger
        self.scanner = scanner
        self.counter = counter
        self.microwave = microwave
        self.microwave2 = microwave2
        self.rf = rf
        self.pm = pm
        self.vector_magnet = vector_magnet
        self.awg = awg
        self.global_vars_editor = GlobalVarsEditor()
        self.global_vars_editor.load('defaults/global_variables.pys')

    def _pg_state_changed(self):
        """
        Connects traits button to laser state variable in CustomPulseGenerator class.
        Required by auto focus, which periodically checks the laser state variable
        in CustomPulseGenerator class.
        """
        if self.pg_state:
            self.pulse_generator.Light()
            self.pulse_generator.pg_laser_state = True
        else:
            self.pulse_generator.pg_laser_state = False
            self.pulse_generator.Night()

    def _time_trace_button_fired(self):
        if not isinstance(self.time_trace, TimeTrace):
            self.time_trace = TimeTrace(self.time_tagger)
        self.time_trace.edit_traits()

    def _confocal_focus_button_fired(self):
        if not isinstance(self.confocal_focus, ConfocalFocus):
            self.confocal_focus = ConfocalFocus(self.scanner, self.pulse_generator)
        self.confocal_focus.edit_traits()

    def _odmr_button_fired(self):
        if not isinstance(self.odmr, ODMR):
            self.odmr = ODMR(self.microwave, self.counter, self.pulse_generator)
        self.odmr.edit_traits()

    def _saturation_button_fired(self):
        if not isinstance(self.saturation, SaturationScan):
            self.saturation = SaturationScan(self.time_tagger, self.laser)
        self.saturation.edit_traits()

    def _autocorrelation_button_fired(self):
        if not isinstance(self.autocorrelation, Autocorrelation):
            self.autocorrelation = Autocorrelation(self.time_tagger)
        self.autocorrelation.edit_traits()

    def _rabi_button_fired(self):
        if not isinstance(self.rabi, Rabi):
            self.rabi = Rabi(self.pulse_generator, self.time_tagger, self.microwave, rf=self.rf,
                             microwave2=self.microwave2)
        self.rabi.edit_traits()

    def _rabi_awg_button_fired(self):
        if not isinstance(self.rabi_awg, Rabi_awg_pulsed):
            self.rabi_awg = Rabi_awg_pulsed(self.pulse_generator, self.time_tagger, rf=self.rf, awg=self.awg)
        self.rabi_awg.edit_traits()

    def _hahn_button_fired(self):
        if not isinstance(self.hahn, Hahn):
            self.hahn = Hahn(self.pulse_generator, self.time_tagger, self.microwave)
        self.hahn.edit_traits()

    def _hahn_dqt_button_fired(self):
        if not isinstance(self.hahn_dqt, HahnDQT):
            self.hahn_dqt = HahnDQT(self.pulse_generator, self.time_tagger, self.microwave, microwave2=self.microwave2)
        self.hahn_dqt.edit_traits()

    def _t1_button_fired(self):
        if not isinstance(self.t1pi, T1pi):
            self.t1pi = T1pi(self.pulse_generator, self.time_tagger, self.microwave)
        self.t1pi.edit_traits()

    def _singletdecay_button_fired(self):
        if not isinstance(self.singletdecay, T1pi):
            self.singletdecay = SingletDecay(self.pulse_generator, self.time_tagger, self.microwave)
        self.singletdecay.edit_traits()

    def _charge_state_button_fired(self):
        if not isinstance(self.charge, ChargeStateDynamics):
            self.charge = ChargeStateDynamics(self.pulse_generator, self.time_tagger, self.microwave)
        self.charge.edit_traits()

    def _t1swap_button_fired(self):
        if not isinstance(self.t1swap, T1pi):
            self.t1swap = T1Swap(self.pulse_generator, self.time_tagger, self.microwave)
        self.t1swap.edit_traits()

    def _xy8_button_fired(self):
        if not isinstance(self.xy8, XY_8):
            self.xy8 = XY_8(self.pulse_generator, self.time_tagger, self.microwave)
        self.xy8.edit_traits()

    def _qdyne_button_fired(self):
        if not isinstance(self.qdyne, Qdyne):
            self.qdyne = Qdyne(self.pulse_generator, self.time_tagger, self.microwave, rf=self.rf)
        self.qdyne.edit_traits()

    def _generic_button_fired(self):
        if not isinstance(self.generic, Generic_Pulsed):
            self.generic = Generic_Pulsed(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.generic.edit_traits()

    def _deer_spectroscopy_button_fired(self):
        if not isinstance(self.deer_spectroscopy, DEERSpectroscopy):
            self.deer_spectroscopy = DEERSpectroscopy(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_spectroscopy.edit_traits()

    def _deer_spectroscopy_dqt_button_fired(self):
        if not isinstance(self.deer_spectroscopy_dqt, DEERSpectroscopyDQT):
            self.deer_spectroscopy_dqt = DEERSpectroscopyDQT(self.pulse_generator, self.time_tagger, self.microwave,
                                                             self.microwave2, self.rf)
        self.deer_spectroscopy_dqt.edit_traits()

    def _deer_rabi_button_fired(self):
        if not isinstance(self.deer_rabi, DEERRabi):
            self.deer_rabi = DEERRabi(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_rabi.edit_traits()

    def _deer_simple_button_fired(self):
        if not isinstance(self.deer_simple, DEER):
            self.deer_simple = DEER(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_simple.edit_traits()

    def _deer_evolution_tau_button_fired(self):
        if not isinstance(self.deer_evolution_tau, DEEREvolutionTau):
            self.deer_evolution_tau = DEEREvolutionTau(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_evolution_tau.edit_traits()

    def _deer_evolution_rf_button_fired(self):
        if not isinstance(self.deer_evolution_rf, DEEREvolutionRf):
            self.deer_evolution_rf = DEEREvolutionRf(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_evolution_rf.edit_traits()

    def _deer_correlation_button_fired(self):
        if not isinstance(self.deer_correlation, DEER_correlation):
            self.deer_correlation = DEER_correlation(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.deer_correlation.edit_traits()

    def _darkspin_rabi_button_fired(self):
        if not isinstance(self.darkspin_rabi, DarkSpin_Rabi):
            self.darkspin_rabi = DarkSpin_Rabi(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.darkspin_rabi.edit_traits()

    def _darkspin_t1_button_fired(self):
        if not isinstance(self.darkspin_t1, DarkSpin_T1):
            self.darkspin_t1 = DarkSpin_T1(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.darkspin_t1.edit_traits()

    def _darkspin_hahn_button_fired(self):
        if not isinstance(self.darkspin_hahn, DarkSpin_Hahn):
            self.darkspin_hahn = DarkSpin_Hahn(self.pulse_generator, self.time_tagger, self.microwave, self.rf)
        self.darkspin_hahn.edit_traits()

    def _ramsey_button_fired(self):
        if not isinstance(self.ramsey, Ramsey):
            self.ramsey = Ramsey(self.pulse_generator, self.time_tagger, self.microwave)
        self.ramsey.edit_traits()

    def _ramsey_dqt_button_fired(self):
        if not isinstance(self.ramsey_dqt, RamseyDQT):
            self.ramsey_dqt = RamseyDQT(self.pulse_generator, self.time_tagger, self.microwave,
                                        microwave2=self.microwave2)
        self.ramsey_dqt.edit_traits()
