"""
Calculations for RIX Mono (SP1K1) energy.

This is shared code between rix3 and ioc-rix-sp1k1-calc

Things to keep in mind:
- Keep as close to a calculations-only module as possible
- No EPICS gets outside of functions
- Must have a way to run each calculation function without an EPICS get (useful for IOC and for testing)
- Don't change function names
- Don't import rix.db or other hutch-python-only objects

This should be copied into ioc-rix-sp1k1-calc after any necessary calculation change
"""

import typing

import numpy as np
from epics import caget, caput

###############################################################################
#### GLOBAL CONSTANTS

# Calibration from 2021 by Alex Reid
# offsetM2 = 90641.0e-6
# offsetG_LRG = 63358.0e-6

# Calibration from 04/13/2024
# offsetM2 = 90641.0e-6
# offsetG_LRG = 62925.3e-6

# Calibrations from 10/08/2026
offsetM2 = 90745.7e-6
offsetG_LRG = 63075.6e-6
# High-res gratings offsets:
offsetG_LEG = 62925.3e-6
offsetG_MEG = 63882.8e-6
offsetG_HEG = 62925.3e-6

# grating periods, 1/mm
D0_LRG = 50.0
D0_LEG = 300.0
D0_MEG = 450.0
D0_HEG = 700.0

# Deflection angles from MR1K1 and to the exit slit
# All angles in rad
thetaM1 = 0.03662
thetaES = 0.1221413


def caget_with_error(pvname: str) -> typing.Any:
    """Wrap pyepics's caget with basic error handling."""
    value = caget(pvname)
    if value is None:
        raise RuntimeError("Failed to read PV: " + pvname)
    return value


def get_pitch_g(rbv: bool = True) -> float:
    """Return the live grating pitch position."""
    pv = "SP1K1:MONO:MMS:G_PI"
    if rbv:
        pv += ".RBV"
    return caget_with_error(pv)


def get_pitch_g_velo() -> float:
    """Return the live grating pitch velocity."""
    return caget_with_error("SL1K2:EXIT:MMS:G_PI.VELO")


def get_pitch_m2(rbv: bool = True) -> float:
    """Return the live mirror pitch position."""
    pv = "SP1K1:MONO:MMS:M_PI"
    if rbv:
        pv += ".RBV"
    return caget_with_error(pv)


def get_exit_slit_gap(rbv: bool = True) -> float:
    """Return the live exit slit gap."""
    pv = "SL1K2:EXIT:MMS:GAP"
    if rbv:
        pv += ".RBV"
    return caget_with_error(pv)


def get_dif_order() -> int:
    """Return the diffraction order."""
    return caget_with_error("SP1K1:MONO:CALC:DIF_ORDER")


def get_grating() -> str:
    """Return the live grating state."""
    return caget_with_error("SP1K1:MONO:GRATING:STATE:GET_RBV")


def get_grating_offset(grating: str = "") -> float:
    """
    Return the offset of the input grating.

    Uses the active grating if none is provided.
    """
    if not grating:
        grating = get_grating()
    if grating == "LRG":
        return offsetG_LRG + caget_with_error("SP1K1:MONO:CALC:LRG_OFFSET")
    elif grating == "LEG":
        return offsetG_LEG + caget_with_error("SP1K1:MONO:CALC:LEG_OFFSET")
    elif grating == "MEG":
        return offsetG_MEG + caget_with_error("SP1K1:MONO:CALC:MEG_OFFSET")
    elif grating == "HEG":
        return offsetG_HEG + caget_with_error("SP1K1:MONO:CALC:HEG_OFFSET")
    else:
        raise RuntimeError("Horizontal position is off grating.")


def get_grating_period(grating: str = "") -> float:
    """
    Return the period of the input grating.

    Uses the active grating if none is provided.
    """
    if not grating:
        grating = get_grating()
    if grating == "LRG":
        return D0_LRG
    elif grating == "LEG":
        return D0_LEG
    elif grating == "MEG":
        return D0_MEG
    elif grating == "HEG":
        return D0_HEG
    else:
        raise RuntimeError("Horizontal position is off grating.")


