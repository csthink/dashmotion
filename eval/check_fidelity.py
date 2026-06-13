#!/usr/bin/env python3
"""Shim: the canonical fidelity checker now ships inside the skill (2026-06-13)
at skills/dashmotion/scripts/check_fidelity.py so generation-time Step 6 can
run it mechanically on mermaid input. This wrapper keeps every documented
eval/test command working unchanged. Single source of truth lives in the skill copy.

Usage: python3 eval/check_fidelity.py source.mmd output.html [--json]
"""

import os
import runpy
import sys

CANONICAL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "skills", "dashmotion", "scripts",
                         "check_fidelity.py")

if not os.path.exists(CANONICAL):
    sys.exit(f"canonical fidelity checker not found: {CANONICAL}")

sys.argv[0] = CANONICAL
runpy.run_path(CANONICAL, run_name="__main__")
