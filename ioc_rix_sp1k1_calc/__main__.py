import textwrap
from os import environ
from pathlib import Path

import caproto.server

from ioc_rix_sp1k1_calc import Ioc_rix_sp1k1_calc


def install_archive(pv_names):
    data_dir = environ['IOC_DATA']
    if not data_dir:
        data_dir = '/cds/data/iocData'
    ioc_name = "ioc-rix-sp1k1-calc"
    archive_path = Path(data_dir, ioc_name, 'archive', ioc_name + '.archive')
    try:
        with open(archive_path, 'w') as f:
            for pv in pv_names:
                f.write(pv + "\t30 monitor\n")
    except Exception as e:
        print(f"Unable to create archive file at {archive_path} due to {e}")


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
