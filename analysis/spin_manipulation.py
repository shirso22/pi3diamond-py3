import numpy as np
from scipy.linalg import expm2 as expm

pi = np.pi


def expM(a):
    return np.matrix(expm(a))


def spin_matrix(S=1, r='x'):
    """
    Constructs spin matrices.

    Input:

        S	=	the spin, e.g., 1./2, 1, 3/2, etc.
        r	=	the desired spin matrix. can be 'x', 'y', 'z', '+', '-', '2' (for S^2)

    Returns:

        the spin matrix. Colums are ordered as S, S-1, ..., -S+1, -S, such that standard
        pauli matrices are returned.

    Example of usage:

        Sy = spin_matrix(1,'y')
    """

    m = np.arange(S, -S - 0.5, -1)
    N = len(m)
    A = np.matrix(np.zeros((N, N), dtype=complex))
    if r == 'x':
        for ii, i in enumerate(m):
            for jj, j in enumerate(m):
                A[ii, jj] = 0.5 * (int(i == j + 1) + int(i + 1 == j)) * (S * (S + 1) - i * j) ** 0.5
    elif r == 'y':
        for ii, i in enumerate(m):
            for jj, j in enumerate(m):
                A[ii, jj] = -0.5j * (int(i == j + 1) - int(i + 1 == j)) * (S * (S + 1) - i * j) ** 0.5
    elif r == 'z':
        for ii, i in enumerate(m):
            for jj, j in enumerate(m):
                A[ii, jj] = int(i == j) * i
    elif r == '+':
        for ii, i in enumerate(m):
            for jj, j in enumerate(m):
                A[ii, jj] = int(i == j + 1) * (S * (S + 1) - i * j) ** 0.5
    elif r == '-':
        for ii, i in enumerate(m):
            for jj, j in enumerate(m):
                A[ii, jj] = int(i + 1 == j) * (S * (S + 1) - i * j) ** 0.5
    elif r == '2':
        A = np.eye(N, dtype=complex) * S * (S + 1)
    return A


def rabi(t, D=20., Z=20., g=10.):
    """
    Rabi oscillations on |-1> transition

    input

        t [mu s] = one-dimensional array, time mesh on which to calculate the Rabi oscillations
        D [MHz]  = detuning of the microwave from the center between the +1 and -1 levels, positive: detuned to lower energy
        Z [MHz]  = Zeeman shift
        g [MHz]  = Rabi frequency of a single transition (coupling strength for 0 --> +1 transition)

    output

        sz       = one-dimensional array of same length as input 't', spin state expectation of s_z**2

    """

    Sz = spin_matrix(1, 'z')

    H_off = D * Sz ** 2 + Z * Sz
    H_mw = np.matrix(((0, g / 2., 0),
                      (g / 2., 0, g / 2.),
                      (0, g / 2., 0)))
    H_on = H_off + H_mw

    z = np.empty_like(t)

    rho_0 = np.matrix(((0, 0, 0), (0, 1, 0), (0, 0, 0)), dtype=complex)

    for i, t_i in enumerate(t):
        Tau = expM(-2 * pi * 1j * H_on * t_i)
        rho = Tau * rho_0 * Tau.transpose().conjugate()
        z[i] = np.real(np.trace(Sz ** 2 * rho))

    return z


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

    return z


# t = np.arange(0, 1, 0.001)
# z = rabi(t)

z = pulse_cal(t_pi=0.048 / 2, t_del=0.015, N=50, D=125. / 2., Z=125. / 2., g=1. / 0.048, hf=2.1)

