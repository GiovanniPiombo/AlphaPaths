# root/tests/conftest.py
import sys
import os
import pytest

#Path Resolving
core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../core'))
if core_path not in sys.path:
    sys.path.insert(0, core_path)