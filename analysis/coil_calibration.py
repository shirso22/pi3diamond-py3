import numpy as np
from scipy.optimize import leastsq

from .magnetometry import Magnetometer, TripletSpin


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


def four_point_calibration(hamiltonians, measurements, signs=(1, 1, 1, 1), candidates=(0, 0, 0, 0)):
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
        
        currents = (field - offset) * np.linalg.inv(ampere_to_gauss)    
    """
    magnetometer = Magnetometer(hamiltonians)
    b = []
    currents = []
    for i, measurement in enumerate(measurements):
        print('measurement %i' % i)
        current, transitions = measurement
        candidate = candidates[i]
        sign = signs[i]
        b_fit, b_est, b_cand, chisqr = magnetometer.get_field(transitions, sign, candidate, full_output=True)
        chisqr.sort()
        print('chi^2:      ', chisqr)
        print('rel. chi^2: ', chisqr / chisqr[0])
        print('candidate:  ', candidate)
        print('sign:       ', sign)
        print('b:          ', b_fit)
        print()
        b.append(b_fit)
        currents.append(current)
    b = np.array(b)
    currents = np.array(currents)
    offset = b[3]
    ampere_to_gauss = np.transpose(b[:3] - b[3]) / currents[:3]
    return ampere_to_gauss, offset


def three_straights_calibration(measurements):
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
        
        currents = (field - offset) * np.linalg.inv(ampere_to_gauss)
    """

    hams = (TripletSpin(), TripletSpin(), TripletSpin())
    magnetometer = Magnetometer(hams)
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

    #                                     nv50 A            nv46 C                nv47 D
    #   measurements = [(3.0, np.array([(2864.420,2884.572), (2840.582,2907.114), (2829.366,2916.622)])),
    #                   (3.0, np.array([(2838.768,2908.924), (2794.255,2948.301), (2815.202,2929.269)])),
    #                   (3.0, np.array([(2773.269,2968.954), (2838.072,2912.539), (2813.145,2934.250)])),
    #                   (0.0, np.array([(2869.136,2871.806), (2868.393,2872.547), (2869.672,2870.437)])),
    #                    ]
    # (0.0, np.array([(2869.257,2871.612), (2868.393,2872.547), (2869.672,2870.437)])),

    # 30/08/2013                       nv50 A            nv46 C                nv47 D
    measurements = [(3.0, np.array([(2864.340, 2884.417), (2840.556, 2907.113), (2829.220, 2916.745)])),
                    (3.0, np.array([(2838.716, 2908.849), (2794.242, 2947.505), (2816.328, 2928.280)])),
                    (3.0, np.array([(2772.604, 2969.538), (2838.284, 2912.526), (2813.140, 2934.428)])),
                    (0.0, np.array([(2869.257, 2871.612), (2868.393, 2872.547), (2869.672, 2870.437)]))
                    ]

    # zfs = measurements[-1][1].mean(axis=1)

    # hamiltonians = (TripletSpin(D=zfs[0]), TripletSpin(D=zfs[1]), TripletSpin(D=zfs[2]))

    # hamiltonians = (TripletSpin(), TripletSpin(), TripletSpin())

    # ampere_to_gauss_no_offset = three_point_calibration(hamiltonians, measurements[:3], signs=(1,-1,1))
    # print ampere_to_gauss_no_offset

    # ampere_to_gauss, offset_field = four_point_calibration(hamiltonians, measurements, signs=(1,-1,1,1), candidates=(0,0,0,0))
    # print ampere_to_gauss
    # print offset_field

    lines_43 = np.array([2.86615326e+09, 2.86830123e+09, 2.86939931e+09,
                         2.87047399e+09, 2.87155438e+09, 2.87374610e+09]) * 1e-6
    transitions_43 = (lines_43[[0, 1, 3]].mean(), lines_43[[2, 4, 5]].mean())
    zfs_43 = lines_43.mean()

    lines_46 = np.array([2.86817717e+09, 2.87049837e+09, 2.87252297e+09]) * 1e-6
    zfs_46 = lines_46[[0, 2]].mean()
    transitions_46 = (zfs_46, zfs_46)

    lines_47 = np.array([2.86728445e+09, 2.86828232e+09, 2.86948072e+09,
                         2.87042212e+09, 2.87162311e+09, 2.87263047e+09]) * 1e-6
    outer_splitting = ((lines_47[1] - lines_47[0]) + (lines_47[5] - lines_47[4])) / 2
    zfs_47 = lines_47.mean()
    transitions_47 = (zfs_47 - 0.5 * outer_splitting, zfs_47 + 0.5 * outer_splitting)

    lines_50 = np.array([2.86721875e+09, 2.86927486e+09, 2.87147561e+09, 2.87349694e+09]) * 1e-6
    zfs_50 = lines_50.mean()
    outer_splitting = ((lines_50[1] - lines_50[0]) + (lines_50[3] - lines_50[2])) / 2
    transitions_50 = (zfs_50 - 0.5 * outer_splitting, zfs_50 + 0.5 * outer_splitting)

    hamiltonians = (TripletSpin(D=zfs_50), TripletSpin(D=zfs_46), TripletSpin(D=zfs_47), TripletSpin(D=zfs_43))

    transitions = np.array([transitions_50, transitions_46, transitions_47, transitions_43])

    magnetometer = Magnetometer(hamiltonians)
    b_fit, b_est, b_cand, chisqr = magnetometer.get_field(transitions, full_output=True)

    sigma = chisqr ** 0.5
    sigma.sort()
    print('sigma:      ', sigma)
    print('rel. sigma: ', sigma / sigma[0])
    print('b:          ', b_fit)
    print()

    old_transitions = np.array([(2869.257, 2871.612), (2868.393, 2872.547), (2869.672, 2870.437)])
    old_zfs = old_transitions.mean(axis=1)
    # old_magnetometer = Magnetometer(3*[TripletSpin()])
    old_magnetometer = Magnetometer([TripletSpin(D=old_zfs[0]),
                                     TripletSpin(D=old_zfs[1]),
                                     TripletSpin(D=old_zfs[2])])
    old_result = old_magnetometer.get_field(old_transitions, candidate=0, full_output=True)

    old_b_fit, old_b_est, old_b_cand, old_chisqr = old_result
    old_sigma = old_chisqr ** 0.5
    old_sigma.sort()
    print('sigma:      ', old_sigma)
    print('rel. sigma: ', old_sigma / old_sigma[0])
    print('b:          ', old_b_fit)
    print()

#     transitions = TripletSpin().transitions((0,0,0)).real
#     measurements.append( (0.0,
#                           np.array([transitions+(.1,.2),
#                                     transitions+(.13,0.04),
#                                     transitions+(-.06,-.1)])))
#     
#     ampere_to_gauss, offset_field = four_point_calibration(measurements, signs=(1,-1,1,1.))
#     print ampere_to_gauss
#     print offset_field
#     
#     measurements[0]+=(1,)
#     measurements[1]+=(-1,)
#     measurements[2]+=(1,)
#     measurements[3]+=(1,)
#     
#     zero_point = measurements.pop()
#     
#     series = [ [zero_point, measurements[0]], [zero_point, measurements[1]], [zero_point, measurements[2]] ]
#     
#     ampere_to_gauss, offset_field = three_straights_calibration(series)
#     print ampere_to_gauss
#     print offset_field
