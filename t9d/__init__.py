"""
t9d
===
System-wide T9 predictive text input via the numpad.
"""

from .engine import T9Engine
from .app import T9App
from .config import load_config

__all__ = ["T9Engine", "T9App", "load_config"]
__version__ = "1.0.0"
