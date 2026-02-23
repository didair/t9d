"""
t9d
=========
System-wide T9 predictive text input via the numpad.

Public API
----------
    from t9d import T9Engine, t9d, load_config

    config = load_config()
    engine = T9Engine(config)
    engine.push_digit("4")
    engine.push_digit("6")
    engine.push_digit("6")
    engine.push_digit("3")
    print(engine.candidates)   # ['home', 'hone', 'gone', ...]
"""

from .engine import T9Engine
from .app import t9d
from .config import load_config

__all__ = ["T9Engine", "t9d", "load_config"]
__version__ = "1.0.0"