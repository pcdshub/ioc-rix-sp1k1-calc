"""
Calculations for RIX Mono (SP1K1) energy

This is shared code between rix3 and ioc-rix-sp1k1-calc

Things to keep in mind:
- Keep as close to a calculations-only module as possible
- No EPICS gets outside of functions
- Must have a way to run each calculation function without an EPICS get
- Don't change function names
- Don't import rix.db or other hutch-python-only objects

This should be copied into ioc-rix-sp1k1-calc after any necessary calculation change
"""
from epics import caget
import numpy as np
import time

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


def get_grating() -> :
    """
    Just reads the grating state PV
    """
    PV_stateG = 'SP1K1:MONO:GRATING:STATE:GET_RBV'
    try:
        temppv = EpicsSignal(PV_stateG)
        stateG = temppv.get()
        #print('Grating state RBV {0}'.format(stateG))
    except:
        print('Failed to read PV: ' + PV_stateG)

    return stateG


def calc_pitch(*args):
    '''
    Calculates the grating pitch and Cff for given photon energy and pre-mirror pitch.
    Based on Alex Reid calculator.
    Arguments:  args[0] (required) - photon energy (eV)
                args[1] (optional) - pre-mirror pitch (urad)
                If only photon energy is provided then current pre-mirror pitch is used.
    Returns:    grating pitch (urad) and Cff
    Examples:   calc_pitch(400) - calculates grating pitch corresponding to 400 eV at the current pre-mirror pitch
                calc_pitch(500, 144650) - calculates grating pitch for 500 eV and 144650 urad pre-mirror pitch
    '''

    if len(args)==1:
        E = args[0]
        PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            #print('Pre-mirror pitch RBV {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2+'.RBV')
    elif len(args)==2:
        E = args[0]
        pitchM2 = args[1]
    else:
        raise Exception('One or two arguments needed.')

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')


    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 1 # diffraction order

    pM2 = pitchM2*1e-6 - offsetM2
    a0 = dif_order*D0*eVmm/E
    pG = pM2 - 0.5*thetaM1 + 0.5*thetaES  - np.arcsin(0.5*a0/np.cos(0.5*np.pi+pM2-0.5*thetaM1-0.5*thetaES))
    alpha = np.pi/2 - pG + 2*pM2 - thetaM1
    beta = -np.pi/2 - pG + thetaES
    Cff = np.cos(beta)/np.cos(alpha)

    # grating pitch in urad
    pitchG = (pG + offsetG)*1e6

    #print('Calculated grating pitch {0:8.2f} urad, Cff {1:3.2f}'.format(pitchG, Cff))
    return pitchG, Cff

def calc_pitchCff(E, Cff):
    '''
    Calculates the grating and pre-mirror pitch for given photon energy and Cff value.
    Based on Alex Reid calculator.
    Arguments:  E (required) - photon energy (eV)
                Cff (required) - Cff value
    Returns:    grating and pre-mirror pitch (urad)
    Example:    calc_pitchCff(400, 1.2) - calculates grating and pre-mirror pitch for 400 eV and Cff 1.2
    '''

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')

    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 2 # diffraction order

    a0 = dif_order*D0*eVmm/E
    beta = -np.arccos(np.sqrt((-a0**2*Cff**2*(1+Cff**2) + 2*a0*Cff**2*np.sqrt(a0**2*Cff**2+Cff**4-2*Cff**2+1))/(Cff**4 - 2*Cff**2 + 1)))
    alpha = np.arcsin(a0 - np.sin(beta))
    pG = -beta - np.pi/2 + thetaES
    pM2 = 0.5*(alpha - np.pi/2 + pG + thetaM1)

    #
    pitchM2 = (pM2 + offsetM2)*1e6
    pitchG = (pG + offsetG)*1e6

    #print('Calculated pre-mirror pitch {0:8.2f} urad'.format(pitchM2))
    #print('Calculated grating pitch {0:8.2f} urad'.format(pitchG))
    return pitchG, pitchM2

