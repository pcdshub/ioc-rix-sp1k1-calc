#!/bin/bash
unset PYTHONPATH
.pixi/envs/default/bin/ioc-rix-sp1k1-calc --list-pvs | tee /cds/data/iocData/ioc-rix-sp1k1-calc/iocInfo/ioc.log
