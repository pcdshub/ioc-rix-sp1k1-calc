"""Module for caproto IOC class."""

import sys
import traceback

from caproto import CaprotoError, ChannelData, ChannelType, ReadNotifyResponse
from caproto.asyncio.client import PV, Context
from caproto.server import PVGroup, pvproperty

from .data import SP1K1DataModel, sp1k1_pv_mapping


class Ioc_rix_sp1k1_calc(PVGroup):
    """ioc-rix-sp1k1-calc."""

    def __init__(self, *args, **kwargs):
        # Main calcs
        self.data_model = SP1K1DataModel()
        # Caproto PVs
        self.pv_attr_map: dict[str, PV] = {}
        # Flags for startup progress
        self.startup_complete = False
        self.first_calc_complete = False
        # Backwards compatibility pass-through
        self.focus_src: dict[str, PV] = {}
        super().__init__(*args, **kwargs)

    async def startup_hook(self, async_lib):
        """Initialize all source PVs used in the IOC."""
        self.client_context = Context()

        # PVs defined in the data model
        pv_objs = await self.client_context.get_pvs(*sp1k1_pv_mapping.values())
        for attr, pvo in zip(sp1k1_pv_mapping, pv_objs, strict=True):
            self.pv_attr_map[attr] = pvo

        # PV data sources for backwards compatibility
        self.focus_src["mr3k2"], self.focus_src["mr4k2"] = await self.client_context.get_pvs(
            "MR3K2:KBH:CALC:FOCUS", "MR4K2:KBV:CALC:FOCUS"
        )
        self.startup_complete = True

    update = pvproperty(name="update", value=False, record="bi")

    @update.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def update(self, instance, async_lib):
        """Read PVs, update the data model, calculate."""
        if not self.startup_complete:
            return
        for attr, pvo in self.pv_attr_map.items():
            try:
                # Note: this is slow if the external PVs are disconnected
                # This is OK because we can't have good values anyway in these cases
                res: ReadNotifyResponse = await pvo.read(data_type="control")
            except CaprotoError as exc:
                print(exc)
                continue
            if hasattr(res.metadata, "enum_strings"):
                try:
                    value = res.metadata.enum_strings[res.data[0]].decode("utf-8")
                except Exception as exc:
                    traceback.print_exception(exc)
                    continue
            else:
                value = res.data[0]
            setattr(self.data_model, attr, value)
        try:
            self.data_model.update_calcs()
        except Exception as exc:
            traceback.print_exception(exc)
        else:
            self.first_calc_complete = True

    async def update_if_type(self, instance: ChannelData, tp: type, value):
        """Update a name-matched floating point value from data model to PV."""
        if not self.first_calc_complete:
            return
        if isinstance(value, tp):
            if value == instance.value:
                return
            try:
                await instance.write(value)
            except CaprotoError as exc:
                traceback.print_exception(exc)
        else:
            print(f"Cannot use non-{tp} {value} for {instance}, skip update", file=sys.stderr)

    energy = pvproperty(
        value=0.0,
        name="ENERGY",
        record="ai",
        read_only=True,
        doc="Calculated SP1K1 Mono energy in eV",
        precision=3,
        units="eV",
    )

    @energy.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def energy(self, instance, async_lib):
        """Update energy PV with last calculated value."""
        await self.update_if_type(instance, float, self.data_model.energy)

    cff = pvproperty(
        value=0.0,
        name="CFF",
        record="ai",
        read_only=True,
        doc="Cff number",
        precision=3,
    )

    @cff.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def cff(self, instance, async_lib):
        """Update cff PV with last calculated value."""
        await self.update_if_type(instance, float, self.data_model.cff)

    bandwidth = pvproperty(
        value=0.0,
        name="BANDWIDTH",
        record="ai",
        read_only=True,
        doc="SP1K1 bandwidth in eV",
        precision=3,
        units="eV",
    )

    @bandwidth.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def bandwidth(self, instance, async_lib):
        """Update bandwidth PV with last calculated value."""
        await self.update_if_type(instance, float, self.data_model.bandwidth)

    # Backwards compatibility: no longer calculated here
    grating = pvproperty(
        value="",
        dtype=ChannelType.STRING,  # ty: ignore[invalid-argument-type]
        name="GRATING",
        record="stringin",
        read_only=True,
        doc="Which grating is in use",
    )

    @grating.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def grating(self, instance, async_lib):
        """Forward last fetched value."""
        await self.update_if_type(instance, str, self.data_model.gr_state)

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

    @mr3k2_focaldist.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def mr3k2_focaldist(self, instance, async_lib):
        """Get and forward value."""
        if not self.first_calc_complete:
            return
        try:
            res: ReadNotifyResponse = await self.focus_src["mr3k2"].read()
        except CaprotoError as exc:
            print(exc)
            return
        await self.update_if_type(instance, float, res.data[0])

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

    @mr4k2_focaldist.scan(period=2.0, use_scan_field=True)  # ty: ignore[invalid-argument-type]
    async def mr4k2_focaldist(self, instance, async_lib):
        """Get and forward value."""
        if not self.first_calc_complete:
            return
        try:
            res: ReadNotifyResponse = await self.focus_src["mr4k2"].read()
        except CaprotoError as exc:
            print(exc)
            return
        await self.update_if_type(instance, float, res.data[0])
