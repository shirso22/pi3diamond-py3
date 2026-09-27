import numpy as np


class TripletSpin():
    """Triplet state Hamiltonian with D, E and Zeeman shift."""

    def __init__(self, D=2870.6, E=0.0, g=2.0028 * 9.27400915 / 6.626068):
        self.D = D
        self.E = E
        self.g = g

    def energy_levels(self, B):
        """Calculate the energy levels for given magnetic field."""
        D = self.D
        E = self.E
        g = self.g
        H = np.array(((0., 1j * g * B[1], -1j * g * B[0]),
                      (-1j * g * B[1], D - E, 1j * g * B[2]),
                      (1j * g * B[0], -1j * g * B[2], D + E)))
        e = np.linalg.eigvalsh(H)
        e.sort()
        return e

    def transitions(self, B):
        """
        Calculate the ESR transitions for given external field.
        Note that this method of sorting the energies fails above the LAC.
        """
        e = self.energy_levels(B)
        return np.array((e[1] - e[0], e[2] - e[0]))


class TripletNuclearSpin():
    """Triplet state Hamiltonian with D, E, electron Zeeman shift."""

    def __init__(self, D=2870.6, E=0.0, g=2.0028 * 9.27400915 / 6.626068):
        self.D = D
        self.E = E
        self.g = g

    def energy_levels(self, B):
        """Calculate the energy levels for given magnetic field."""
        D = self.D
        E = self.E
        g = self.g
        # PY3-PORT REPAIR: the source read "(-2. / 3. * D          0.," -- a
        # syntax error that predates this port. This file has never been
        # importable, under Python 2 either. Two readings were possible
        # (-2/3*D, or 0.); kept -2/3*D because it is the only thing that
        # distinguishes this class from TripletSpin above, which uses 0.
        # >>> REVIEW AGAINST THE INTENDED HAMILTONIAN CONVENTION. <<<
        H = np.array(((-2. / 3. * D, 1j * g * B[1], -1j * g * B[0]),
                      (-1j * g * B[1], D - E, 1j * g * B[2]),
                      (1j * g * B[0], -1j * g * B[2], D + E)))
        e = np.linalg.eigvalsh(H)
        e.sort()
        return e

    def transitions(self, B):
        """
        Calculate the ESR transitions for given external field.
        Note that this method of sorting the energies fails above the LAC.
        """
        e = self.energy_levels(B)
        return np.array((e[1] - e[0], e[2] - e[0]))
