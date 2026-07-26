from typing import Annotated

from pytypehint import Pattern

# Convenience aliases, not new types: to the contract they are an ordinary
# Annotated[str, Pattern(...)], so their plan is a plain str node. They exist
# only to save every caller from repeating the pattern.

# StrWidget mirrors this exact string (COLOR_PATTERN in static/inputs.js): a str
# node whose pattern equals it, by string equality, gets a colour picker. An
# equivalent pattern written differently does not. Presentation, never contract.
COLOR_PATTERN = "#[0-9a-fA-F]{6}"

# A format filter from FuncToWeb 1.x, inside the portable RegExp subset plan_of()
# accepts. Not an email validator: it rejects RFC-valid addresses and accepts
# nonsense, and the docs say so.
EMAIL_PATTERN = r"[^@ ]+@[^@ ]+\.[a-z]{2,}"

Color = Annotated[str, Pattern(COLOR_PATTERN, message="Hex color like #ff5733")]
Email = Annotated[str, Pattern(EMAIL_PATTERN, message="An email like ana@example.com")]
