import numpy as np

from caproto import ChannelData, ChannelType
from caproto.asyncio.client import Context
from caproto.server import AsyncLibraryLayer, PVGroup, pvproperty


class Ioc_rix_sp1k1_calc(PVGroup):
    """
    ioc-rix-sp1k1-calc.
    """
    energy = pvproperty(
        value=0.0,
        name='ENERGY',
        record='ai',
        read_only=True,
        doc='Calculated SP1K1 Mono energy in eV',
        precision=3,
        units='eV',
        )

    def __init__(self, *args, **kwargs):
        self.client_context = None
        self.g_pi_pv = None
        self.m_pi_pv = None
        self.g_pi_sub = None
        self.m_pi_sub = None
        self.g_pi_value = None
        self.m_pi_value = None
        super().__init__(*args, **kwargs)

    @energy.startup
    async def value(self, instance, async_lib):
        self.client_context = Context()

        self.g_pi_pv, self.m_pi_v = await self.client_context.get_pvs(
            'SP1K1:MONO:MMS:G_PI.RBV', 'SP1K1:MONO:MMS:M_PI.RBV')

        self.g_pi_sub = self.g_pi_pv.subscribe(data_type='time')
        self.g_pi_sub.add_callback(self._g_pi_callback)

        self.m_pi_sub = self.m_pi_pv.subscribe(data_type='time')
        self.m_pi_sub.add_callback(self._m_pi_callback)


    async def _g_pi_callback(self, pv, response):
        self.g_pi_value = response.data
        await self._update_calc(response.metadata.timestamp)

    async def _m_pi_callback(self, pv, response):
        self.m_pi_value = response.data
        await self._update_calc(response.metadata.timestamp)

    async def _update_calc(self, timestamp):
        new_value = self.calculate_energy()
        await self.energy.write(new_value, timestamp=timestamp)

    def calculate_energy(self):
        if None in (self.g_pi_value, self.m_pi_value):
            return 0

        # Calculation copied from Alex Reid's email with minimal edits

        # Constants:
        D = 5e4 # ruling density in lines per meter
        c = 299792458 # speed of light
        h = 6.62607015E-34 # Plank's const
        el = 1.602176634E-19 # elemental charge
        b = 0.03662 # beam from MR1K1 design value in radians
        ex = 0.1221413 # exit trajectory design value in radians

        # Inputs:
        # grating pitch remove offset and convert to rad
        g = (self.g_pi_value - 97386)/1e6
        # pre mirror pitch remove offset and convert to rad
        p = (self.m_pi_value - 56061)/1e6

        # Calculation
        alpha = np.pi/2 - g + 2*p - b
        beta = np.pi/2 + g - ex
        # Energy in eV
        return h*c*D/(el*(np.sin(alpha)-np.sin(beta)))

