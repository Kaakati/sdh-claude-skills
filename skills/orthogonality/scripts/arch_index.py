#!/usr/bin/env python3
"""Build, refresh or inspect the orthogonality index; look a concept up before adding a model or table.

    arch_index.py [--refresh | --rebuild | --status [--require-complete]]
                  [--show models|tables|contexts|mechanisms|graph|coverage] [--name NAME] [common flags]

Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("arch_index", sys.argv[1:], _archrules.ALL_DETECTORS))
