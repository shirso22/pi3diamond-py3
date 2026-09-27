# PY3-PORT: pickle.load(..., encoding='latin1') throughout this file.
# Python 2 pickled `str` as bytes; without an explicit codec every string
# in a historical .pys file comes back as bytes, or raises
# UnicodeDecodeError. latin-1 round-trips bytes 0-255 one-to-one, so numpy
# arrays and ASCII dict keys both survive. No-op for Python 3 pickles.
import numpy as np
from scipy.optimize import leastsq

from .fitting import baseline, LorentzianZero, GaussianZeroY, n15


def n_lorentzians(*p):
    N = (len(p) - 1) // 3
    def f(x):
        #y = p[0] * np.ones(x.shape)
        y = p[0] * np.ones_like(x)
        for i in range(N):
            y += LorentzianZero(*p[i * 3 + 1:i * 3 + 4])(x)
        return y

    return f


def n_gaussians(*p):
    N = (len(p) - 1) // 3

    def f(x):
        #y = p[0] * np.ones(x.shape)
        y = p[0] * np.ones_like(x)
        for i in range(N):
            y += GaussianZeroY(*p[i * 3 + 1:i * 3 + 4])(x)
        return y

    return f


def n_n15(*p):
    N = (len(p) - 1) // 3

    def f(x):
        #y = p[0] * np.ones(x.shape)
        y = p[0] * np.ones_like(x)
        for i in range(N):
            y += n15(*p[i * 3 + 1:i * 3 + 4])(x)
        return y

    return f


def grow(mask):
    """Grows regions in a 1D binary array in both directions.
    Helper function to kill noise in odmr fit."""
    return np.logical_or(np.logical_or(mask, np.append(mask[1:], False)),
                         np.append(False, mask[:-1]))


