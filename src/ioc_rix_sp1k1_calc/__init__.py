"""Launcher for the server."""

from os import environ
from pathlib import Path

import caproto.server

from .ioc_rix_sp1k1_calc import Ioc_rix_sp1k1_calc


def install_archive(pv_names):
    """Update the archive request file."""
    data_dir = environ["IOC_DATA"]
    if not data_dir:
        data_dir = "/cds/data/iocData"
    ioc_name = "ioc-rix-sp1k1-calc"
    archive_path = Path(data_dir, ioc_name, "archive", ioc_name + ".archive")
    try:
        with open(archive_path, "w") as f:
            for pv in pv_names:
                f.write(pv + "\t30 monitor\n")
    except Exception as e:
        print(f"Unable to create archive file at {archive_path} due to {e}")


def main():
    """Run the server process."""
    default_prefix = "SP1K1:MONO:CALC:"
    ioc_options, run_options = caproto.server.ioc_arg_parser(
        default_prefix=default_prefix,
        desc="SP1K1 Calc IOC",
    )

    ioc = Ioc_rix_sp1k1_calc(**ioc_options)
    if ioc_options["prefix"] == default_prefix:
        install_archive(ioc.pvdb.keys())
    caproto.server.run(ioc.pvdb, startup_hook=ioc.startup_hook, **run_options)  # ty: ignore[invalid-argument-type]
