"""Pytest configuration for ReEngrave backend tests."""

import sys
import os

# Add the backend directory to sys.path so modules can be imported directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