def calc_pitch(
    E: float,
    pitchM2: float | None = None,
    dif_order: int | None = None,
    offsetG: float | None = None,
    D0: float | None = None,
) -> tuple[float, float]:
    """
    Calculate the grating pitch and Cff for given photon energy and pre-mirror pitch.

    Based on Alex Reid calculator.
    Arguments:  E (required) - photon energy (eV)
                pitchM2 (optional) - pre-mirror pitch (urad)
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
                If only photon energy is provided then current pre-mirror pitch is used.
    Returns:    grating pitch (urad) and Cff
    Examples:   calc_pitch(400) - calculates grating pitch corresponding to 400 eV at the current pre-mirror pitch
                calc_pitch(500, 144650) - calculates grating pitch for 500 eV and 144650 urad pre-mirror pitch
    """
    if pitchM2 is None:
        pitchM2 = get_pitch_m2()
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]

    pM2 = pitchM2 * 1e-6 - offsetM2
    a0 = dif_order * D0 * eVmm / E
    pG = (
        pM2
        - 0.5 * thetaM1
        + 0.5 * thetaES
        - np.arcsin(0.5 * a0 / np.cos(0.5 * np.pi + pM2 - 0.5 * thetaM1 - 0.5 * thetaES))
    )
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES
    Cff = np.cos(beta) / np.cos(alpha)

    # grating pitch in urad
    pitchG = (pG + offsetG) * 1e6

    # print('Calculated grating pitch {0:8.2f} urad, Cff {1:3.2f}'.format(pitchG, Cff))
    return pitchG, Cff


def calc_pitchCff(
    E: float, Cff: float, dif_order: int | None = None, offsetG: float | None = None, D0: float | None = None
) -> tuple[float, float]:
    """
    Calculate the grating and pre-mirror pitch for given photon energy and Cff value.

    Based on Alex Reid calculator.
    Arguments:  E (required) - photon energy (eV)
                Cff (required) - Cff value
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
    Returns:    grating and pre-mirror pitch (urad)
    Example:    calc_pitchCff(400, 1.2) - calculates grating and pre-mirror pitch for 400 eV and Cff 1.2
    """
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
    # m = 2 # diffraction order

    a0 = dif_order * D0 * eVmm / E
    beta = -np.arccos(
        np.sqrt(
            (-(a0**2) * Cff**2 * (1 + Cff**2) + 2 * a0 * Cff**2 * np.sqrt(a0**2 * Cff**2 + Cff**4 - 2 * Cff**2 + 1))
            / (Cff**4 - 2 * Cff**2 + 1)
        )
    )
    alpha = np.arcsin(a0 - np.sin(beta))
    pG = -beta - np.pi / 2 + thetaES
    pM2 = 0.5 * (alpha - np.pi / 2 + pG + thetaM1)

    #
    pitchM2 = (pM2 + offsetM2) * 1e6
    pitchG = (pG + offsetG) * 1e6

    # print('Calculated pre-mirror pitch {0:8.2f} urad'.format(pitchM2))
    # print('Calculated grating pitch {0:8.2f} urad'.format(pitchG))
    return pitchG, pitchM2


def calc_E(
    pitchG: float | None = None,
    pitchM2: float | None = None,
    dif_order: int | None = None,
    offsetG: float | None = None,
    D0: float | None = None,
) -> tuple[float, float]:
    """
    Calculate photon energy and Cff for given grating and pre-mirror pitch.

    Based on Alex Reid calculator.
    Arguments:  pitchG (optional) - grating pitch (urad)
                pitchM2 (optional) - pre-mirror pitch (urad)
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
    Returns:    photon energy (eV) and Cff
    Examples:   calc_E() - calculates grating and pre-mirror pitch at current position, should be same as
                           SP1K1:MONO:CALC:ENERGY
                calc_E(153650) - calculates photon energy for 153650 urad grating pitch and current pre-mirror pitch
                calc_E(153650, 140800) - calculates photon energy for 153650 urad grating pitch and 144650 urad
                                         pre-mirror pitch
    """
    if pitchG is None:
        pitchG = get_pitch_g()
    if pitchM2 is None:
        pitchM2 = get_pitch_m2()
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
    # m = 1 # diffraction order

    pG = pitchG * 1e-6 - offsetG
    pM2 = pitchM2 * 1e-6 - offsetM2
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES
    E = dif_order * D0 * eVmm / (np.sin(alpha) + np.sin(beta))
    Cff = np.cos(beta) / np.cos(alpha)

    # print('Calculated photon energy {0:6.2f} eV, Cff {1:3.2f}'.format(E, Cff))
    return E, Cff


