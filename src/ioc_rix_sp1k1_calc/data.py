"""
Data models and PV mappings for the mono IOC.

Intentionally IOC backend independent.
"""

from dataclasses import dataclass

import numpy as np

from .rix_mono_calcs import (
    raw_calc_alpha_beta,
    raw_calc_bandwidth,
    raw_calc_cff,
    raw_calc_energy,
    select_base_offset,
    select_D0,
)


@dataclass
class SP1K1DataModel:
    """
    Data model for SP1K1 IOC.

    This can be used robustly in 1-3 scan loops:
    - get new values for the PV inputs
    - call update_value for each
    - run update_calcs
    - update output PVs
    """

    # Mono PVs
    gr_pitch: float = 0
    m2_pitch: float = 0
    slit_gap: float = 0
    gr_state: str = ""

    # Notepad PVs
    m2_dyn_offset: float = 0
    lrg_dyn_offset: float = 0
    leg_dyn_offset: float = 0
    meg_dyn_offset: float = 0
    heg_dyn_offset: float = 0
    dif_order: int = 1

    # Calculation Results
    energy: float = 0.0
    cff: float = 0.0
    bandwidth: float = 0.0

    # Settings
    buffer_size: int = 5

    def __post_init__(self):
        """Initialize buffers for rolling averages of noisy inputs."""
        self.buffers: dict[str, list[float]] = {"gr_pitch": [], "m2_pitch": [], "slit_gap": []}

    def update_value(self, attr: str, value: float | int | str):
        """Update a value, and for buffered values use a rolling average."""
        if attr in self.buffers:
            if isinstance(value, float):
                self.buffers[attr].append(value)
                while len(self.buffers[attr]) > self.buffer_size:
                    self.buffers[attr].pop(0)
                setattr(self, attr, float(np.mean(self.buffers[attr])))
            else:
                raise TypeError(f"Expected float for {attr}, got {value}")
        else:
            setattr(self, attr, value)

    def update_calcs(self):
        """Run calculations on the input fields to set the results."""
        match self.gr_state:
            case "LRG":
                gr_dyn_offset = self.lrg_dyn_offset
            case "LEG":
                gr_dyn_offset = self.leg_dyn_offset
            case "MEG":
                gr_dyn_offset = self.meg_dyn_offset
            case "HEG":
                gr_dyn_offset = self.heg_dyn_offset
            case _:
                raise ValueError(f"Invalid grating state {self.gr_state}, must be one of LRG, LEG, MEG, HEG.")
        offsetG = gr_dyn_offset + select_base_offset(self.gr_state)
        offsetM2 = self.m2_dyn_offset + select_base_offset(name="M2")
        alpha, beta = raw_calc_alpha_beta(
            pitchG=self.gr_pitch,
            pitchM2=self.m2_pitch,
            offsetG=offsetG,
            offsetM2=offsetM2,
        )
        D0 = select_D0(self.gr_state)
        self.energy = raw_calc_energy(alpha=alpha, beta=beta, dif_order=self.dif_order, D0=D0)
        self.cff = raw_calc_cff(alpha=alpha, beta=beta)
        self.bandwidth = raw_calc_bandwidth(
            alpha=alpha, beta=beta, dif_order=self.dif_order, D0=D0, slit_gap=self.slit_gap
        )


sp1k1_pv_mapping = {
    # Mono PVs
    "gr_pitch": "SP1K1:MONO:MMS:G_PI.RBV",
    "m2_pitch": "SP1K1:MONO:MMS:M_PI.RBV",
    "slit_gap": "SL1K2:EXIT:MMS:GAP.RBV",
    "gr_state": "SP1K1:MONO:GRATING:STATE:GET_RBV",
    # Notepad PVs
    "m2_dyn_offset": "SP1K1:MONO:CALC:M2_OFFSET",
    "lrg_dyn_offset": "SP1K1:MONO:CALC:LRG_OFFSET",
    "leg_dyn_offset": "SP1K1:MONO:CALC:LEG_OFFSET",
    "meg_dyn_offset": "SP1K1:MONO:CALC:MEG_OFFSET",
    "heg_dyn_offset": "SP1K1:MONO:CALC:HEG_OFFSET",
    "dif_order": "SP1K1:MONO:CALC:DIF_ORDER",
}