def calc_E(*args):
    '''
    Calculates photon energy and Cff for given grating and pre-mirror pitch.
    Based on Alex Reid calculator.
    Arguments:  args[0] (optional) - grating pitch (urad)
                args[1] (optional) - pre-mirror pitch (urad)
                If grating or pre-mirror pitch are not provided then current values are used.
    Returns:    photon energy (eV) and Cff
    Examples:   calc_E() - calculates grating and pre-mirror pitch at current position, should be same as SP1K1:MONO:CALC:ENERGY
                calc_E(153650) - calculates photon energy for 153650 urad grating pitch and current pre-mirror pitch
                calc_E(153650, 140800) - calculates photon energy for 153650 urad grating pitch and 144650 urad pre-mirror pitch
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    if len(args)==0:
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            temppv = EpicsSignal(PV_pitchG)
            pitchG_target = temppv.get()
            #print('Grating pitch RBV {0:8.2f} urad, target {1:8.2f} urad'.format(pitchG, pitchG_target))
        except:
            print('Failed to read PV: ' + PV_pitchG)
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            temppv = EpicsSignal(PV_pitchM2)
            pitchM2_target = temppv.get()
            #print('Pre-mirror pitch RBV {0:8.2f} urad, target {1:8.2f} urad'.format(pitchM2, pitchM2_target))
        except:
            print('Failed to read PV: ' + PV_pitchM2)
    elif len(args)==1:
        pitchG = args[0]
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2_rbv = temppv.get()
            temppv = EpicsSignal(PV_pitchM2)
            pitchM2 = temppv.get()
            #print('Pre-mirror pitch RBV {0:8.2f} urad, target {1:8.2f} urad'.format(pitchM2, pitchM2_target))
        except:
            print('Failed to read PV: ' + PV_pitchM2)
    elif len(args)==2:
        pitchG = args[0]
        pitchM2 = args[1]
    else:
        raise Exception('Too many arguments.')

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')

    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 1 # diffraction order

    pG = pitchG*1e-6 - offsetG
    pM2 = pitchM2*1e-6 - offsetM2
    alpha = np.pi/2 - pG + 2*pM2 - thetaM1
    beta = -np.pi/2 - pG + thetaES
    E = dif_order*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    Cff = np.cos(beta)/np.cos(alpha)

    #print('Calculated photon energy {0:6.2f} eV, Cff {1:3.2f}'.format(E, Cff))
    return E, Cff

def calc_BW(*args):
    '''
    Calculates mono bandwidth (eV).
    Arguments:  args[0] (optional) - exit slit gap (um)
                args[1] (optional) - grating pitch (urad)
                args[2] (optional) - pre-mirror pitch (urad)
                If slit or grating or pre-mirror pitch are not provided then current values are used.
    Returns:    mono bandwidth (eV)
    Examples:   calc_BW() - calculates monochromator bandwidth at the current slit and mono settings
                calc_BW(0.1) - calculates monochromator bandwidth for 0.1 mm slit at the current mono setting
                calc_BW(0.1, 153650, 140800) - calculates monochromator bandwidth for 0.1 mm slit and 153650 urad grating pitch and 144650 urad pre-mirror pitch
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    PV_slit = 'SL1K2:EXIT:MMS:GAP'
    if len(args)==0:
        try:
            temppv = EpicsSignal(PV_slit+'.RBV')
            slit = temppv.get()
            print('Exit slit gap is {0:8.2f} um'.format(slit))
        except:
            print('Failed to read PV: ' + PV_slit+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            print('Grating pitch is {0:8.2f} urad'.format(pitchG))
        except:
            print('Failed to read PV: ' + PV_pitchG+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==1:
        slit = args[0]
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            print('Grating pitch is {0:8.2f} urad'.format(pitchG))
        except:
            print('Failed to read PV: ' + PV_pitchG+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==2:
        slit = args[0]
        pitchG = args[1]
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==3:
        slit = args[0]
        pitchG = args[1]
        pitchM2 = args[2]
    else:
        raise Exception('Too many arguments.')

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')

    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 1 # diffraction order
    R = 20.0e3 # mm, exit slit distance


    pG = pitchG*1e-6 - offsetG
    pM2 = pitchM2*1e-6 - offsetM2
    alpha = np.pi/2 - pG + 2*pM2 - thetaM1
    beta = -np.pi/2 - pG + thetaES
    
    #E = m*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    #Cff = np.cos(beta)/np.cos(alpha)
    ang_disp = dif_order*D0*eVmm*np.cos(beta)/(np.sin(alpha) + np.sin(beta))**2 # angular dispersion
    lin_disp = ang_disp/R # linear dispersion
    BW = (slit/1000)*lin_disp
    
    #print('Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}'.format(E, Cff))
    #print('Angular dispersion is {0:6.2f} eV/rad'.format(ang_disp))
    #print('Linear dispersion is {0:6.2f} eV/mm'.format(lin_disp))
    #print('Bandwidth is {0:6.2f} eV'.format(BW))
    return BW

def calc_grating_velocity_eV(*args):
    '''
    Calculates mono grating velocity.
    Arguments:  args[0] (optional) - grating velocity in urad (urad/sec)
                args[1] (optional) - grating pitch (urad)
                args[2] (optional) - pre-mirror pitch (urad)
                If velocity or grating or pre-mirror pitch are not provided then current values are used.
    Returns:    grating velocity (eV/sec)
    Examples:   calc_grating_velocity_eV() - calculates monochromator velocity at the current mono settings
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    PV_velocity = 'SL1K2:EXIT:MMS:G_PI.VELO'
    if len(args)==0:
        try:
            temppv = EpicsSignal(PV_velocity+'.RBV')
            velocity = temppv.get()
            print('Velocity is {0:8.2f} urad/sec'.format(velocity))
        except:
            print('Failed to read PV: ' + PV_velocity+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            print('Grating pitch is {0:8.2f} urad'.format(pitchG))
        except:
            print('Failed to read PV: ' + PV_pitchG+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==1:
        velocity = args[0]
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            print('Grating pitch is {0:8.2f} urad'.format(pitchG))
        except:
            print('Failed to read PV: ' + PV_pitchG+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==2:
        velocity = args[0]
        pitchG = args[1]
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==3:
        velocity = args[0]
        pitchG = args[1]
        pitchM2 = args[2]
    else:
        raise Exception('Too many arguments.')

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')

    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 1 # diffraction order
    #R = 20.0e3 # mm, exit slit distance


    pG = pitchG*1e-6 - offsetG
    pM2 = pitchM2*1e-6 - offsetM2
    alpha = np.pi/2 - pG + 2*pM2 - thetaM1
    beta = -np.pi/2 - pG + thetaES
    
    E = dif_order*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    Cff = np.cos(beta)/np.cos(alpha)
    ang_disp = dif_order*D0*eVmm*np.cos(beta)/(np.sin(alpha) + np.sin(beta))**2 # angular dispersion
    velocity_eV = ang_disp*velocity*1e-6
    
    print('Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}'.format(E, Cff))
    print('Angular dispersion is {0:6.2f} eV/urad'.format(ang_disp*1e-6))
    print('Velocity is {0:6.2f} eV/sec'.format(velocity_eV))
    return velocity_eV

def calc_slit(*args):
    '''
    Calculates exit slit gap (um).
    Arguments:  args[0] (required) - bandwidth (eV)
                args[1] (optional) - grating pitch (urad)
                args[2] (optional) - pre-mirror pitch (urad)
                If grating or pre-mirror pitch are not provided then current values are used.
    Returns:    gap (um)
    Examples:   calc_slit(0.1) - calculates exit slit gap for 0.1 eV bandwidth at the current mono setting
                calc_slit(0.1, 153650, 140800) - calculates exit slit gap for 0.1 eV bandwidth for 153650 urad grating pitch and 144650 urad pre-mirror pitch
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    if len(args)==1:
        BW = args[0]
        try:
            temppv = EpicsSignal(PV_pitchG+'.RBV')
            pitchG = temppv.get()
            print('Grating pitch is {0:8.2f} urad'.format(pitchG))
        except:
            print('Failed to read PV: ' + PV_pitchG+'.RBV')
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==2:
        BW = args[0]
        pitchG = args[1]
        try:
            temppv = EpicsSignal(PV_pitchM2+'.RBV')
            pitchM2 = temppv.get()
            print('Pre-mirror pitch is {0:8.2f} urad'.format(pitchM2))
        except:
            print('Failed to read PV: ' + PV_pitchM2 + '.RBV')
    elif len(args)==3:
        BW = args[0]
        pitchG = args[1]
        pitchM2 = args[2]
    else:
        raise Exception('One, two or three arguments required.')

    stateG = get_grating()
    if stateG=='LRG':
        D0 = D0_LRG
        offsetG = offsetG_LRG
    elif stateG=='LEG':
        D0 = D0_LEG
        offsetG = offsetG_LEG
    elif stateG=='MEG':
        D0 = D0_MEG
        offsetG = offsetG_MEG
    elif stateG=='HEG':
        D0 = D0_HEG
        offsetG = offsetG_HEG
    else:
        raise Exception('Horizontal position is off grating.')

    # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    #m = 2 # diffraction order
    R = 20.0e3 # mm, exit slit distance


    pG = pitchG*1e-6 - offsetG
    pM2 = pitchM2*1e-6 - offsetM2
    alpha = np.pi/2 - pG + 2*pM2 - thetaM1
    beta = -np.pi/2 - pG + thetaES
    
    #E = m*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    #Cff = np.cos(beta)/np.cos(alpha)
    ang_disp = dif_order*D0*eVmm*np.cos(beta)/(np.sin(alpha) + np.sin(beta))**2 # angular dispersion
    lin_disp = ang_disp/R # linear dispersion
    slit = BW/lin_disp
    
    #print('Calculated photon energy is {0:6.2f} eV, Cff is {1:3.2f}'.format(E, Cff))
    #print('Angular dispersion is {0:6.2f} eV/rad'.format(ang_disp))
    #print('Linear dispersion is {0:6.2f} eV/mm'.format(lin_disp))
    #print('Exit slit gap {0:6.2f} eV'.format(BW))
    return slit*1000

def calc_slitE(*args):
    '''
    Calculates exit slit gap (um).
    Arguments:  args[0] (required) - bandwidth (eV)
                args[1] (required) - photon energy (eV)
                args[2] (required) - Cff value
    Returns:   gap (um)
    Examples:  calc_slitE(0.1, 400, 1.2) - calculates exit slit gap for 0.1 eV bandwidth at 400 eV and 1.2 Cff
    '''

    BW = args[0]
    E = args[1]
    Cff = args[2]

    pitchG, pitchM2 = calc_pitchCff(E, Cff)
    slit = calc_slit(BW, pitchG, pitchM2)

    return slit

def get_E():
    '''
    Reports current photon energy and Cff for based on current grating and pre-mirror pitch target and RBV.
    Reports mono bandwidth based on the exit slit gap.
    Reports the FEL set energy.
    Arguments: none
    Returns:   none
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    PV_slit = 'SL1K2:EXIT:MMS:GAP'
    PV_SET1 = 'RIX:USER:MCC:EPHOTK:SET1'

    try:
        temppv = EpicsSignal(PV_pitchG+'.RBV')
        pitchG = temppv.get()
    except:
        print('Failed to read PV: ' + PV_pitchG+'.RBV')
    try:
        temppv = EpicsSignal(PV_pitchG)
        pitchG_target = temppv.get()
    except:
        print('Failed to read PV: ' + PV_pitchG)
    try:
        temppv = EpicsSignal(PV_pitchM2+'.RBV')
        pitchM2 = temppv.get()
    except:
        print('Failed to read PV: ' + PV_pitchM2+'.RBV')
    try:
        temppv = EpicsSignal(PV_pitchM2)
        pitchM2_target = temppv.get()
    except:
        print('Failed to read PV: ' + PV_pitchM2)
    try:
        temppv = EpicsSignal(PV_slit+'.RBV')
        slit = temppv.get()
    except:
        print('Failed to read PV: ' + PV_slit+'.RBV')
    try:
        temppv = EpicsSignal(PV_slit)
        slit_target = temppv.get()
    except:
        print('Failed to read PV: ' + PV_slit)

    try:
        temppv = EpicsSignal(PV_SET1)
        E_FEL = temppv.get()
    except:
        print('Failed to read PV: ' + PV_SET1)

    print('Grating pitch RBV {0:8.2f} urad, target {1:8.2f} urad'.format(pitchG, pitchG_target))
    print('Pre-mirror pitch RBV {0:8.2f} urad, target {1:8.2f} urad'.format(pitchM2, pitchM2_target))
    print('Exit slit gap RBV {0:3.2f} um, target {1:3.2f} um'.format(slit, slit_target))

    # RBV
    E, Cff = calc_E(pitchG, pitchM2)
    BW = calc_BW(slit, pitchG, pitchM2)

    # target
    E_target, Cff_target = calc_E(pitchG_target, pitchM2_target)
    BW_target = calc_BW(slit_target, pitchG_target, pitchM2_target)

    print('Target mono energy {0:6.2f} eV (BW {1:3.2f} eV), Cff {2:3.2f}'.format(E_target, BW_target, Cff_target))
    print('RBV mono energy {0:6.2f} eV (BW {1:3.2f} eV), Cff {2:3.2f}'.format(E, BW, Cff))
    print('FEL set energy {0:6.2f} eV'.format(E_FEL))

    return

def move_E(*args):
    '''
    Moves the mono and Vernier/undulator to specified energy.
    Arguments:  args[0] (required) - photon energy (eV)
                args[1] (optional) - pre-mirror pitch (urad)
    If pre-mirror pitch is not given, then pre-mirror target PV value is used.
    Returns:    None
    Examples:   move_E(500)
                move_E(400, 140800)
    '''

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    PV_SET1 = 'RIX:USER:MCC:EPHOTK:SET1'

    if len(args)==1:
        E = args[0]
        try:
            temppv = EpicsSignal(PV_pitchM2)
            pitchM2 = temppv.get()
        except:
            print('Failed to read PV: ' + PV_pitchM2)
    elif len(args)==2:
        E = args[0]
        pitchM2 = args[1]
    else:
        raise Exception('One or two arguments needed.')

    pitchG, Cff = calc_pitch(E, pitchM2)

    # report current energy
    #get_E()

    #
    print('Will do following moves:')
    print(' Grating pitch to {0:8.2f} urad, pre-mirror pitch to {1:8.2f} urad'.format(pitchG, pitchM2))
    print(' FEL photon energy to {0:6.2f} eV'.format(E))

    # command grating pitch, pre-mirror and FEL energy moves
    try:
        temppv = EpicsSignal(PV_pitchG)
        tempval = temppv.put(pitchG)
    except:
        print('Failed to write PV: ' + PV_pitchG)
    try:
        temppv = EpicsSignal(PV_pitchM2)
        tempval = temppv.put(pitchM2)
    except:
        print('Failed to write PV: ' + PV_pitchM2)
    try:
        temppv = EpicsSignal(PV_SET1)
        tempval = temppv.put(E)
    except:
        print('Failed to write PV: ' + PV_SET1)

    return

def move_E_Cff(*args):
    '''
    Moves the mono and Vernier/undulator to specified energy.
    Arguments:  args[0] (required) - photon energy (eV)
                args[1] (required) - Cff
    Returns:    None
    Examples:   move_E(400, 1.2)
                move_E(700, 1.13)
    '''

    if len(args)==2:
        E = args[0]
        Cff = args[1]
        pitchG, pitchM2 = calc_pitchCff(E, Cff)
    else:
        raise Exception('Two arguments needed.')

    PV_pitchG = 'SP1K1:MONO:MMS:G_PI'
    PV_pitchM2 = 'SP1K1:MONO:MMS:M_PI'
    PV_SET1 = 'RIX:USER:MCC:EPHOTK:SET1'

    # report current energy
    #get_E()
    
    #
    print('Will do following moves:')
    print(' Grating pitch to {0:8.2f} urad, pre-mirror pitch to {1:8.2f} urad'.format(pitchG, pitchM2))
    print(' FEL photon energy to {0:6.2f} eV'.format(E))

    try:
        temppv = EpicsSignal(PV_pitchG)
        tempval = temppv.put(pitchG)
    except:
        print('Failed to write PV: ' + PV_pitchG)

    try:
        temppv = EpicsSignal(PV_pitchM2)
        tempval = temppv.put(pitchM2)
    except:
        print('Failed to write PV: ' + PV_pitchM2)
    try:
        temppv = EpicsSignal(PV_SET1)
        tempval = temppv.put(E)
    except:
        print('Failed to write PV: ' + PV_SET1)

    return

def setKScanningPVs(E=None):
    '''
    Sets the K scanning PVs to current Mono energy
    '''
    if E is None:
        E,cff = calc_E()
    
    print(f"Setting {E:.2f} eV as reference energy for K Scanning. Type 'y' to continue")
    answer = input()
    if answer.lower() not in ["y","yes"]:
        print('Reference change aborted')
        return
    
    EpicsSignal('RIX:USER:MCC:EPHOTK:REF1').put(E)
    EpicsSignal('RIX:USER:MCC:EPHOTK:SET1').put(E)

    reference = EpicsSignal('RIX:USER:MCC:EPHOTK:REF1').get()
    setpoint = EpicsSignal('RIX:USER:MCC:EPHOTK:SET1').get()
    print(f"Reference RIX:USER:MCC:EPHOTK:REF1 set to {reference:.2f} eV.")
    print(f"Set point RIX:USER:MCC:EPHOTK:SET1 set to {setpoint:.2f} eV.")
    return