def calc_BW(
    slit: float | None = None,
    pitchG: float | None = None,
    pitchM2: float | None = None,
    dif_order: int | None = None,
    offsetG: float | None = None,
    D0: float | None = None,
) -> float:
    """
    Calculate mono bandwidth (eV).

    Arguments:  slit (optional) - exit slit gap (um)
                pitchG (optional) - grating pitch (urad)
                pitchM2 (optional) - pre-mirror pitch (urad)
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
    Returns:    mono bandwidth (eV)
    Examples:   calc_BW() - calculates monochromator bandwidth at the current slit and mono settings
                calc_BW(0.1) - calculates monochromator bandwidth for 0.1 mm slit at the current mono setting
                calc_BW(0.1, 153650, 140800) - calculates monochromator bandwidth for 0.1 mm slit and 153650 urad
                                               grating pitch and 144650 urad pre-mirror pitch
    """
    if slit is None:
        slit = get_exit_slit_gap()
        print("Exit slit gap is {0:8.2f} um".format(slit))
    if pitchG is None:
        pitchG = get_pitch_g()
        print("Grating pitch is {0:8.2f} urad".format(pitchG))
    if pitchM2 is None:
        pitchM2 = get_pitch_m2()
        print("Pre-mirror pitch is {0:8.2f} urad".format(pitchM2))
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
    # m = 1 # diffraction order
    R = 20.0e3  # mm, exit slit distance

    pG = pitchG * 1e-6 - offsetG
    pM2 = pitchM2 * 1e-6 - offsetM2
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES

    # E = m*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    # Cff = np.cos(beta)/np.cos(alpha)
    ang_disp = dif_order * D0 * eVmm * np.cos(beta) / (np.sin(alpha) + np.sin(beta)) ** 2  # angular dispersion
    lin_disp = ang_disp / R  # linear dispersion
    BW = (slit / 1000) * lin_disp

    # print('Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}'.format(E, Cff))
    # print('Angular dispersion is {0:6.2f} eV/rad'.format(ang_disp))
    # print('Linear dispersion is {0:6.2f} eV/mm'.format(lin_disp))
    # print('Bandwidth is {0:6.2f} eV'.format(BW))
    return BW


def calc_grating_velocity_eV(
    velocity: float | None = None,
    pitchG: float | None = None,
    pitchM2: float | None = None,
    dif_order: int | None = None,
    offsetG: float | None = None,
    D0: float | None = None,
):
    """
    Calculate mono grating velocity.

    Arguments:  velocity - grating velocity in urad (urad/sec)
                pitchG - grating pitch (urad)
                pitchM2 - pre-mirror pitch (urad)
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
    Returns:    grating velocity (eV/sec)
    Examples:   calc_grating_velocity_eV() - calculates monochromator velocity at the current mono settings
    """
    if velocity is None:
        velocity = get_pitch_g_velo()
        print("Velocity is {0:8.2f} urad/sec".format(velocity))
    if pitchG is None:
        pitchG = get_pitch_g()
        print("Grating pitch is {0:8.2f} urad".format(pitchG))
    if pitchM2 is None:
        pitchM2 = get_pitch_m2()
        print("Pre-mirror pitch is {0:8.2f} urad".format(pitchM2))
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
    # m = 1 # diffraction order
    # R = 20.0e3 # mm, exit slit distance

    pG = pitchG * 1e-6 - offsetG
    pM2 = pitchM2 * 1e-6 - offsetM2
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES

    E = dif_order * D0 * eVmm / (np.sin(alpha) + np.sin(beta))
    Cff = np.cos(beta) / np.cos(alpha)
    ang_disp = dif_order * D0 * eVmm * np.cos(beta) / (np.sin(alpha) + np.sin(beta)) ** 2  # angular dispersion
    velocity_eV = ang_disp * velocity * 1e-6

    print("Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}".format(E, Cff))
    print("Angular dispersion is {0:6.2f} eV/urad".format(ang_disp * 1e-6))
    print("Velocity is {0:6.2f} eV/sec".format(velocity_eV))
    return velocity_eV


