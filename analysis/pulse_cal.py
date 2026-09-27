"""
Manual fitting of a pulse calibration.

Helmut Fedder 2013-02-26
"""

import numpy as np
from numpy import pi

from .spin_manipulation import spin_matrix, expM


def pulse_cal(t_pi=0.05, t_del=0.0001, N=20, D=20., Z=20., g=10., hf=2.1):
    """
    Pulse Calibration on |-1> triplet

    input
    
        t_pi [mu s] = length of single pulses
        t_del [mu s] = length of single delay
        N          = number of pulses
        D [MHz]    = detuning of the microwave from the center between the +1 and -1 levels, positive: detuned to lower energy
        Z [MHz]    = Zeeman shift
        g [MHz]    = Rabi frequency of a single transition (coupling strength for 0 --> +1 transition)

    output

        sz       = one-dimensional array of same length as input 't', spin state expectation of s_z**2
        
    """

    Sz = spin_matrix(1, 'z')

    rho_0 = np.matrix(((0, 0, 0), (0, 1, 0), (0, 0, 0)), dtype=complex)  # initial density matrix

    z = np.zeros(N)

    for h in [-hf, 0., +hf]:  # loop over hyperfine triplet

        d = Z + h

        H_off = D * Sz ** 2 + d * Sz
        H_mw = np.matrix(((0, g / 2., 0),
                          (g / 2., 0, g / 2.),
                          (0, g / 2., 0)))
        H_on = H_off + H_mw

        P_p = expM(-2 * pi * 1j * H_on * t_pi)  # propagator for the pulse
        P_d = expM(-2 * pi * 1j * H_off * t_del)  # propagator for the delay

        P_1 = P_p * P_d  # propagator for one segment

        for n in range(N):
            P = P_1 ** n
            rho = P * rho_0 * P.transpose().conjugate()
            z[n] += np.real(np.trace(Sz ** 2 * rho))

    return (1.0 - z / 3.0)


#########################################
# Trait GUIs for pulsed fits
#########################################

from traits.api import Float, Tuple, on_trait_change
from traitsui.api import View, Item, Tabbed, VGroup
from chaco.api import ArrayPlotData, PlotLabel

from tools.chaco_addons import SavePlot as Plot, SaveTool

from .pulsed import PulsedTool


class PulseCalFit(PulsedTool):
    pi = Float(21., auto_set=False, enter_set=True)
    delay = Float(15., auto_set=False, enter_set=True)

    detuning = Float(20., auto_set=False, enter_set=True)
    zeeman_shift = Float(20., auto_set=False, enter_set=True)
    rabi_frequency = Float(10., auto_set=False, enter_set=True)
    hyperfine = Float(2.1, auto_set=False, enter_set=True)

    # combine all parameters to a tuple for easier handling    
    parameters = Tuple()

    # fit results
    # fit_result = Tuple()

    # fit_button = Button()
    # undo_button = Button()

    # add fit results to the get_set_items
    # get_set_items = PulsedTool.get_set_items + ['fit_result','text']
    # get_set_items = PulsedTool.get_set_items + ['text']

    def __init__(self, **kwargs):
        super(PulseCalFit, self).__init__(**kwargs)
        self.on_trait_change(self._on_parameters_changed, 'parameters', dispatch='ui')

    @on_trait_change('pi,delay,measurement.N,detuning,zeeman_shift,rabi_frequency,hyperfine')
    def _update_parameters(self):
        self.parameters = (self.pi,
                           self.delay,
                           self.measurement.N,
                           self.zeeman_shift,
                           self.detuning,
                           self.rabi_frequency,
                           self.hyperfine
                           )

    # overwrite the line_plot to include fit and text label 
    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  spin_state=np.array((0, 0)),
                                  theory=np.array((0, 0)))
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.plot(('index', 'theory'), color='red', name='fit')
        plot.index_axis.title = 'pulse number'
        plot.value_axis.title = 'spin state'
        plot.overlays.insert(0, PlotLabel(text='', hjustify='left', vjustify='bottom', position=[64, 32]))
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _on_parameters_changed(self, new):
        y0 = self.measurement.spin_state[0]
        y1 = self.measurement.spin_state[1]
        y = pulse_cal(*new) * (y0 - y1) + y1
        self.line_data.set_data('theory', y)
        text = ('pi [mus]: {0:f}\ndelay [mus]: {1:f}\nN: {2:g}\n'
                'detuning [MHz]: {3:f}\nzeeman [MHz]: {4:f}\n'
                'Rabi [MHz]: {5:f}\n'
                'hyperfine [MHz]: {6:f}'.format(*new)
                )
        self.line_plot.overlays[0].text = text

    # overwrite this to change the window title
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VGroup(Item('pi'),
                                     Item('delay'),
                                     Item('detuning'),
                                     Item('zeeman_shift'),
                                     Item('rabi_frequency'),
                                     Item('hyperfine'),
                                     ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=200, resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=200, resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=200, resizable=True),
                                     ),
                              ),
                       title='PulsCal Fit',
                       buttons=[], resizable=True
                       )


if __name__ == '__main__':
    pulse_cal_fit = PulseCalFit(measurement=pc_measurement)
    pulse_cal_fit.edit_traits()
    pulse_cal_fit.pi = 0.01
    pulse_cal_fit.delay = 0.001
    pulse_cal_fit.detuning = 200.
    pulse_cal_fit.zeeman_shift = 200.0
    pulse_cal_fit.rabi_frequency = 50.0