"""
Rabi oscillations on |-1> transition

Sz = spin_matrix(1,'z')

D       =   2.  # MHz detuning of mw from center between the +1 and -1 levels, positive: detuned to lower energy
d       =   5.  # MHz Zeeman shift
g_plus  = 100.  # MHz coupling strength for 0 --> +1 transition (rabi frequency of single transition)
g_minus = 100.  # MHz coupling strength for 0 --> -1 transition (rabi frequency of single transition)

H_off = D*Sz**2 + d*Sz
H_mw  = np.matrix( (( 0, g_plus/2.,  0),
				    (g_plus/2.,  0, g_minus/2.),
				    ( 0, g_minus/2.,  0)) )
H_on = H_off + H_mw

t = np.arange(0,0.01,.0001)
z = np.empty_like(t)

rho_0 = np.matrix( ((0,0,0),(0,1,0),(0,0,0)), dtype=complex )

for i, t_i in enumerate(t):
	Tau = expm( -2*pi*1j*H_on*t_i )
	rho =  Tau * rho_0 * Tau.transpose().conjugate()
	z[i] = np.real(np.trace(Sz**2*rho))
"""

"""
selective FID 100kHz above the |-1> transition

Sz = spin_matrix(1,'z')

D       = 10.  # MHz detuning of mw from center between the +1 and -1 levels, positive: detuned to lower energy
d       = 10.1 # MHz Zeeman shift
g_plus  = 1.0  # MHz coupling strength for 0 --> +1 transition (rabi frequency of single transition)
g_minus = 1.0  # MHz coupling strength for 0 --> -1 transition (rabi frequency of single transition)

H_off = D*Sz**2 + d*Sz
H_mw  = np.matrix( (( 0, g_plus/2.,  0),
				    (g_plus/2.,  0, g_minus/2.),
				    ( 0, g_minus/2.,  0)) )
H_on = H_off + H_mw


t_pi2 = 0.25 / g_minus

t = np.arange(0.,20.,.1)
z = np.empty_like(t)

rho_0 = np.matrix( ((0,0,0),(0,1,0),(0,0,0)), dtype=complex )

Pi2 = np.matrix(expm( -2*pi*1j*H_on*t_pi2 ))
for i, t_i in enumerate(t):
	Tau = np.matrix(expm( -2*pi*1j*H_off*t_i ))
	U = Pi2*Tau*Pi2
	rho =  U * rho_0 * U.transpose().conjugate()
	z[i] = np.real(np.trace(Sz**2*rho))
"""

"""
DQT FID 

Sz = spin_matrix(1,'z')

D       =   6.  # MHz detuning of mw from center between the +1 and -1 levels, positive: detuned to lower energy
d       =   4.  # MHz Zeeman shift
g_plus  = 100.  # MHz coupling strength for 0 --> +1 transition (rabi frequency of single transition)
g_minus = 100.  # MHz coupling strength for 0 --> -1 transition (rabi frequency of single transition)

H_off = D*Sz**2 + d*Sz
H_mw  = np.matrix( (( 0, g_plus/2.,  0),
				    (g_plus/2.,  0, g_minus/2.),
				    ( 0, g_minus/2.,  0)) )
H_on = H_off + H_mw


t_pi = 0.5 / (g_minus * 2**0.5)

t = np.arange(0.,1.,.001)
z = np.empty_like(t)

rho_0 = np.matrix( ((0,0,0),(0,1,0),(0,0,0)), dtype=complex )

Pi = np.matrix(expm( -2*pi*1j*H_on*t_pi ))
for i, t_i in enumerate(t):
	Tau = np.matrix(expm( -2*pi*1j*H_off*t_i ))
	U = Pi*Tau*Pi
	rho =  U * rho_0 * U.transpose().conjugate()
	z[i] = np.real(np.trace(Sz**2*rho))
"""