def calc_slit(
    BW: float,
    pitchG: float | None = None,
    pitchM2: float | None = None,
    dif_order: int | None = None,
    offsetG: float | None = None,
    D0: float | None = None,
):
    """
    Calculate exit slit gap (um).

    Arguments:  BW (required) - bandwidth (eV)
                pitchG (optional) - grating pitch (urad)
                pitchM2 (optional) - pre-mirror pitch (urad)
                dif_order (optional) - diffraction order
                offsetG (optional) - grating offset (mm)
                D0 (optional) - grating period (1/mm)
                All optional arguments will pull from live PV values.
    Returns:    gap (um)
    Examples:   calc_slit(0.1) - calculates exit slit gap for 0.1 eV bandwidth at the current mono setting
                calc_slit(0.1, 153650, 140800) - calculates exit slit gap for 0.1 eV bandwidth for 153650 urad grating
                                                 pitch and 144650 urad pre-mirror pitch
    """
    if pitchG is None:
        pitchG = get_pitch_g()
        print("Grating pitch is {0:8.2f} urad".format(pitchG))
    if pitchM2 is None:
        pitchM2 = get_pitch_m2()
        print("Pre-mirror pitch is {0:8.2f} urad".format(pitchM2))
    if dif_order is None:
        dif_order = get_dif_order()
    if offsetG is None:
        offsetG = get_grating_offset()
    if D0 is None:
        D0 = get_grating_period()

    # constants
    eVmm = 0.001239842  # Wavelenght[mm] = eVmm/Energy[eV]
    # m = 2 # diffraction order
    R = 20.0e3  # mm, exit slit distance

    pG = pitchG * 1e-6 - offsetG
    pM2 = pitchM2 * 1e-6 - offsetM2
    alpha = np.pi / 2 - pG + 2 * pM2 - thetaM1
    beta = -np.pi / 2 - pG + thetaES

    # E = m*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    # Cff = np.cos(beta)/np.cos(alpha)
    ang_disp = dif_order * D0 * eVmm * np.cos(beta) / (np.sin(alpha) + np.sin(beta)) ** 2  # angular dispersion
    lin_disp = ang_disp / R  # linear dispersion
    slit = BW / lin_disp

    # print('Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}'.format(E, Cff))
    # print('Angular dispersion is {0:6.2f} eV/rad'.format(ang_disp))
    # print('Linear dispersion is {0:6.2f} eV/mm'.format(lin_disp))
    # print('Exit slit gap {0:6.2f} eV'.format(BW))
    return slit * 1000


def calc_slitE(BW: float, E: float, Cff: float):
    """
    Calculate exit slit gap (um).

    Arguments:  BW (required) - bandwidth (eV)
                E (required) - photon energy (eV)
                Cff (required) - Cff value
    Returns:   gap (um)
    Examples:  calc_slitE(0.1, 400, 1.2) - calculates exit slit gap for 0.1 eV bandwidth at 400 eV and 1.2 Cff
    """
    pitchG, pitchM2 = calc_pitchCff(E, Cff)
    slit = calc_slit(BW, pitchG, pitchM2)

    return slit


def get_E():
    """
    Print current status.

    Reports current photon energy and Cff for based on current grating and pre-mirror pitch target and RBV.
    Reports mono bandwidth based on the exit slit gap.
    Reports the FEL set energy.
    Arguments: none
    Returns:   none
    """
    pitchG = get_pitch_g()
    pitchG_target = get_pitch_g(rbv=False)
    pitchM2 = get_pitch_m2()
    pitchM2_target = get_pitch_m2(rbv=False)
    slit = get_exit_slit_gap()
    slit_target = get_exit_slit_gap(rbv=False)

    E_FEL = caget_with_error("RIX:USER:MCC:EPHOTK:SET1")

    print("Grating pitch RBV {0:8.2f} urad, target {1:8.2f} urad".format(pitchG, pitchG_target))
    print("Pre-mirror pitch RBV {0:8.2f} urad, target {1:8.2f} urad".format(pitchM2, pitchM2_target))
    print("Exit slit gap RBV {0:3.2f} um, target {1:3.2f} um".format(slit, slit_target))

    # RBV
    E, Cff = calc_E(pitchG, pitchM2)
    BW = calc_BW(slit, pitchG, pitchM2)

    # target
    E_target, Cff_target = calc_E(pitchG_target, pitchM2_target)
    BW_target = calc_BW(slit_target, pitchG_target, pitchM2_target)

    print("Target mono energy {0:6.2f} eV (BW {1:3.2f} eV), Cff {2:3.2f}".format(E_target, BW_target, Cff_target))
    print("RBV mono energy {0:6.2f} eV (BW {1:3.2f} eV), Cff {2:3.2f}".format(E, BW, Cff))
    print("FEL set energy {0:6.2f} eV".format(E_FEL))

    return


