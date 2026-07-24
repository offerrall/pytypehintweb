from typing import Annotated

from pytypehint import Pattern

# Convenience aliases. Color and Email are NOT new types: to the contract they are
# an ordinary `Annotated[str, Pattern(...)]`, so the plan they produce is a plain
# str node, indistinguishable from one hand-written with the same pattern. The
# library ships them only to save every caller from repeating the pattern.

# A hex colour in #rrggbb form. This exact string is also the opt-in constant the
# StrWidget mirrors (COLOR_PATTERN in static/inputs.js): a str node whose pattern
# equals it, by string equality, gets a colour picker beside the text field. Any
# other pattern — even an equivalent one written differently — does not. That is
# widget presentation, never contract.
COLOR_PATTERN = "#[0-9a-fA-F]{6}"

# A format filter adapted from FuncToWeb 1.x ([^@ ]+@[^@ ]+\.[a-z]{2,}), kept
# inside the portable RegExp subset plan_of() accepts: a run of non-space, non-@
# characters, an @, another such run, a dot, and a suffix of two or more lowercase
# letters. It is a reasonable *format* check, not an email validator — it rejects
# plenty of RFC-valid addresses and accepts plenty of nonsense. Documented as such.
EMAIL_PATTERN = r"[^@ ]+@[^@ ]+\.[a-z]{2,}"

Color = Annotated[str, Pattern(COLOR_PATTERN, message="Hex color like #ff5733")]
Email = Annotated[str, Pattern(EMAIL_PATTERN, message="An email like ana@example.com")]
