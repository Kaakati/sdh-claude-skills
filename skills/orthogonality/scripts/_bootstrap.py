#!/usr/bin/env python3
"""Put the plugin's hooks/ directory on sys.path, so every script imports the one shared engine.

The engine lives in `<plugin>/hooks/_arch*.py` and is shared with the orthogonality hooks; no
detector code exists under skills/. Resolved from this file (`../../../hooks`), which stays inside
the plugin. Exits 3 with a clear message when the engine is missing (a partial install).
"""
import os
import sys

HOOKS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hooks"))

if not os.path.isfile(os.path.join(HOOKS_DIR, "_archstore.py")):
    sys.stderr.write("orthogonality: the plugin's hooks directory was not found at %s (expected _archstore.py there); "
                     "reinstall or update the sdh plugin.\n" % HOOKS_DIR)
    sys.exit(3)
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)
