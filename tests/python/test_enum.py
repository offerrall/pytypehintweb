import json
from enum import Enum
from typing import Annotated

import pytest

from pytypehint import EnumShape, Label, signature_of
from pytypehintweb import decode, plan_of
from pytypehintweb.plan import _check_branches


class Estado(Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    EN_PROCESO = "en_proceso"


class Prioridad(Enum):
    BAJA = 1
    MEDIA = 2
    ALTA = 3


class Aliased(Enum):
    A = 1
    B = 1  # an alias of A: list(Aliased) never yields it


def _sig(fn):
    return signature_of(fn)


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


# --- the enum node ----------------------------------------------------------

def test_plan_of_emits_an_enum_node():
    def f(value: Estado) -> None: ...

    assert _node(f) == {
        "kind": "enum",
        "options": {
            "choices": ["ACTIVO", "INACTIVO", "EN_PROCESO"],
            "placeholder": None,
            "labels": None,
        },
    }


def test_choices_preserve_declaration_order_and_use_names_not_values():
    def f(value: Prioridad) -> None: ...

    # Names in declaration order, never the values (1, 2, 3).
    assert _node(f)["options"]["choices"] == ["BAJA", "MEDIA", "ALTA"]


def test_an_alias_never_appears_in_the_choices():
    def f(value: Aliased) -> None: ...

    # list(cls) yields only canonical members, so the alias B is absent.
    assert _node(f)["options"]["choices"] == ["A"]


def test_an_enum_default_travels_as_the_member_name():
    def f(value: Annotated[Estado, Label("s")] = Estado.EN_PROCESO) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == "EN_PROCESO"


# --- union transport (string group) -----------------------------------------

def test_str_and_enum_collide_on_the_wire_and_travel_wrapped():
    def f(value: str | Estado) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"str": "wrapped", "Estado": "wrapped"}


def test_two_enums_collide_and_travel_wrapped_by_class_name():
    def f(value: Estado | Prioridad) -> None: ...

    node = _node(f)
    modes = {b["value"]: b["mode"] for b in node["branches"]}

    # option_id() of an enum is its class name, so that is the $type discriminator.
    assert modes == {"Estado": "wrapped", "Prioridad": "wrapped"}


def test_date_and_enum_collide_and_travel_wrapped():
    from datetime import date

    def f(value: date | Estado) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"date": "wrapped", "Estado": "wrapped"}


def test_enum_and_int_are_distinct_groups_and_stay_plain():
    def f(value: Estado | int) -> None: ...

    # An enum travels as a string, an int as a number: distinct groups, no wrapper.
    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"Estado": "plain", "int": "plain"}


def test_two_enums_with_the_same_class_name_are_rejected_by_the_core():
    # Since pytypehint 0.0.5 the core's _check_discriminators covers
    # _DISCRIMINATED = (Struct, EnumShape), so it rejects two same-named enum
    # classes in a union at compile time: the class name is the wrapper's $type
    # discriminator, and two "Estado" would be unroutable. It raises in
    # signature_of, before the adapter's own _check_branches (the defense-in-depth
    # guard exercised directly by the next test) ever runs on this path.
    E1 = Enum("Estado", {"A": 1, "B": 2})
    E2 = Enum("Estado", {"X": 1, "Y": 2})

    def f(value: E1 | E2) -> None: ...

    with pytest.raises(ValueError, match="duplicate discriminator name"):
        signature_of(f)


def test_check_branches_still_rejects_two_homonym_enum_shapes():
    # The adapter's option-id guard survives as defense in depth. The core now
    # makes the homonym-enum union inconstructible via the normal Field path (the
    # test above), so to reach _check_branches we hand it two EnumShape built
    # straight from homonym classes — the core's public shape API, no Field in
    # between. Both option_id() to "Estado", so the guard refuses them, pinning
    # that it stays live against future core relaxations and shapes assembled off
    # the normal path.
    E1 = Enum("Estado", {"A": 1, "B": 2})
    E2 = Enum("Estado", {"X": 1, "Y": 2})

    left, right = EnumShape(cls=E1), EnumShape(cls=E2)
    assert left.option_id() == right.option_id() == "Estado"

    with pytest.raises(TypeError, match="share the option id"):
        _check_branches([left, right], "fields.value")


# --- decode: name -> member -------------------------------------------------

def test_a_name_is_rebuilt_into_a_member_at_the_root():
    def f(value: Estado) -> None: ...

    result = decode(_sig(f), {"value": "ACTIVO"})

    assert result == {"value": Estado.ACTIVO}
    assert type(result["value"]) is Estado


def test_names_are_rebuilt_inside_a_list():
    def f(value: list[Estado]) -> None: ...

    result = decode(_sig(f), {"value": ["ACTIVO", "EN_PROCESO"]})

    assert result == {"value": [Estado.ACTIVO, Estado.EN_PROCESO]}
    assert all(type(v) is Estado for v in result["value"])


def test_the_enum_branch_of_a_wrapper_is_rebuilt_and_the_str_branch_kept():
    def f(value: str | Estado) -> None: ...

    schema = _sig(f)

    rebuilt = decode(schema, {"value": {"$type": "Estado", "$value": "ACTIVO"}})
    assert rebuilt == {"value": Estado.ACTIVO}
    assert type(rebuilt["value"]) is Estado

    # A str that matches a member name stays a str: the $type says str.
    kept = decode(schema, {"value": {"$type": "str", "$value": "ACTIVO"}})
    assert kept == {"value": "ACTIVO"}
    assert type(kept["value"]) is str


def test_an_alias_name_resolves_to_its_canonical_member():
    def f(value: Aliased) -> None: ...

    # cls["B"] resolves through __members__ to the canonical member A. A producer
    # that sends an alias name gets the member the alias points at.
    result = decode(_sig(f), {"value": "B"})

    assert result == {"value": Aliased.A}
    assert type(result["value"]) is Aliased


def test_a_name_that_is_not_a_member_passes_through_untouched():
    def f(value: Estado) -> None: ...

    # decode prepares, it does not validate: an unknown name is left for build().
    assert decode(_sig(f), {"value": "NOPE"}) == {"value": "NOPE"}


def test_decode_never_guesses_a_member_from_a_plain_str_field():
    def f(value: str) -> None: ...

    # A str field is a str, even when the content is a member name.
    result = decode(_sig(f), {"value": "ACTIVO"})
    assert result == {"value": "ACTIVO"}
    assert type(result["value"]) is str


def test_the_core_rejects_the_string_group_wrapper_directly():
    # Pin the core's behaviour: it routes str/enum by exact Python type and has
    # no wrapper for them, so a raw wrapper is rejected. decode must unwrap it.
    def f(value: str | Estado) -> None: ...

    schema = _sig(f)

    with pytest.raises(Exception):
        schema.build({"value": {"$type": "Estado", "$value": "ACTIVO"}})


# --- the star round trip through the browser --------------------------------

def _star(node_fixture, tmp_path, fn, name):
    plan = plan_of(fn)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node_fixture("enum-star-runner.mjs", str(path), name)
    return result["read"]


def test_a_picked_member_builds_the_exact_python_member(node, tmp_path):
    def f(value: Annotated[Estado, Label("Status")]) -> None: ...

    read = _star(node, tmp_path, f, "EN_PROCESO")
    assert read["value"] == "EN_PROCESO"

    schema = _sig(f)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built == {"value": Estado.EN_PROCESO}
    assert type(built["value"]) is Estado