def move_E(E: float, pitchM2: float | None = None):
    """
    Move the mono and Vernier/undulator to specified energy.

    Arguments:  E (required) - photon energy (eV)
                pitchM2 (optional) - pre-mirror pitch (urad)
    If pre-mirror pitch is not given, then pre-mirror target PV value is used.
    Returns:    None
    Examples:   move_E(500)
                move_E(400, 140800)
    """
    if pitchM2 is None:
        pitchM2 = get_pitch_m2(rbv=False)

    pitchG, Cff = calc_pitch(E, pitchM2)

    # report current energy
    # get_E()

    print("Will do following moves:")
    print(" Grating pitch to {0:8.2f} urad, pre-mirror pitch to {1:8.2f} urad".format(pitchG, pitchM2))
    print(" FEL photon energy to {0:6.2f} eV".format(E))

    PV_pitchG = "SP1K1:MONO:MMS:G_PI"
    PV_pitchM2 = "SP1K1:MONO:MMS:M_PI"
    PV_SET1 = "RIX:USER:MCC:EPHOTK:SET1"

    # command grating pitch, pre-mirror and FEL energy moves
    res_pitchG = caput(PV_pitchG, pitchG)
    res_pitchM2 = caput(PV_pitchM2, pitchM2)
    res_photk = caput(PV_SET1, E)

    if res_pitchG != 1:
        print("Failed to write PV: " + PV_pitchG)
    if res_pitchM2 != 1:
        print("Failed to write PV: " + PV_pitchM2)
    if res_photk != 1:
        print("Failed to write PV: " + PV_SET1)


def move_E_Cff(E: float, Cff: float):
    """
    Move the mono and Vernier/undulator to specified energy.

    Arguments:  args[0] (required) - photon energy (eV)
                args[1] (required) - Cff
    Returns:    None
    Examples:   move_E(400, 1.2)
                move_E(700, 1.13)
    """
    pitchG, pitchM2 = calc_pitchCff(E, Cff)

    # report current energy
    # get_E()

    #
    print("Will do following moves:")
    print(" Grating pitch to {0:8.2f} urad, pre-mirror pitch to {1:8.2f} urad".format(pitchG, pitchM2))
    print(" FEL photon energy to {0:6.2f} eV".format(E))

    PV_pitchG = "SP1K1:MONO:MMS:G_PI"
    PV_pitchM2 = "SP1K1:MONO:MMS:M_PI"
    PV_SET1 = "RIX:USER:MCC:EPHOTK:SET1"

    res_pitchG = caput(PV_pitchG, pitchG)
    res_pitchM2 = caput(PV_pitchM2, pitchM2)
    res_photk = caput(PV_SET1, E)

    if res_pitchG != 1:
        print("Failed to write PV: " + PV_pitchG)
    if res_pitchM2 != 1:
        print("Failed to write PV: " + PV_pitchM2)
    if res_photk != 1:
        print("Failed to write PV: " + PV_SET1)


def setKScanningPVs(E=None):
    """Set the K scanning PVs to current Mono energy."""
    if E is None:
        E, cff = calc_E()

    print(f"Setting {E:.2f} eV as reference energy for K Scanning. Type 'y' to continue")
    answer = input()
    if answer.lower() not in ["y", "yes"]:
        print("Reference change aborted")
        return

    caput("RIX:USER:MCC:EPHOTK:REF1", E)
    caput("RIX:USER:MCC:EPHOTK:SET1", E)

    reference = caget_with_error("RIX:USER:MCC:EPHOTK:REF1")
    setpoint = caget_with_error("RIX:USER:MCC:EPHOTK:SET1")
    print(f"Reference RIX:USER:MCC:EPHOTK:REF1 set to {reference:.2f} eV.")
    print(f"Set point RIX:USER:MCC:EPHOTK:SET1 set to {setpoint:.2f} eV.")
