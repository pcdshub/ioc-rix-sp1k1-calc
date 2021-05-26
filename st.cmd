#!/bin/bash
source /reg/g/pcds/pyps/conda/py36/etc/profile.d/conda.sh
conda activate pcds-4.0.1

python ioc-rix-sp1k1-calc/__main__.py --list-pvs | tee /cds/data/iocData/ioc-rix-sp1k1-calc/iocInfo/ioc.log
