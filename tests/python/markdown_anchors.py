"""GitHub's heading anchors, reproduced closely enough to check our own links.

GitHub renders a heading, slugifies its *text* — not its Markdown source — and
uses the result as the `id`. Repeated slugs get `-1`, `-2` and so on, in document
order. `docs/` links to those anchors, so a checker that slugs differently
reports working links as broken; that is exactly what happened to
`#file_resolver`, whose underscore an earlier version of this helper deleted.

The rules, in the order they apply:

1. inline Markdown is reduced to the text it renders as — HTML tags, image and
   link syntax, backticks and emphasis markers all disappear, their content
   stays;
2. the text is lowercased;
3. every character that is not a letter, a digit, `_`, `-` or a space is
   removed — so `.`, `(`, `)`, `/`, `:` and friends leave nothing behind, not
   even a separator;
4. each remaining space becomes `-`. Runs are *not* collapsed: `a / b` loses the
   slash and keeps both spaces, giving `a--b`;
5. letters outside ASCII are kept as they are, so `Café` slugs to `café`;
6. a slug already used in the same document gets `-1`, then `-2`, and so on.

Known divergence: emphasis is unwrapped only when the marker sits at a word
boundary, which is the rule that keeps `file_resolver` intact. A heading that
put emphasis *inside* a word would slug differently from GitHub. No heading in
this repository does, and preserving the underscore matters more.
"""

import re
import unicodedata
from pathlib import Path

# Inline constructs, removed before slugging so the slug sees rendered text.
HTML_TAG = re.compile(r"<[^>\n]+>")
IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
CODE_SPAN = re.compile(r"`+")
ASTERISK_EMPHASIS = re.compile(r"\*+")
UNDERSCORE_OPEN = re.compile(r"(?<![0-9A-Za-z_])_+(?=\S)")
UNDERSCORE_CLOSE = re.compile(r"(?<=\S)_+(?![0-9A-Za-z_])")

# Everything a GitHub anchor drops: anything that is not a word character
# (letters in any script, digits, `_`), a hyphen or a space.
DROPPED = re.compile(r"[^\w\- ]", re.UNICODE)

ATX = re.compile(r"^ {0,3}(#{1,6})(?:\s+(.*?))?\s*$")
SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def plain_text(heading: str) -> str:
    """The text a heading renders as, with its inline Markdown removed."""
    text = heading.strip()
    text = HTML_TAG.sub("", text)
    text = IMAGE.sub(r"\1", text)
    text = LINK.sub(r"\1", text)
    text = CODE_SPAN.sub("", text)
    text = ASTERISK_EMPHASIS.sub("", text)
    text = UNDERSCORE_OPEN.sub("", text)
    text = UNDERSCORE_CLOSE.sub("", text)

    return text.strip()


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading, ignoring duplicates.

    Duplicates need document order, so they are handled by `Slugger`.
    """
    text = unicodedata.normalize("NFC", plain_text(heading)).lower()

    return DROPPED.sub("", text).replace(" ", "-")


class Slugger:
    """Slugs in document order, suffixing repeats the way GitHub does."""

    def __init__(self):
        self.seen: dict[str, int] = {}

    def add(self, heading: str) -> str:
        base = slug(heading)

        if base not in self.seen:
            self.seen[base] = 0
            return base

        self.seen[base] += 1

        return f"{base}-{self.seen[base]}"


def headings(text: str) -> list[str]:
    """Every heading in a Markdown document, in order.

    ATX (`# Heading`) and Setext (underlined with `=` or `-`) are both read.
    Fenced code blocks are skipped whole, which is what keeps a shell comment
    such as `# install this` from being mistaken for a heading.
    """
    found = []
    fence = None
    previous = ""

    for line in text.splitlines():
        if fence is not None:
            # A closing fence is the same character, at least as long, and
            # alone on its line — so a short run inside a longer block is just
            # content.
            stripped = line.strip()

            if (stripped != ""
                    and set(stripped) == {fence[0]}
                    and len(stripped) >= len(fence)):
                fence = None

            previous = ""
            continue

        opening = FENCE.match(line)

        if opening is not None:
            fence = opening.group(1)
            previous = ""
            continue

        atx = ATX.match(line)

        if atx is not None:
            # A closing run of #s is decoration, not part of the text.
            found.append(re.sub(r"\s+#+\s*$", "", atx.group(2) or ""))
            previous = ""
            continue

        if (previous.strip() != "" and SETEXT_UNDERLINE.match(line) is not None):
            found.append(previous.strip())
            previous = ""
            continue

        previous = line

    return found


def anchors(path: Path) -> set[str]:
    """Every anchor a document offers, duplicate suffixes included."""
    slugger = Slugger()

    return {slugger.add(heading)
            for heading in headings(path.read_text(encoding="utf-8"))}
