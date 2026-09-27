import numpy as np
from scipy.optimize import leastsq

from analysis.magnetometry import Magnetometer, TripletSpin


def three_point_calibration(hamiltonians, measurements, signs=(1, 1, 1)):
    """
    Simple calibration based on one measurement with each coil.
    
    input:
    
    measurements    contains the three measurements for the three coils.
                    each measurement is a tuple of the form
                    
                        (current, transitions),
                        
                    where
                        'current' is the current applied to the coil and
                        'transitions' consists the ODMR transitions of the three NVs
                        and has the form ((-1,+1), (-1,+1), (-1,+1)).
                    
    signs           The resulting fields are multiplied with 'signs'. I.e., you
                    can use 'signs' to remove the ambiguity of the field direction.
                    In practice you will have to try out all possible combinations
                    of signs.
                    
    output:
    
    ampere_to_gauss 3x3 matrix that can be used to compute the field from a given current.
    
                        field = ampere_to_gauss * currents
                        
                    Use the inverse matrix to calculate the currents required for a
                    desired field.
                    
                        currents = np.linalg.inv(ampere_to_gauss) field
    
    """
    magnetometer = Magnetometer(hamiltonians)
    n = []
    for current, transitions in measurements:
        b_fit, b_est, b_cand, chisqr = magnetometer.get_field(transitions, full_output=True)
        n.append(b_fit / current)
    n = np.array(n)
    return n.transpose() * signs


def four_point_calibration(hamiltonians, measurements, signs=(1, 1, 1, 1)):
    """
    Simple calibration based on one measurement with each coil
    and one measurement at zero field.
    
    input:
    
    measurements    contains the four measurements for the three coils at high current
                    and one measurement at zero field. Each measurement is a tuple
                    
                        (current, transitions),
                        
                    where
                        'current' is the current applied to the coil and
                        'transitions' consists the ODMR transitions of the three NVs
                        and has the form ((-1,+1), (-1,+1), (-1,+1)).
                    
    signs           The resulting fields are multiplied with 'signs'. I.e., you
                    can use 'signs' to remove the ambiguity of the field direction.
                    In practice you will have to try out all possible combinations
                    of signs.
                    
    output:
    
    ampere_to_gauss 3x3 matrix
    
    offset          offset field [gauss]
    
    Use the matrix and offset to calculate the field from a current and current from a field:
    
        field = ampere_to_gauss * currents + offset
        
        currents = (field - offset) * np.linalg.inv(gauss_per_amp)    
    """
    magnetometer = Magnetometer(hamiltonians)
    b = []
    currents = []
    for current, transitions in measurements:
        b_fit, b_est, b_cand, chisqr = magnetometer.get_field(transitions, full_output=True)
        b.append(b_fit)
        currents.append(current)
    b = np.array(b)
    currents = np.array(currents)
    b = np.transpose(signs * np.transpose(b))
    offset = b[3]
    ampere_to_gauss = np.transpose(b[:3] - b[3]) / currents[:3]
    return ampere_to_gauss, offset


