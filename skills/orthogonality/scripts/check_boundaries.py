#!/usr/bin/env python3
"""Bounded-context coupling over the whole index: BC1-BC4, MF1, and file-level cycles (FC1).

    check_boundaries.py [--detectors BC1,BC2,BC3,BC4,MF1,FC1]
                        [--contexts-source auto|packwerk|importlinter|tach|config|nx|inferred]
                        [--cycles context|file] [--graph dot|json] [common flags]

Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("check_boundaries", sys.argv[1:], _archrules.FAMILIES["boundaries"]))
