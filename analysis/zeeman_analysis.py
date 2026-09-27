"""
(re)analyze all odmr files from a zeeman measurement
"""

basename = 'C:\\data\\2012-10-09\\0306-05\\Zeeman\\at-13.1-17.7\\D+E\\2012-10-18_0306-05_D+E_Zeeman'
currents = np.arange(0., 3., 1.)
zeros = np.zeros_like(current)

current = np.vstack((current, zeros, zeros)).transpose()

import measurements.odmr

odmr = measurements.odmr.ODMR()

transitions = np.empty_like(currents)

for i, current_i in enumerate(current):
    filename = basename + '_' + str(current_i * 1000) + '.pys'
    odmr.load(filename)
    odmr.perform_fit = True
    transitions[i] = odmr.fit_frequencies[1].mean()
