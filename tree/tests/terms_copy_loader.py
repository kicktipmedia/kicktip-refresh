"""Test helper: import src/terms_copy.py (the single source of the banner text and the under-Run line)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from terms_copy import *   # noqa
