#!/bin/bash
unset PYTHONPATH
source /reg/g/pcds/pyps/conda/py39/etc/profile.d/conda.sh
conda activate pcds-5.8.4

python ioc_rix_sp1k1_calc/__main__.py --list-pvs | tee /cds/data/iocData/ioc-rix-sp1k1-calc/iocInfo/ioc.log
