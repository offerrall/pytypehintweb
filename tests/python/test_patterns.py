import json
import re
from typing import Annotated

import pytest

from pytypehint import Pattern
from pytypehintweb import plan_of
from pytypehintweb.plan import _pattern_reason

UNCLOSED = [
    ("[", "unclosed character class"),
    ("[abc", "unclosed character class"),
    ("[^abc", "unclosed character class"),
    ("[a-z", "unclosed character class"),
    ("a[b", "unclosed character class"),
]

ACCEPTED = [
    ("[0-9]{4}", "brace quantifier"),
    ("[0-9]{2,}", "open brace quantifier"),
    ("[A-Z]{2}-[0-9]{3}", "literal hyphen"),
    ("[abc]", "closed character class"),
    ("[^abc]", "closed negated class"),
    ("[a-z]", "closed range class"),
    ("[\\]]", "escaped bracket inside a class"),
    ("[^@ ]+@[^@ ]+\\.[a-z]{2,}", "negated class"),
    ("a|ab", "alternation"),
    ("(?:ab)+", "non-capturing group"),
    ("\\.", "escaped metacharacter"),
    ("[.]", "dot inside a class"),
    ("\\]", "escaped closing bracket"),
    ("\\[", "escaped opening bracket"),
    ("\\{", "escaped opening brace"),
    ("\\}", "escaped closing brace"),
    ("a\\{b\\}", "escaped braces around text"),
    ("[{}]", "braces inside a class"),
    ("[\\-a]", "escaped hyphen inside a class"),
    ("\\\\a", "escaped backslash before a letter"),
    ("\\x7f", "two-digit hex escape"),
    ("\\u0061", "four-digit hex escape"),
    ("\\u20AC", "non-BMP-adjacent hex escape"),
    ("ሴ", "literal non-ASCII character"),
    ("\U0001F600", "literal astral character"),
    ("\\n", "control escape"),
    ("a*b+c?", "simple quantifiers"),
    ("(?=[a-z])[a-z]+", "positive lookahead"),
    ("(?!x)[a-z]+", "negative lookahead"),
    ("(?=[0-9]{2})[0-9]{4}", "quantified content inside a lookahead"),
    ("(?=(?:ab)+)[a-z]+", "nested group inside a lookahead"),
    ("(?=a)(b)+", "lookahead then a quantifier on a different group"),
]

REJECTED = [
    ("a{b}", "loose opening brace"),
    ("{x}", "loose opening brace"),
    ("a{,5}", "unsupported brace quantifier"),
    ("a{", "loose opening brace"),
    ("a}", "loose closing brace"),
    ("}", "loose closing brace"),
    ("a]", "loose closing bracket"),
    ("]", "loose closing bracket"),
    ("[a]]", "loose closing bracket"),
    ("[]]", "leading bracket inside a class"),
    ("[^]]", "leading bracket inside a class"),
    ("\\uD800", "high surrogate escape"),
    ("\\uDFFF", "low surrogate escape"),
    ("\\uD83D\\uDE00", "surrogate pair escape"),
    ("\\d+", "engine-dependent class"),
    ("\\w+", "engine-dependent class"),
    ("\\s", "engine-dependent class"),
    ("\\bword\\b", "word boundary"),
    ("\\Aword", "Python-only anchor"),
    ("word\\Z", "Python-only anchor"),
    ("\\N{BULLET}", "Python-only escape"),
    ("\\U0001F600", "Python-only escape"),
    ("\\a", "identity escape invalid under u"),
    ("\\_", "identity escape invalid under u"),
    ("\\-", "hyphen escape outside a class"),
    (".", "unescaped dot"),
    ("a.b", "unescaped dot"),
    ("(?:.+)", "unescaped dot"),
    ("(?P<name>[a-z]+)", "Python named group"),
    ("(?>[a-z]+)", "atomic group"),
    ("(?i)[a-z]+", "inline flags"),
    ("(?#comment)[a-z]+", "inline comment"),
    ("(?<=a)b", "lookbehind"),
    ("(?<!a)b", "negative lookbehind"),
    ("(a)(?(1)b|c)", "conditional"),
    ("[a-z]++", "possessive quantifier"),
    ("(ab)\\1", "numeric backreference"),
    ("(?=a)+", "quantified positive lookahead"),
    ("(?=a)*", "star-quantified lookahead"),
    ("(?!a)?", "optional negative lookahead"),
    ("(?=a){2}", "brace-quantified lookahead"),
    ("(?!a){1,3}", "range-quantified negative lookahead"),
]


