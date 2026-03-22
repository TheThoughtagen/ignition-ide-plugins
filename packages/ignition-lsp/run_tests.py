#!/usr/bin/env python3
"""Run pytest using the venv Python interpreter."""
import subprocess
import sys
import os

venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
result = subprocess.run(
    [venv_python, "-m", "pytest", os.path.join(os.path.dirname(__file__), "tests"), "-v"],
    cwd=os.path.dirname(__file__),
)
sys.exit(result.returncode)
