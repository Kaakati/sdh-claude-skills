#!/usr/bin/env python3
"""Competing mechanisms over the whole index: CM1-CM5 and MF2; example lint configuration.

    check_mechanisms.py [--detectors CM1,CM2,CM3,CM4,CM5,MF2] [--emit-lint-config eslint|ruff] [common flags]

--emit-lint-config prints (never writes) an ESLint no-restricted-imports block or a Ruff banned-api
table built from hooks/_mechanisms.json for the deployables in scope.
Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("check_mechanisms", sys.argv[1:], _archrules.FAMILIES["mechanisms"]))