def three_straights_calibration(hamiltonians, measurements):
    """
    Calibration for 3 straights with common offset.
    
    input
    
    measurements    contains three series of measurements for the three coils.
                    each measurement is a list of tuples of the form
                    
                        [ (current, transitions, sign), (current, transitions, sign), ... ]
                        
                    where
                        'current' is the current applied to the coil and
                        'transitions' consists the ODMR transitions of the three NVs
                        and has the form ((-1,+1), (-1,+1), (-1,+1)).
                        'sign': The resulting fields are multiplied with 'sign'.
                        I.e., you can use 'sign' to remove the ambiguity of the
                        field direction. In practice you will have to try out
                        possible combinations of signs.
                    
    output:
    
    ampere_to_gauss 3x3 matrix
    
    offset          offset field [gauss]
    
    Use the matrix and offset to calculate the field from a current and current from a field:
    
        field = ampere_to_gauss * currents + offset
        
        currents = (field - offset) * np.linalg.inv(gauss_per_amp)
    """

    magnetometer = Magnetometer(hamiltonians)
    y = []
    x = []
    for coil in measurements:
        fields = []
        currents = []
        for current, transitions, sign in coil:
            b_fit, b_est, b_cand, chisqr = magnetometer.get_field(transitions, full_output=True)
            fields.append(b_fit * sign)
            currents.append(current)
        fields = np.array(fields)
        currents = np.array(currents)
        y.append(fields)
        x.append(currents)

    ampere_to_gauss = []
    offset = []
    for coordinate in range(3):
        def chi(p):
            a1, a2, a3, b = p
            part1 = a1 * x[0] + b - y[0][:, coordinate]
            part2 = a2 * x[1] + b - y[1][:, coordinate]
            part3 = a3 * x[2] + b - y[2][:, coordinate]
            return np.hstack((part1, part2, part3))

        guess = (y[0][-1, coordinate] / x[0][-1],
                 y[1][-1, coordinate] / x[1][-1],
                 y[2][-1, coordinate] / x[2][-1],
                 0.)
        p = leastsq(chi, guess)[0]
        ampere_to_gauss.append(p[:3])
        offset.append(p[3])
    ampere_to_gauss = np.array(ampere_to_gauss)
    offset = np.array(offset)
    return ampere_to_gauss, offset


if __name__ == '__main__':
    ### result from old script ###
    # ampere_to_gauss = [[  5.50200534, -9.47761127,   3.83365335],
    #                   [ -7.89713033, -2.05779109,   10.06609897],
    #                   [  4.43236343,  4.32183548,   6.23921791]],

    # old one                            nv50 A            nv46 C                nv47 D
    #    measurements = [(3.0, np.array([(2864.420,2884.572), (2840.582,2907.114), (2829.366,2916.622)])),
    #                    (3.0, np.array([(2838.768,2908.924), (2794.255,2948.301), (2815.202,2929.269)])),
    #                    (3.0, np.array([(2773.269,2968.954), (2838.072,2912.539), (2813.145,2934.250)]))
    #                    ]

    # 30/08/2013                       nv50 A            nv46 C                nv47 D
    measurements = [(3.0, np.array([(2864.340, 2884.417), (2840.556, 2907.113), (2829.220, 2916.745)])),
                    (3.0, np.array([(2838.716, 2908.849), (2794.242, 2947.505), (2816.328, 2928.280)])),
                    (3.0, np.array([(2772.604, 2969.538), (2838.284, 2912.526), (2813.140, 2934.428)])),
                    (0.0, np.array([(2869.257, 2871.612), (2868.393, 2872.547), (2869.672, 2870.437)]))
                    ]

    zfs = [2869.947669, 2870.456487, 2869.967540, 2869.990627]
    # hamiltonians = (TripletSpin(D=zfs[0]),TripletSpin(D=zfs[1]),TripletSpin(D=zfs[2]))
    hamiltonians = (TripletSpin(), TripletSpin(), TripletSpin())

    ampere_to_gauss = three_point_calibration(hamiltonians, measurements[:3], signs=(1, -1, 1))
    print(ampere_to_gauss)

    ampere_to_gauss, offset_field = four_point_calibration(hamiltonians, measurements, signs=(1, -1, 1, 1.))
    print(ampere_to_gauss)
    print(offset_field)

    # measurements[0]+=(1,)
    # measurements[1]+=(-1,)
    # measurements[2]+=(1,)
    # measurements[3]+=(1,)

    # zero_point = measurements.pop()

    # series = [ [zero_point, measurements[0]], [zero_point, measurements[1]], [zero_point, measurements[2]] ]

    # ampere_to_gauss, offset_field = three_straights_calibration(series)
    # print ampere_to_gauss
    # print offset_field
