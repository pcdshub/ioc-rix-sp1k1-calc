"""Module for caproto IOC class."""

import asyncio
import traceback

import numpy as np
from caproto import CaprotoError, ChannelData, ChannelType, ReadNotifyResponse
from caproto.asyncio.client import PV, Context
from caproto.server import PVGroup, pvproperty

from .data import SP1K1DataModel, sp1k1_pv_mapping


class Ioc_rix_sp1k1_calc(PVGroup):
    """Implements a caproto IOC for collecting inputs and publishing RIX mono calculation outputs."""

    def __init__(self, *args, **kwargs):
        # Main calcs
        self.data_model = SP1K1DataModel()
        # Caproto PVs
        self.pv_attr_map: dict[str, PV] = {}
        # Flags for startup progress
        self.startup_complete = False
        # Backwards compatibility pass-through
        self.focus_src: dict[str, PV] = {}
        super().__init__(*args, **kwargs)

    async def startup_hook(self, async_lib):
        """Initialize all source PVs used in the IOC."""
        self.client_context = Context()

        # PVs defined in the data model: main calculation inputs
        pv_objs = await self.client_context.get_pvs(*sp1k1_pv_mapping.values())
        for attr, pvo in zip(sp1k1_pv_mapping, pv_objs, strict=True):
            self.pv_attr_map[attr] = pvo

        # Additional PV data sources for backwards compatibility
        # Keep separate to simplify setting up pv_attr_map
        self.focus_src["mr3k2"], self.focus_src["mr4k2"] = await self.client_context.get_pvs(
            "MR3K2:KBH:CALC:FOCUS", "MR4K2:KBV:CALC:FOCUS"
        )
        self.startup_complete = True

    # energy, cff, and bandwidth are the main outputs
    # these are updated by write_calcs in the update loop.
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

    # Dummy PV just to scan the inputs
    update = pvproperty(name="update", value=False, record="bi")

    @update.scan(period=1.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def update(self, instance, async_lib):
        """
        Execute the main calc update loop.

        - Read PVs
        - Run calculation
        - Write Outputs
        """
        if not self.startup_complete:
            return
        await asyncio.gather(*(self.collect_pv_value(attr) for attr in self.pv_attr_map))
        try:
            self.data_model.update_calcs()
        except Exception as exc:
            traceback.print_exception(exc)
        await self.write_calcs()

    async def collect_pv_value(self, attr: str):
        """Get a PV value and update the data model."""
        pvo = self.pv_attr_map[attr]
        try:
            res = await pvo.read(data_type="control")
        except CaprotoError as exc:
            print(exc)
            return
        if hasattr(res.metadata, "enum_strings"):
            try:
                value = res.metadata.enum_strings[res.data[0]].decode("utf-8")
            except Exception as exc:
                traceback.print_exception(exc)
                return
        else:
            value = res.data[0]
        self.data_model.update_value(attr, value)

    async def write_calcs(self):
        """Update our output PVs from the data model."""
        try:
            await asyncio.gather(
                self.write_if_changed(self.energy, self.data_model.energy),
                self.write_if_changed(self.cff, self.data_model.cff),
                self.write_if_changed(self.bandwidth, self.data_model.bandwidth),
            )
        except Exception as exc:
            traceback.print_exception(exc)

    async def write_if_changed(self, instance: ChannelData, value):
        """If we have a new value, write it out to the PV produced here."""
        try:
            if np.isclose(value, instance.value, rtol=0, atol=0.0005):
                return
        except Exception:
            # Not handled by np.isclose
            if value == instance.value:
                return
        try:
            await instance.write(value)
        except CaprotoError as exc:
            print(exc)

    # Backwards compatibility: no longer calculated here
    grating = pvproperty(
        value="",
        dtype=ChannelType.STRING,  # ty: ignore[invalid-argument-type]
        name="GRATING",
        record="stringin",
        read_only=True,
        doc="Which grating is in use",
    )

    @grating.scan(period=5.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def grating(self, instance, async_lib):
        """
        Forward last fetched value.

        This is pulled as an input for the main calc and re-exported here as a PV.
        """
        await self.write_if_changed(instance, self.data_model.gr_state)

    # Backwards compatibility: no longer calculated here
    mr3k2_focaldist = pvproperty(
        value=0.0,
        name="MR3K2:FOCUS",
        record="ai",
        read_only=True,
        doc="MR3K2 focal distance",
        precision=3,
        units="m",
    )

    @mr3k2_focaldist.scan(period=5.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def mr3k2_focaldist(self, instance, async_lib):
        """
        Get and forward value.

        This is completely unrelated to the main IOC purpose, and has been moved to a different IOC.
        Collect the value from that other IOC and republish it here.
        """
        if not self.startup_complete:
            return
        try:
            res: ReadNotifyResponse = await self.focus_src["mr3k2"].read()
        except CaprotoError as exc:
            print(exc)
            return
        await self.write_if_changed(instance, res.data[0])

    # Backwards compatibility: no longer calculated here
    mr4k2_focaldist = pvproperty(
        value=0.0,
        name="MR4K2:FOCUS",
        record="ai",
        read_only=True,
        doc="MR4K2 focal distance",
        precision=3,
        units="m",
    )

    @mr4k2_focaldist.scan(period=5.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def mr4k2_focaldist(self, instance, async_lib):
        """
        Get and forward value.

        This is completely unrelated to the main IOC purpose, and has been moved to a different IOC.
        Collect the value from that other IOC and republish it here.
        """
        if not self.startup_complete:
            return
        try:
            res: ReadNotifyResponse = await self.focus_src["mr4k2"].read()
        except CaprotoError as exc:
            print(exc)
            return
        await self.write_if_changed(instance, res.data[0])
