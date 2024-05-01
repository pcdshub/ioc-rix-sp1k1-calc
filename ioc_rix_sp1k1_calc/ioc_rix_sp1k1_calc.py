import importlib.util
import sys

import numpy as np

from caproto import ChannelData, ChannelType
from caproto.asyncio.client import Context
from caproto.server import AsyncLibraryLayer, PVGroup, pvproperty

DEADBAND = 0.05
DYNAMIC_PATH = "/cds/home/opr/rixopr/scripts/rix_utilities.py"
DYNAMIC_NAME = "rix_utilities"


class NoneRixDB:
    def __getattr__(self, name):
        return None


sys.modules["rix.db"] = NoneRixDB()
spec = importlib.util.spec_from_file_location(DYNAMIC_NAME, DYNAMIC_PATH)
rix_utilities = importlib.util.module_from_spec(spec)
sys.modules[DYNAMIC_NAME] = rix_utilities
spec.loader.exec_module(rix_utilities)


class Ioc_rix_sp1k1_calc(PVGroup):
    """
    ioc-rix-sp1k1-calc.
    """
    energy = pvproperty(
        value=0.0,
        name="ENERGY",
        record="ai",
        read_only=True,
        doc="Calculated SP1K1 Mono energy in eV",
        precision=3,
        units="eV",
        )
    cff = pvproperty(
        value=0.0,
        name="CFF",
        record="ai",
        read_only=True,
        doc="Cff number",
        precision=3,
        )
    bandwidth = pvproperty(
        value=0.0,
        name="BANDWIDTH",
        record="ai",
        read_only=True,
        doc="SP1K1 bandwidth in eV",
        precision=3,
        units="eV",
        )
    grating = pvproperty(
        value="",
        dtype=ChannelType.STRING,
        name="GRATING",
        record="stringin",
        read_only=True,
        doc="Which grating is in use",
        )

    def __init__(self, *args, **kwargs):
        self.g_pi_value = None
        self.m_pi_value = None
        self.exit_gap_value = None
        self.g_h_value = None
        super().__init__(*args, **kwargs)

    async def __ainit__(self, async_lib):
        """
        Set up async monitoring and callbacks of the critical mono PVs.
        """
        self.client_context = Context()

        self.g_pi_pv, self.m_pi_pv, self.exit_gap_pv, self.g_h_pv = await self.client_context.get_pvs(
            "SP1K1:MONO:MMS:G_PI.RBV",
            "SP1K1:MONO:MMS:M_PI.RBV",
            "SL1K2:EXIT:MMS:GAP.RBV",
            "SP1K1:MONO:MMS:G_H.RBV",
        )

        self.g_pi_sub = self.g_pi_pv.subscribe(data_type="time")
        self.g_pi_sub.add_callback(self._g_pi_callback)

        self.m_pi_sub = self.m_pi_pv.subscribe(data_type="time")
        self.m_pi_sub.add_callback(self._m_pi_callback)

        self.exit_gap_sub = self.exit_gap_pv.subscribe(data_type="time")
        self.exit_gap_sub.add_callback(self._exit_gap_callback)

        self.g_h_pv = self.g_h_pv.subscribe(data_type="time")
        self.g_h_pv.add_callback(self._g_h_callback)

    async def _g_pi_callback(self, pv, response):
        if self.g_pi_value is None or not np.isclose(self.g_pi_value, response.data, rtol=0, atol=DEADBAND):
            self.g_pi_value = response.data
            await self._update_energy_calc(response.metadata.timestamp)
            await self._update_bandwidth_calc(response.metadata.timestamp)

    async def _m_pi_callback(self, pv, response):
        if self.m_pi_value is None or not np.isclose(self.m_pi_value, response.data, rtol=0, atol=DEADBAND):
            self.m_pi_value = response.data
            await self._update_energy_calc(response.metadata.timestamp)
            await self._update_bandwidth_calc(response.metadata.timestamp)

    async def _exit_gap_callback(self, pv, response):
        if self.exit_gap_value is None or not np.isclose(self.exit_gap_value, response.data, rtol=0, atol=DEADBAND):
            self.exit_gap_value = response.data
            await self._update_bandwidth_calc(response.metadata.timestamp)

    async def _g_h_callback(self, pv, response):
        if self.g_h_value is None or not np.isclose(self.g_h_value, response.data, rtol=0, atol=DEADBAND):
            self.g_h_value = response.data
            await self._update_grating_calc(response.metadata.timestamp)

    async def _update_energy_calc(self, timestamp):
        new_energy, new_cff = self.calculate_energy()
        await self.energy.write(new_energy, timestamp=timestamp)
        await self.cff.write(new_cff, timestamp=timestamp)

    def calculate_energy(self) -> tuple[float, float]:
        if None in (self.g_pi_value, self.m_pi_value):
            return (0, 0)
        return rix_utilities.calc_E(self.g_pi_value, self.m_pi_value)

    async def _update_bandwidth_calc(self, timestamp):
        new_bandwidth = self.calculate_bandwidth()
        await self.bandwidth.write(new_bandwidth, timestamp=timestamp)

    def calculate_bandwidth(self) -> float:
        if None in (self.g_pi_value, self.m_pi_value, self.exit_gap_value):
            return 0
        return rix_utilities.calc_BW(self.exit_gap_value, self.g_pi_value, self.m_pi_value)

    async def _update_grating_calc(self, timestamp):
        new_grating = self.calculate_grating()
        await self.grating.write(new_grating, timestamp=timestamp)

    def calculate_grating(self) -> str:
        if self.g_h_value is None:
            return ""
        return rix_utilities.get_grating()