"""Small helpers for reading `widgets.css` as data.

The stylesheet is the whole theme contract, so the tests read it rather than a
rendered page: a flat list of rules, the custom properties each one assigns, and
a WCAG contrast ratio from two hex values. Nothing here knows the palette — the
tests check relations and thresholds, never a specific colour.
"""

import re

from pytypehintweb import STATIC

CSS = (STATIC / "widgets.css").read_text(encoding="utf-8")

THEME_ATTRIBUTE = "data-pth-theme"
ROOT_CLASS = ".pth-root"
LIGHT_ROOT = f'[{THEME_ATTRIBUTE}="light"]'
DARK_ROOT = f'[{THEME_ATTRIBUTE}="dark"]'
AUTO_SELECTOR = (f"{ROOT_CLASS}:not([{THEME_ATTRIBUTE}])"
                 f":not([{THEME_ATTRIBUTE}] *)")
DARK_MEDIA = "@media (prefers-color-scheme: dark)"

DECLARATION = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
REFERENCE = re.compile(r"var\(\s*(--[a-z0-9-]+)")
HEX = re.compile(r"#[0-9a-f]{6}\b")
ASSET = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""")

ICONS = STATIC / "icons"


def is_asset(value):
    """True for a token value that names a file rather than holding a colour."""
    return ASSET.fullmatch(value.strip()) is not None


def asset_path(value):
    """The file a `url(...)` token points at, resolved next to the stylesheet.

    Relative URLs in CSS resolve against the stylesheet's own URL, so the same
    arithmetic applies here: `./icons/x.svg` sits beside `widgets.css`.
    """
    found = ASSET.fullmatch(value.strip())

    assert found is not None, f"not a url() value: {value!r}"

    reference = found.group(1)

    assert not reference.startswith(("/", "http:", "https:", "data:")), (
        f"{reference!r} must be relative to the stylesheet")

    return STATIC / reference


def asset(value):
    """The text of the file a `url(...)` token points at."""
    return asset_path(value).read_text(encoding="utf-8")


class Rule:
    """One declaration block, with the at-rules it sits inside."""

    def __init__(self, at_rules, prelude, body, order):
        self.at_rules = at_rules
        self.prelude = prelude
        self.body = body
        self.order = order

    @property
    def selectors(self):
        return [part.strip() for part in self.prelude.split(",")
                if part.strip()]

    @property
    def declarations(self):
        """The custom properties this rule assigns, in source order."""
        return dict(DECLARATION.findall(self.body))

    @property
    def references(self):
        """The custom properties this rule reads through `var()`."""
        return set(REFERENCE.findall(self.body))

    @property
    def in_dark_media(self):
        return DARK_MEDIA in self.at_rules

    def __repr__(self):
        return f"<Rule {self.prelude!r}>"


def _without_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def rules(text=CSS):
    """Every declaration block, flattened, in source order.

    The stylesheet nests only at-rules (`@media`), never plain rules, so a
    brace-counting scan is enough and needs no CSS parser.
    """
    text = _without_comments(text)

    found = []
    at_rules = []
    prelude = ""
    index = 0

    while index < len(text):
        character = text[index]

        if character == "{":
            head = prelude.strip()
            prelude = ""

            if head.startswith("@"):
                at_rules.append(head)
                index += 1
                continue

            end = text.index("}", index)
            found.append(Rule(tuple(at_rules), head,
                              text[index + 1:end], len(found)))
            index = end + 1
            continue

        if character == "}":
            if at_rules:
                at_rules.pop()
            prelude = ""
            index += 1
            continue

        prelude += character
        index += 1

    return found


def theme_blocks(text=CSS):
    """The four blocks that assign the active tokens, keyed by what they are.

    `auto-light` and `auto-dark` are the two halves of the automatic mode;
    `manual-light` and `manual-dark` are the `data-pth-theme` overrides.
    """
    blocks = {}

    for rule in rules(text):
        if rule.selectors == [AUTO_SELECTOR]:
            blocks["auto-dark" if rule.in_dark_media else "auto-light"] = rule
        elif rule.selectors == [LIGHT_ROOT]:
            blocks["manual-light"] = rule
        elif rule.selectors == [DARK_ROOT]:
            blocks["manual-dark"] = rule

    return blocks


def palette(text=CSS):
    """The `-light` / `-dark` palette pairs, as {stem: {"light": …, "dark": …}}."""
    values = {}

    for rule in rules(text):
        if ROOT_CLASS not in rule.selectors:
            continue

        for name, value in rule.declarations.items():
            for suffix in ("light", "dark"):
                if name.endswith(f"-{suffix}"):
                    stem = name[:-(len(suffix) + 1)]
                    values.setdefault(stem, {})[suffix] = value.strip()

    return values


def _channel(value):
    value = value / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(colour):
    """WCAG relative luminance of a `#rrggbb` string."""
    digits = colour.lstrip("#")
    red, green, blue = (int(digits[i:i + 2], 16) for i in (0, 2, 4))

    return (0.2126 * _channel(red)
            + 0.7152 * _channel(green)
            + 0.0722 * _channel(blue))


def contrast(first, second):
    """WCAG contrast ratio between two `#rrggbb` strings, 1.0 … 21.0."""
    one, other = luminance(first), luminance(second)
    lighter, darker = max(one, other), min(one, other)

    return (lighter + 0.05) / (darker + 0.05)
