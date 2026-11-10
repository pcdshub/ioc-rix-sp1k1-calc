"""
Core Calculations for RIX Mono (SP1K1) energy.

This is shared code between rix3 and ioc-rix-sp1k1-calc

Things to keep in mind:
- Must remain a calculations-only module
- No EPICS anywhere
- Don't change function names or arguments
- Don't add new package imports

This should be copied into ioc-rix-sp1k1-calc after any necessary calculation change
"""

import numpy as np

# Calibrations from 10/08/2026
offsetM2_base = 90745.7e-6
offsetG_LRG_base = 63075.6e-6
# High-res gratings offsets:
offsetG_LEG_base = 62925.3e-6
offsetG_MEG_base = 63882.8e-6
offsetG_HEG_base = 62925.3e-6

# Grating periods, 1/mm
D0_LRG = 50.0
D0_LEG = 300.0
D0_MEG = 450.0
D0_HEG = 700.0

# Deflection angles from MR1K1 and to the exit slit
# All angles in rad
thetaM1 = 0.03662
thetaES = 0.1221413

# Other constants
eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
R = 20.0e3  # mm, exit slit distance

### Calculations used in the IOC


def raw_calc_alpha_beta(pitchG: float, pitchM2: float, offsetG: float, offsetM2: float) -> tuple[float, float]:
    """
    Calculate the alpha and beta calculation intermediates.

    Parameters
    ----------
    pitchG : Grating pitch [μrad], float
    pitchM2 : pre-mirror pitch [μrad], float
    offsetG : total offset for grating pitch (mm), float
    offsetM2 : total offset for pre-mirror pitch (mm), float
    """
    pG = pitchG * 1e-6 - offsetG
    pM2 = pitchM2 * 1e-6 - offsetM2
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES
    return alpha, beta


def select_base_offset(name: str) -> float:
    """Return the base offset [mm] associated with grating name, or pre-mirror M2."""
    if name == "M2":
        return offsetM2_base
    elif name == "LRG":
        return offsetG_LRG_base
    elif name == "LEG":
        return offsetG_LEG_base
    elif name == "MEG":
        return offsetG_MEG_base
    elif name == "HEG":
        return offsetG_HEG_base
    else:
        raise ValueError("Invalid offset name, must be one of M2, LRG, LEF, MEG, HEG")


def select_D0(name: str) -> float:
    """Return the grating period [1/mm] associated with grating name."""
    if name == "LRG":
        return D0_LRG
    elif name == "LEG":
        return D0_LEG
    elif name == "MEG":
        return D0_MEG
    elif name == "HEG":
        return D0_HEG
    else:
        raise ValueError("Invalid D0 name, must be one of  LRG, LEF, MEG, HEG")


def raw_calc_energy(alpha: float, beta: float, dif_order: int, D0: float) -> float:
    """
    Calculate the mono photon energy [eV].

    Parameters
    ----------
    alpha : see raw_calc_alpha_beta, float
    beta : see raw_calc_alpha_beta, float
    dif_order : diffraction order, int
    D0 : grating period [1/mm], float
    """
    return dif_order * D0 * eVmm / (np.sin(alpha) + np.sin(beta))


def raw_calc_cff(alpha: float, beta: float) -> float:
    """
    Calculate the mono Cff.

    Parameters
    ----------
    alpha : see raw_calc_alpha_beta, float
    beta : see raw_calc_alpha_beta, float
    """
    return np.cos(beta) / np.cos(alpha)


def raw_calc_bandwidth(alpha: float, beta: float, dif_order: int, D0: float, slit_gap: float) -> float:
    """
    Calculate the mono bandwidth [eV].

    Parameters
    ----------
    alpha : see raw_calc_alpha_beta, float
    beta : see raw_calc_alpha_beta, float
    dif_order : diffraction order, int
    D0 : grating period [1/mm], float
    slit_gap : exit slit gap [mm], float
    """
    ang_disp = dif_order * D0 * eVmm * np.cos(beta) / (np.sin(alpha) + np.sin(beta)) ** 2  # angular dispersion
    lin_disp = ang_disp / R  # linear dispersion
    return (slit_gap / 1000) * lin_disp
