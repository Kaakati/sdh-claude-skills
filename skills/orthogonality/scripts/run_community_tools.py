#!/usr/bin/env python3
"""Detect and run community architecture tools that the project already has. Never installs.

    run_community_tools.py [--list] [--tools auto|packwerk,import-linter,...] [--base REF]
                           [--with-db] [--update-seen] [common flags]

--list prints the detection matrix (found / absent / needs-db, why, and the install command it
will not run). Database-connected tools run only with --with-db.
Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("run_community_tools", sys.argv[1:], _archrules.ALL_DETECTORS))
