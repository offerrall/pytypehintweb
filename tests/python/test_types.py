import json
from typing import Annotated

from pytypehint import Label, Pattern, signature_of

from pytypehintweb import (
    COLOR_PATTERN, EMAIL_PATTERN, Color, Email, decode, plan_of,
)


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


# --- the aliases are ordinary str nodes -------------------------------------

def test_a_color_is_a_plain_str_node():
    def f(bg: Color) -> None: ...

    node = _node(f)

    assert node["kind"] == "str"
    assert node["options"]["pattern"] == COLOR_PATTERN
    assert node["options"]["patternMessage"] == "Hex color like #ff5733"


def test_a_color_node_is_indistinguishable_from_a_hand_written_one():
    # The contract does not know Color exists: the plan it produces is byte-equal
    # to the same Annotated[str, Pattern(...)] written out by hand.
    def alias(bg: Color) -> None: ...

    def manual(bg: Annotated[str, Pattern("#[0-9a-fA-F]{6}",
                                          message="Hex color like #ff5733")]) -> None: ...

    # Compare the field (node included); only the form name differs, which is the
    # function name, not part of the type's contract.
    assert plan_of(alias)["fields"][0] == plan_of(manual)["fields"][0]


def test_an_email_is_a_plain_str_node_with_the_filter_pattern():
    def f(addr: Email) -> None: ...

    node = _node(f)

    assert node["kind"] == "str"
    assert node["options"]["pattern"] == EMAIL_PATTERN
    assert node["options"]["patternMessage"] == "An email like ana@example.com"
    # Email carries no baked Placeholder: it stays composable, so a caller can add
    # their own Label/Placeholder without a duplicate.
    assert node["options"]["placeholder"] is None


def test_the_email_pattern_passes_the_portable_scanner():
    # The whole point of adapting the 1.x filter: it must survive plan_of()'s
    # pattern scanner unchanged. If it did not, plan_of would raise here.
    def f(addr: Email) -> None: ...

    assert _node(f)["options"]["pattern"] == r"[^@ ]+@[^@ ]+\.[a-z]{2,}"


# --- composition ------------------------------------------------------------

def test_a_color_composes_with_a_field_label():
    # typing flattens the nested Annotated, so the pattern and the label both reach
    # the plan: the pattern on the node, the label on the field.
    def f(bg: Annotated[Color, Label("Fondo")]) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["label"] == "Fondo"
    assert field["node"]["kind"] == "str"
    assert field["node"]["options"]["pattern"] == COLOR_PATTERN


# --- round trips through decode() and build() -------------------------------

def test_a_color_round_trips_to_a_built_string():
    def f(bg: Color) -> None: ...

    schema = signature_of(f)
    built = schema.build(decode(schema, {"bg": "#ff5733"}))

    assert built == {"bg": "#ff5733"}
    assert type(built["bg"]) is str


def test_an_email_round_trips_to_a_built_string():
    def f(addr: Email) -> None: ...

    schema = signature_of(f)
    built = schema.build(decode(schema, {"addr": "ana@example.com"}))

    assert built == {"addr": "ana@example.com"}


def test_a_color_default_is_certified_by_the_core():
    def f(bg: Annotated[Color, Label("Fondo")] = "#ff5733") -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == "#ff5733"


# --- the JS mirror constant -------------------------------------------------

def test_the_js_mirror_constant_equals_the_python_constant(node):
    # Least-fragile pin: compare the runtime value the JS module exports against
    # the Python one, not a regex over the source. If either drifts, this fails.
    result = node("color-constant.mjs")

    assert result["colorPattern"] == COLOR_PATTERN
