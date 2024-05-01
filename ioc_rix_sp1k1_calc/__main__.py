import textwrap

import caproto.server

from ioc_rix_sp1k1_calc import Ioc_rix_sp1k1_calc


def main():
    ioc_options, run_options = caproto.server.ioc_arg_parser(
        default_prefix='SP1K1:MONO:CALC:',
        desc=textwrap.dedent(Ioc_rix_sp1k1_calc.__doc__)
    )

    ioc = Ioc_rix_sp1k1_calc(**ioc_options)
    caproto.server.run(ioc.pvdb, startup_hook=ioc.__ainit__, **run_options)


if __name__ == '__main__':
    main()
