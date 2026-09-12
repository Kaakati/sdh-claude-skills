#!/usr/bin/env python3
"""Duplicated knowledge over the whole index: DK1-DK6 and MF3-MF5.

    find_duplicates.py [--detectors DK1,DK2,DK3,DK4,DK5,DK6,MF3,MF4,MF5]
                       [--min-jaccard 0.6] [--min-shared 4] [--min-tokens 70] [--include-tests] [common flags]

Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("find_duplicates", sys.argv[1:], _archrules.FAMILIES["duplicates"]))
