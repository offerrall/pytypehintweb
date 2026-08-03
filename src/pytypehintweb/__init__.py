from pathlib import Path

from pytypehintweb.decode import decode
from pytypehintweb.plan import INLINE, PLAIN, WRAPPED, WebConfig, plan_of
from pytypehintweb.types import COLOR_PATTERN, EMAIL_PATTERN, Color, Email

STATIC = Path(__file__).parent / "static"

__version__ = "0.0.5"

__all__ = [
    "plan_of",
    "decode",
    "WebConfig",
    "STATIC",
    "PLAIN",
    "INLINE",
    "WRAPPED",
    "Color",
    "Email",
    "COLOR_PATTERN",
    "EMAIL_PATTERN",
]
