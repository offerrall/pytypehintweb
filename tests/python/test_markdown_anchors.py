"""The anchor helper itself, case by case.

`test_documentation_links.py` walks the real documentation, which proves the
links resolve but says nothing about *why* a slug came out the way it did. This
module pins the algorithm: one table of headings and the anchor GitHub gives
them, plus the heading parser and the duplicate counter.
"""

from pathlib import Path

import pytest
from markdown_anchors import Slugger, anchors, headings, plain_text, slug

# The canonical table. Each row is a heading as written in Markdown and the
# anchor GitHub renders it to. Punctuation vanishes without leaving a separator,
# spaces become hyphens and are never collapsed, `_` and `-` survive, and
# non-ASCII letters are kept.
CASES = [
    # plain words
    ("Heading", "heading"),
    ("File resolver", "file-resolver"),
    ("Read and submit values", "read-and-submit-values"),

    # the regression this helper exists for
    ("file_resolver", "file_resolver"),
    ("`file_resolver`", "file_resolver"),
    ("plan_of and decode", "plan_of-and-decode"),

    # hyphens already present
    ("Well-known", "well-known"),
    ("A float bound, choice or default is bit-identical",
     "a-float-bound-choice-or-default-is-bit-identical"),

    # inline code
    ("`decode()`", "decode"),
    ("`decode()` scope", "decode-scope"),
    ("`compileForm()`", "compileform"),
    ("`WebConfig`", "webconfig"),
    ("``a `b` c``", "a-b-c"),

    # emphasis
    ("**Bold** heading", "bold-heading"),
    ("*em* heading", "em-heading"),
    ("_em_ heading", "em-heading"),
    ("a _b_ c", "a-b-c"),

    # punctuation leaves nothing behind, not even a separator
    ("A.B (C)", "ab-c"),
    ("decode(), plan_of()", "decode-plan_of"),
    ("TypeError: expected a dataclass type",
     "typeerror-expected-a-dataclass-type"),
    ("What's new?", "whats-new"),
    ("100% done!", "100-done"),

    # a dropped character does not join the words around it
    ("HTTP / transport", "http--transport"),
    ("a / b / c", "a--b--c"),
    ("[0.0.1] - 2026-07-22", "001---2026-07-22"),

    # unicode letters survive, and are lowercased
    ("Café y té", "café-y-té"),
    ("Año", "año"),
    ("Grüße", "grüße"),

    # links and images reduce to their text
    ("[Getting started](getting-started.md)", "getting-started"),
    ("![alt](image.png) shot", "alt-shot"),

    # html is stripped, its content is not
    ("<code>x</code> y", "x-y"),

    # nothing usable left
    ("...", ""),
    ("()", ""),
]


@pytest.mark.parametrize("heading, expected", CASES,
                         ids=[heading for heading, _ in CASES])
def test_the_slug_matches_the_github_anchor(heading, expected):
    assert slug(heading) == expected


def test_plain_text_keeps_the_words_and_drops_the_markup():
    assert plain_text("**`plan_of()`** and _more_") == "plan_of() and more"


# --- duplicates -------------------------------------------------------------


def test_a_repeated_heading_is_numbered_from_one():
    slugger = Slugger()

    assert [slugger.add("Same title") for _ in range(4)] == [
        "same-title", "same-title-1", "same-title-2", "same-title-3"]


def test_headings_that_differ_only_in_punctuation_collide():
    slugger = Slugger()

    assert slugger.add("Errors") == "errors"
    assert slugger.add("Errors!") == "errors-1"


def test_distinct_headings_keep_their_own_slug():
    slugger = Slugger()

    assert [slugger.add(name) for name in ("One", "Two", "One")] == [
        "one", "two", "one-1"]


# --- the heading parser -----------------------------------------------------


def test_atx_headings_of_every_depth_are_found():
    text = "# One\n## Two\n###### Six\n"

    assert headings(text) == ["One", "Two", "Six"]


def test_a_closing_run_of_hashes_is_decoration():
    assert headings("## Two ##\n") == ["Two"]


def test_a_hash_without_a_space_is_not_a_heading():
    assert headings("#NotAHeading\n") == []


def test_setext_headings_are_found():
    text = "Title\n=====\n\nSubtitle\n--------\n"

    assert headings(text) == ["Title", "Subtitle"]


def test_a_rule_after_a_blank_line_is_not_a_setext_heading():
    assert headings("Some text\n\n-------\n") == []


def test_a_shell_comment_inside_a_fence_is_not_a_heading():
    # The bug this parser replaces: every `# …` line in a bash block became an
    # anchor, so the documentation advertised anchors that do not exist.
    text = (
        "# Real heading\n"
        "\n"
        "```bash\n"
        "# Demo with all widgets, served on port 8000\n"
        "pytypehintweb-demo\n"
        "```\n"
        "\n"
        "## Another real one\n"
    )

    assert headings(text) == ["Real heading", "Another real one"]


def test_a_tilde_fence_hides_its_contents_too():
    text = "~~~\n# not a heading\n~~~\n# a heading\n"

    assert headings(text) == ["a heading"]


def test_a_longer_fence_is_not_closed_by_a_shorter_one():
    text = "````\n```\n# still inside\n````\n# outside\n"

    assert headings(text) == ["outside"]


def test_a_setext_underline_inside_a_fence_is_ignored():
    text = "```\nTitle\n=====\n```\n"

    assert headings(text) == []


# --- against the real documentation -----------------------------------------

ROOT = Path(__file__).resolve().parents[2]


def test_the_file_resolver_anchor_exists_where_python_md_links_to_it():
    # The concrete regression: `docs/python.md` links to `#file_resolver` over a
    # `### \`file_resolver\`` heading. The previous helper deleted underscores,
    # so this link had to be written as plain text to keep the suite green.
    python = ROOT / "docs" / "python.md"

    assert "file_resolver" in anchors(python)
    assert "(#file_resolver)" in python.read_text(encoding="utf-8")


def test_no_document_offers_a_phantom_anchor_from_a_code_block():
    # Shell comments live in fences all over the documentation; none of them may
    # turn into an anchor.
    readme = ROOT / "README.md"

    assert "demo-with-all-widgets-served-by-a-local-http-server-on-port-8000" \
        not in anchors(readme)


def test_every_document_offers_at_least_one_anchor():
    empty = [path.name
             for path in [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
             if anchors(path) == set()]

    assert empty == []
