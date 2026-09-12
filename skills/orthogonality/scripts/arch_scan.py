#!/usr/bin/env python3
"""The orthogonality orchestrator: refresh, every detector (scan-only ones included), community
tools on request, baseline management and reports. The same command runs in CI.

    arch_scan.py [--detectors ...] [--changed-since REF] [--new-only] [--fail-on warn|info|never]
                 [--tools [auto|list]] [--with-db] [--update-seen]
                 [--update-baseline --reason TEXT] [--baseline-report]
                 [--format json|markdown|brief|sarif-lite] [--write-report] [common flags]

Thin wrapper: every behaviour lives in hooks/_archcli.py and the shared _arch* engine.
"""
import sys

import _bootstrap  # noqa: F401  puts <plugin>/hooks on sys.path
import _archcli
import _archrules

if __name__ == "__main__":
    sys.exit(_archcli.main("arch_scan", sys.argv[1:], _archrules.ALL_DETECTORS))
