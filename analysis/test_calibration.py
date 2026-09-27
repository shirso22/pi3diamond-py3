import numpy as np

from .coil_calibration import four_point_calibration
from .magnetometry import TripletSpin
from .magnetometry import axis_angle, rotation_matrix

a = np.array([[10., 2., 0.],
              [2.5, 11., 1.],
              [0., 3., 12.]])

offset = np.array([0.2, 0.3, 0.4])

currents = [3., 3., 3., 0.]

fields = [currents[0] * a[0] + offset,
          currents[1] * a[1] + offset,
          currents[2] * a[2] + offset,
          offset, ]

hamiltonians = 3 * [TripletSpin(D=2870.4)]
directions = np.array(((1, 1, 1), (-1, -1, 1), (1, -1, -1), (-1, 1, -1))) / 3 ** 0.5

measurements = []
for j in range(4):
    field = fields[j]
    transitions = []
    for i in range(3):
        hamiltonian = hamiltonians[i]
        axis = directions[i]
        nr, phi = axis_angle(axis, np.array((0, 0, 1)))
        rotation = rotation_matrix(nr, phi)
        transitions.append(hamiltonian.transitions(np.dot(rotation, field)))
    measurements.append((currents[j], np.array(transitions).real))

# print measurements

# sprint a.transpose()

hamiltonians = 3 * [TripletSpin(D=2870.5)]

ampere_to_gauss, offset_field = four_point_calibration(hamiltonians, measurements, signs=(1, 1, 1, 1.),
                                                       candidates=(1, 0, 1, 0))
print(ampere_to_gauss)
print(offset_field)
