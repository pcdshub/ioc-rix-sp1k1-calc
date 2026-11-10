# ioc-rix-sp1k1-calc

Calculation IOC for the RIX Monochromater.

## PVs Provided

Calculates and provides the following PVs:
- SP1K1:MONO:CALC:Energy
- SP1K1:MONO:CALC:Cff
- SP1K1:MONO:CALC:Bandwidth

This IOC used to calculate the following PVs, now it only fowards the values for backwards compatiblity with old dashboards:
- SP1K1:MONO:CALC:GRATING
- SP1K1:MONO:CALC:MR3K2:FOCUS
- SP1K1:MONO:CALC:MR4K2:FOCUS

## Operating Principles
- Every 1s, get new values from the hardware
- Take the average of the last 5 values for hardware inputs to reduce noise
- Run the same calculations as in the hutch-python
- Publish the results if they changed