def plan_for(pattern: str) -> dict:
    def example(value: Annotated[str, Pattern(pattern)]) -> None: ...

    return plan_of(example)


@pytest.mark.parametrize("pattern, category", ACCEPTED,
                         ids=[c for _, c in ACCEPTED])
def test_a_portable_pattern_reaches_the_plan(pattern, category):
    node = plan_for(pattern)["fields"][0]["node"]

    assert node["options"]["pattern"] == pattern


@pytest.mark.parametrize("pattern, category", REJECTED,
                         ids=[c for _, c in REJECTED])
def test_an_unportable_pattern_is_rejected_during_plan_generation(pattern,
                                                                  category):
    with pytest.raises(TypeError, match="outside the portable RegExp subset"):
        plan_for(pattern)


@pytest.mark.parametrize("pattern, category", REJECTED,
                         ids=[c for _, c in REJECTED])
def test_a_rejected_pattern_still_compiles_in_python(pattern, category):
    re.compile(pattern)


@pytest.mark.parametrize("pattern, category", UNCLOSED,
                         ids=[c for _, c in UNCLOSED])
def test_an_unclosed_character_class_is_not_portable(pattern, category):
    assert _pattern_reason(pattern) == "an unclosed character class"


@pytest.mark.parametrize("pattern, category", UNCLOSED,
                         ids=[c for _, c in UNCLOSED])
def test_the_core_also_rejects_an_unclosed_character_class(pattern, category):
    with pytest.raises(re.error, match="unterminated character set"):
        re.compile(pattern)


def test_the_core_rejects_a_reversed_brace_quantifier_before_the_adapter():
    with pytest.raises(re.error):
        re.compile("a{2,1}")


def test_the_core_rejects_an_empty_pattern_before_the_adapter():
    with pytest.raises((TypeError, ValueError)):
        Pattern("")


def test_every_accepted_pattern_builds_a_javascript_regexp(node, tmp_path):
    patterns = [pattern for pattern, _ in ACCEPTED if pattern != ""]
    path = tmp_path / "patterns.json"
    path.write_text(json.dumps(patterns), encoding="utf-8")

    result = node("check-patterns.mjs", str(path))

    assert result["checked"] == len(patterns)
    assert result["failed"] == []


def test_every_demo_pattern_builds_a_javascript_regexp(node, tmp_path):
    from pytypehintweb.demo import app

    def walk(plan_node):
        kind = plan_node.get("kind")

        if kind == "str":
            found = plan_node.get("options", {}).get("pattern")
            if found is not None:
                yield found
        elif kind == "list":
            yield from walk(plan_node["item"])
        elif kind == "object":
            for field in plan_node["fields"]:
                yield from walk(field["node"])
        elif kind == "choice":
            for branch in plan_node["branches"]:
                yield from walk(branch["node"])
        elif kind == "optional":
            yield from walk(plan_node["node"])

    patterns = sorted({
        pattern
        for section in app.PLANS
        for form in section["forms"]
        for field in form["plan"]["fields"]
        for pattern in walk(field["node"])
    })

    assert patterns != []

    path = tmp_path / "demo-patterns.json"
    path.write_text(json.dumps(patterns), encoding="utf-8")

    result = node("check-patterns.mjs", str(path))

    assert result["failed"] == []
