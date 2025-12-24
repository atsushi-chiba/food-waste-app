# Ensure the `python/` package directory is on sys.path when running tests from repository root
import os
import sys

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
