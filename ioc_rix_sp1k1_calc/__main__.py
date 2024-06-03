import textwrap
from os import environ
from pathlib import Path
from shutil import copy2

import caproto.server

from ioc_rix_sp1k1_calc import Ioc_rix_sp1k1_calc


def install_archive(pv_names):
    ioc_name = "ioc-rix-sp1k1-calc"
    archive_file = ioc_name + '.archive'
    data_dir = environ['IOC_DATA']
    if not data_dir:
        data_dir = '/reg/d/iocData'
    archive_path = Path(data_dir, ioc_name, 'archive', archive_file)
    local_archive = Path(Path(__file__).parent.parent, archive_file)
    with open(local_archive, 'w') as f:
        for pv in pv_names:
            f.write(pv + "\t30 monitor\n")
    copy2(local_archive, archive_path)


def main():
    ioc_options, run_options = caproto.server.ioc_arg_parser(
        default_prefix='SP1K1:MONO:CALC:',
        desc=textwrap.dedent(Ioc_rix_sp1k1_calc.__doc__)
    )

    ioc = Ioc_rix_sp1k1_calc(**ioc_options)
    install_archive(ioc.pvdb.keys())
    caproto.server.run(ioc.pvdb, startup_hook=ioc.__ainit__, **run_options)


if __name__ == '__main__':
    main()