"""
selective FID 100kHz above the |-1> transition using switching from rotating to laboratory frame

NOT WORKING YET

Sz = spin_matrix(1,'z')

D       = 2800.
nu      = 2790.

d       = 10.1 # MHz Zeeman shift
g_plus  = 1.0  # MHz coupling strength for 0 --> +1 transition (rabi frequency of single transition)
g_minus = 1.0  # MHz coupling strength for 0 --> -1 transition (rabi frequency of single transition)

H_off_lab = np.matrix( (( D+d,  0,    0),
				     (   0,  0,    0),
				     (   0,  0,  D-d)) )

H_off  = np.matrix( (( D+d-nu,  0,       0),
				     (      0,  0,       0),
				     (      0,  0,  D-d-nu)) )

H_on   = np.matrix( ((    D+d-nu,   g_plus/2.,           0),
				     ( g_plus/2.,           0,  g_minus/2.),
				     (         0,  g_minus/2.,      D-d-nu)) )	

t_pi2 = 0.25 * g_minus

t = np.arange(0.,20.,.1)
zp = np.empty_like(t)

rho_0 = np.matrix( ((0,0,0),(0,1,0),(0,0,0)), dtype=complex )

R_pi2 = np.matrix( expm( -2*pi*1j*Sz**2*nu*t_pi2 ) )#.transpose().conjugate()

Pi2 = np.matrix(expm( -2*pi*1j*H_on*t_pi2 ))

#	RPi2 = R_pi2_inv*Pi2

for i, t_i in enumerate(t[20:21]):
	Tau = np.matrix(expm( -2*pi*1j*H_off*t_i ))
	U1   = Pi2*Tau*Pi2
	Tau_lab = np.matrix(expm( -2*pi*1j*H_off_lab*t_i ))
	R_tau = np.matrix( expm( -2*pi*1j*Sz**2*nu*t_i ) ).transpose().conjugate()
	U2 = Pi2*R_tau*Tau_lab*R_pi2*Pi2
	rho1 =  U1 * rho_0 * U1.transpose().conjugate()
	rho2 =  U2 * rho_0 * U2.transpose().conjugate()
	print rho1
	print rho2
	
#		zp[i] = np.real(np.trace(Sz**2*rho))
"""

"""
QDT FID with hard pulses

D    = 2000.
hnu  = 2000.5
Delta = D-hnu
d  = 0.25 # MHz Zeeman shift
g1 = 2.0 # MHz coupling strength for 0 --> +1 transition
g2 = 1.5 # MHz coupling strength for 0 --> -1 transition

H_off = D*Sz**2 + d*Sz
H_on  = np.matrix( ((D+hnu+d,  g1,        0),
				    (g1,        0,       g2),
				    ( 0,       g2,  D+hnu-d)) )	
	
t = np.arange(0,3.,.001)
z = np.empty_like(t)

rho_0 = np.matrix( ((0,0,0),(0,1,0),(0,0,0)), dtype=complex )

for i, t_i in enumerate(t):
	tau = expm(-2*pi*1j*H_on*t_i )
	R = expm( -1j * t_i * Sz**2 )
	U = tau * R 
	rho =  tau * rho_0 * tau.transpose().conjugate()
	z[i] = np.real(np.trace(Sz**2*rho))
"""

"""
nu = 2860.
D  = 2870. # MHz
d  =    3. # MHz
g1 =    2. # MHz
g2 =    1. # MHz

HS  = D*Sz**2 + d*Sz
HpS = (D-nu)*Sz**2 + d*Sz


HpF = HpS + HpI 

def switch(rho, phi, direction=1):
	U = expm(-1j*phi*Sz**2)
	#print U
	if direction == 1:
		return np.dot(U.conj(),np.dot(rho,U))
	elif direction == -1:
		return np.dot(U,np.dot(rho,U.conj()))

	
rho = np.array( ((0,0,0),
				 (0,1,0),
				 (0,0,0)), dtype=complex)

t1 = 1.0e-2
t2 = 3.0e-2

rho = propagate(rho, HpF, t1)
rho = propagate(rho, HpS, t2)

print rho

rho = np.array( ((0,0,0),
				 (0,1,0),
				 (0,0,0)), dtype=complex)

rho = propagate(rho, HpF, t1)
rho = switch(rho, 2*np.pi*nu*t1, 1)
rho = propagate(rho, HS, t2)
rho = switch(rho, 2*np.pi*nu*t2, -1)
print rho
"""