def fit_odmr(x, y, threshold=0.5, number_of_peaks='auto', peakshape='lorentzian'):
    import inspect

    """Attempts to fit a sum of multiple peaks and returns the fit parameters
    (c, x0, g0, a0, x1, g1, a1,... ).

    We can choose what the peakshape is:
    lorentzian: single Lorentzian
    gaussian: single Gaussian
    n15: two Lorentzians, which are 3 MHz apart
    """

    # first re-scale the data to the range (0,1), such that the baseline is at 0.
    # flip the data in y-direction if threshold is negative
    y0 = baseline(y)

    yp = y - y0
    if threshold < 0:
        yp = -yp
    y_max = yp.max()
    #print("y_max =", y_max)

    yp = yp / y_max

    # compute crossings through a horizontal line at height 'threshold'
    mask = yp > abs(threshold)

    edges = np.where(np.logical_xor(mask, np.append(False, mask[:-1])))[0]
    if len(edges) % 2 != 0:
        raise RuntimeError('found an uneven number of edges')
    if len(edges) < 2:
        raise RuntimeError('did not find a distinct peak with the given threshold')

    N_detected = len(edges) // 2 #added fix stable peak control
    #print("Detected peaks:", N_detected)

    if number_of_peaks != 'auto':
        number_of_peaks = int(number_of_peaks)
        #print("Requested peaks:", number_of_peaks)

        if N_detected > number_of_peaks:
            edges = edges[: 2 * number_of_peaks]

        if N_detected < number_of_peaks:
            raise RuntimeError("Fewer peaks detected than requested.")

    N = len(edges) // 2
    #print("Final N used for fit:", N) #end fix
    '''
    if number_of_peaks == 'auto':  # try to find N automatically #fix from number_of_peaks is 'auto':
        # attempt initial growth of connected regions to kill noise
        while True:
            mask = grow(mask)
            new_edges = np.where(np.logical_xor(mask, np.append(False, mask[:-1])))[0]
            if len(new_edges) < len(edges):
                edges = new_edges
            else:
                break
    else:  # if N is specified grow until number of regions =< N
        while len(edges) // 2 > number_of_peaks:
            mask = grow(mask)
            edges = np.where(np.logical_xor(mask, np.append(False, mask[:-1])))[0]
    ''' #fix 26.02

    if len(edges) % 2 != 0:
        raise RuntimeError('found an uneven number of edges')
    if len(edges) < 2:
        raise RuntimeError('did not find a distinct peak with the given threshold')
    #N = len(edges) // 2
    #left_and_right_edges = edges.reshape((N, 2))
    raw_edges = edges.reshape((N, 2)) #added fix 26.02

    left_and_right_edges = []

    for left, right in raw_edges:
        if (right - left) > 3:  # minimum width of 3 points
            left_and_right_edges.append((left, right))

    #left_and_right_edges = np.array(left_and_right_edges)
    left_and_right_edges = np.array(left_and_right_edges)

    # HW-FIX: if the width filter above rejected everything, this array is
    # EMPTY, and the reshape below raised the bare NumPy error
    #     cannot reshape array of size 0 into shape (1,2)
    # which says nothing useful. Raise the same kind of message as the other
    # no-peak paths: the data simply has no resonance wide enough to fit.
    if left_and_right_edges.size == 0:
        raise RuntimeError('no peak survived the minimum-width filter '
                           '(candidates were narrower than 3 points -- '
                           'likely noise, not a resonance)')

    if left_and_right_edges.ndim == 1:
        left_and_right_edges = left_and_right_edges.reshape(1, 2)
    N = len(left_and_right_edges)

    #print("Peaks after width filter:", N) #end fix
    p = [0]
    # for every local maximum, estimate parameters of a Lorentzian and append them to the list of
    # parameters p
    for left, right in left_and_right_edges:
        if peakshape == 'n15':
            g = abs(x[right] - x[left]) / 2.  # FWHM
        else:
            g = abs(x[right] - x[left])  # FWHM
        i = y[left:right].argmax() + left  # index of local minimum
        x0 = x[i]  # position of local minimum
        if peakshape in ('lorentzian', 'n15'): #fix from == 'lorentzian' or 'n15'
            a = y[i] * np.pi * g  # height of local minimum in terms of Lorentzian parameter a
        if peakshape == 'gaussian':
            a = y[i]  # height of local minimum in terms of Gaussian parameter a
        p += [x0, g, a]

    #p = tuple(p)
    p = np.array(p, dtype=float)
    # chi for N Lorentzians with a common baseline
    '''
    def chi(p):
        ypp = p[0] - yp
        for i in range(N):
            if peakshape == 'lorentzian':
                ypp += LorentzianZero(*p[i * 3 + 1:i * 3 + 4])(x)
            if peakshape == 'gaussian':
                ypp += GaussianZeroY(*p[i * 3 + 1:i * 3 + 4])(x)
            if peakshape == 'n15':
                ypp += n15(*p[i * 3 + 1:i * 3 + 4])(x)
        return ypp
    '''

    def chi(p):
        #print("----- chi called -----")
        #print("len(p) =", len(p))
        #print("N =", N)
        #print("yp.shape =", yp.shape)

        ypp = p[0] - yp
        #print("ypp initial shape:", ypp.shape)

        for i in range(N):
            start = i * 3 + 1
            end = i * 3 + 4
            '''
            if end > len(p):
                print("Parameter length mismatch inside chi")
                params = [0, 1, 0]
            else:
                params = p[start:end]
            '''
            params = p[start:end] #fix
            if len(params) != 3:
                print("!!! BAD PARAM LENGTH inside chi, forcing default !!!", params)
                params = np.ones(3) * np.nan
            #print("i =", i, "params =", params, "len =", len(params)) #end

            if len(params) != 3:
                print("!!! BAD PARAM LENGTH !!!")

            if peakshape == 'lorentzian':
                test = LorentzianZero(*params)(x)
            elif peakshape == 'gaussian':
                test = GaussianZeroY(*params)(x)
            elif peakshape == 'n15':
                test = n15(*params)(x)
            else:
                raise RuntimeError("Unknown peakshape")

            #print("Lorentzian output shape:", test.shape)

            ypp += test
            #print("ypp shape after add:", ypp.shape)

        #print("Returning shape:", ypp.shape)
        return ypp
    #print("Final N:", N)
    #print("Initial parameter length:", len(p))
    #print("Expected parameter length:", 1 + 3 * N)
    r = leastsq(chi, p, full_output=True)

    if r[-1] == 0:
        raise RuntimeError('least square fit did not work out')

    p = np.array(r[0])

    y_amp = y_max * np.sign(threshold)

    # rescale fit parameters back to original data
    p[0] = p[0] * y_amp + y0
    p[3::3] *= y_amp

    try:
        delta = np.diag(r[1]) ** 0.5
        delta[0] = delta[0] * y_max
        delta[3::3] *= y_max
    except:
        # raise RuntimeError('Problem encounterd in Error calculation of fit.')
        delta = None

    return p, delta


if __name__ == '__main__':
    import pickle

    fil = open(
        '/home/helmut/projects/NewDefect/nuclear_polarization/alignement_at_LAC/2012-09-10/zeeman/D-E/2012-09-10_0306-05_DmE_zeeman_0.122A.pys',
        'rb')
    d = pickle.load(fil, encoding='latin1')
    x = d['frequency']
    y = d['counts']

    """
    y_max=y.max()
    y_min=y.min()

    N=int((y_max-y_min)/y_min**0.5)

    print(N)

    hist, bin_edges = np.histogram(y,N)

    import pylab
    pylab.close('all')
    pylab.plot(bin_edges[:-1],hist)
    pylab.show()
    """

    y_max = y.max()
    y_min = y.min()

    threshold = 8 * y_min ** 0.5 / (y_max - y_min)

    #print(threshold)

    p, dp = fit_odmr(x, y, threshold=threshold)

    import pylab

    pylab.close('all')
    pylab.plot(x, y)
    pylab.plot(x, n_lorentzians(*p)(x), 'r-')
    pylab.show()
