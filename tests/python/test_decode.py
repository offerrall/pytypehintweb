import json
from dataclasses import dataclass
from datetime import date, time
from enum import Enum
from typing import Annotated

import pytest

from pytypehint import Label, Min, signature_of, struct_of
from pytypehintweb import decode, plan_of


def _sig(fn):
    return signature_of(fn)


class Estado(Enum):
    A = "a"
    B = "b"


def test_int_is_coerced_to_float_at_the_root():
    def f(value: float) -> None: ...

    schema = _sig(f)

    assert decode(schema, {"value": 3}) == {"value": 3.0}
    assert type(decode(schema, {"value": 3})["value"]) is float


def test_a_real_float_passes_untouched():
    def f(value: float) -> None: ...

    assert decode(_sig(f), {"value": 3.5}) == {"value": 3.5}


def test_int_is_coerced_inside_a_nested_object():
    @dataclass
    class P:
        x: Annotated[float, Label("x")]
        y: Annotated[int, Label("y")]

    def f(p: Annotated[P, Label("p")]) -> None: ...

    result = decode(_sig(f), {"p": {"x": 3, "y": 5}})

    assert result == {"p": {"x": 3.0, "y": 5}}
    assert type(result["p"]["x"]) is float
    assert type(result["p"]["y"]) is int


def test_int_is_coerced_inside_a_list():
    def f(value: list[float]) -> None: ...

    result = decode(_sig(f), {"value": [1, 2, 3]})

    assert result == {"value": [1.0, 2.0, 3.0]}
    assert all(type(v) is float for v in result["value"])


def test_int_is_coerced_inside_a_nested_list():
    def f(value: list[list[float]]) -> None: ...

    result = decode(_sig(f), {"value": [[1, 2], [3]]})

    assert result == {"value": [[1.0, 2.0], [3.0]]}


def test_the_float_branch_of_a_wrapper_is_coerced_and_unwrapped():
    def f(value: int | float) -> None: ...

    result = decode(_sig(f), {"value": {"$type": "float", "$value": 3}})

    # The wrapper is consumed: $type becomes the real type, the payload a bare
    # float the core routes by exact type.
    assert result == {"value": 3.0}
    assert type(result["value"]) is float


def test_the_int_branch_of_a_wrapper_keeps_the_integer():
    def f(value: int | float) -> None: ...

    result = decode(_sig(f), {"value": {"$type": "int", "$value": 3}})

    assert result == {"value": 3}
    assert type(result["value"]) is int


def test_a_wrapper_the_core_keeps_is_preserved_and_its_payload_prepared():
    def f(value: list[float] | list[int]) -> None: ...

    result = decode(_sig(f), {"value": {"$type": "list[float]", "$value": [1, 2]}})

    # list | list is a genuine collision the core keeps wrapped, so decode
    # leaves the wrapper and only coerces inside $value.
    assert result == {"value": {"$type": "list[float]", "$value": [1.0, 2.0]}}


def test_a_none_passes_through_untouched():
    def f(value: Annotated[float, Label("x")] | None) -> None: ...

    assert decode(_sig(f), {"value": None}) == {"value": None}


def test_an_invalid_value_passes_through_without_touching_or_raising():
    def f(value: float) -> None: ...

    # decode prepares, it does not validate: a string in a float field is the
    # core's to reject, later, with its own error.
    assert decode(_sig(f), {"value": "abc"}) == {"value": "abc"}
    assert decode(_sig(f), {"value": True}) == {"value": True}


def test_an_unknown_key_travels_intact():
    def f(value: float) -> None: ...

    assert decode(_sig(f), {"value": 3, "extra": 9}) == {"value": 3.0, "extra": 9}


def test_the_input_is_never_mutated():
    def f(value: list[float]) -> None: ...

    data = {"value": [1, 2, 3]}
    decode(_sig(f), data)

    assert data == {"value": [1, 2, 3]}
    assert all(type(v) is int for v in data["value"])


def test_a_dict_with_no_floats_comes_out_equal():
    def f(name: str, age: int, tags: list[str]) -> None: ...

    data = {"name": "a", "age": 5, "tags": ["x", "y"]}
    result = decode(_sig(f), data)

    assert result == data
    assert result is not data


def test_decode_works_on_a_struct_schema():
    @dataclass
    class Box:
        size: Annotated[float, Label("size")]

    result = decode(struct_of(Box), {"size": 4})

    assert result == {"size": 4.0}
    assert type(result["size"]) is float


def test_decode_rejects_a_schema_that_is_not_a_signature_or_struct():
    with pytest.raises(TypeError, match="Signature or Struct"):
        decode(object(), {})


def test_the_star_round_trip_builds_a_float_from_typed_text(node, tmp_path):
    # "3" typed -> read() -> JSON -> parse -> decode -> build -> 3.0 (float).
    def f(value: Annotated[float, Label("Amount")]) -> None: ...

    schema = _sig(f)
    plan = plan_of(f)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node("float-star-runner.mjs", str(path), "3")
    read = result["read"]

    # read() reports a plain JS number; across JSON it lands as a Python int.
    transported = json.loads(json.dumps(read))
    assert type(transported["value"]) is int
    assert transported["value"] == 3

    built = schema.build(decode(schema, transported))

    assert built == {"value": 3.0}
    assert type(built["value"]) is float


# --- date/time preparation --------------------------------------------------

def test_an_iso_string_is_converted_to_a_date_at_the_root():
    def f(value: date) -> None: ...

    result = decode(_sig(f), {"value": "2026-07-22"})

    assert result == {"value": date(2026, 7, 22)}
    assert type(result["value"]) is date


def test_an_iso_string_is_converted_to_a_time_with_seconds():
    def f(value: time) -> None: ...

    result = decode(_sig(f), {"value": "14:30:05"})

    assert result == {"value": time(14, 30, 5)}


def test_iso_strings_are_converted_inside_a_nested_object_and_a_list():
    @dataclass
    class Slot:
        day: Annotated[date, Label("day")]
        note: Annotated[str, Label("note")]

    def f(slot: Annotated[Slot, Label("s")], days: list[date]) -> None: ...

    result = decode(_sig(f), {
        "slot": {"day": "2026-07-22", "note": "2026-07-22"},
        "days": ["2026-01-01", "2026-12-31"],
    })

    assert result["slot"]["day"] == date(2026, 7, 22)
    # A str field keeps its string even when the string looks like a date.
    assert result["slot"]["note"] == "2026-07-22"
    assert type(result["slot"]["note"]) is str
    assert result["days"] == [date(2026, 1, 1), date(2026, 12, 31)]


def test_the_date_branch_of_a_wrapper_is_converted_and_the_str_branch_kept():
    def f(value: str | date) -> None: ...

    schema = _sig(f)

    converted = decode(schema, {"value": {"$type": "date", "$value": "2026-07-22"}})
    assert converted == {"value": date(2026, 7, 22)}

    kept = decode(schema, {"value": {"$type": "str", "$value": "2026-07-22"}})
    assert kept == {"value": "2026-07-22"}
    assert type(kept["value"]) is str


def test_a_non_iso_string_passes_through_without_touching_or_raising():
    def f(value: date) -> None: ...

    # decode prepares, it does not validate: the core rejects it later.
    assert decode(_sig(f), {"value": "not-a-date"}) == {"value": "not-a-date"}


def test_decode_never_guesses_a_date_from_a_plain_str_field():
    def f(value: str) -> None: ...

    # A str field is a str, whatever the content looks like.
    result = decode(_sig(f), {"value": "2026-07-22"})
    assert result == {"value": "2026-07-22"}
    assert type(result["value"]) is str


def test_a_date_list_decode_does_not_mutate_the_input():
    def f(value: list[date]) -> None: ...

    data = {"value": ["2026-01-01"]}
    decode(_sig(f), data)

    assert data == {"value": ["2026-01-01"]}
    assert type(data["value"][0]) is str


def test_the_string_group_wrapper_is_consumed_before_build_sees_it():
    # build() routes str/date by exact Python type and has no wrapper for them,
    # so a raw wrapper handed straight to it is rejected. Consuming it is
    # decode's work, and the core's decode is what does it.
    def f(value: str | date) -> None: ...

    schema = _sig(f)
    wrapper = {"value": {"$type": "date", "$value": "2026-07-22"}}

    with pytest.raises(Exception):
        schema.build(wrapper)

    assert decode(schema, wrapper) == {"value": date(2026, 7, 22)}
    assert schema.build(decode(schema, wrapper)) == {"value": date(2026, 7, 22)}


def test_the_star_round_trip_builds_a_date_from_a_picked_value(node, tmp_path):
    def f(value: Annotated[date, Label("Day")]) -> None: ...

    schema = _sig(f)
    plan = plan_of(f)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node("float-star-runner.mjs", str(path), "2026-07-22")
    transported = json.loads(json.dumps(result["read"]))

    assert type(transported["value"]) is str

    built = schema.build(decode(schema, transported))

    assert built == {"value": date(2026, 7, 22)}
    assert type(built["value"]) is date


# --- malformed discriminated transport --------------------------------------
#
# A wrapper is consumed only when it is exactly {$type, $value}, the path is a
# real union, and $type names one of its branches. Anything that merely looks
# like a wrapper is malformed transport: decode leaves it intact so build()
# still sees the evidence and reports it, instead of being handed a clean value.

def _wrapped_sig():
    def f(value: int | float) -> None: ...

    return signature_of(f)


def test_a_valid_wrapper_is_still_decoded():
    result = decode(_wrapped_sig(), {"value": {"$type": "float", "$value": 3}})

    assert result == {"value": 3.0}
    assert type(result["value"]) is float


def test_a_wrapper_with_an_unexpected_key_travels_intact():
    payload = {"$type": "float", "$value": 3, "unexpected": "x"}

    # Before the fix the extra key was dropped and the payload came out as 3.0,
    # erasing the evidence that the transport was malformed.
    assert decode(_wrapped_sig(), {"value": payload}) == {"value": payload}


def test_a_kept_wrapper_with_an_unexpected_key_travels_intact():
    def f(value: list[float] | list[int]) -> None: ...

    payload = {"$type": "list[float]", "$value": [1, 2], "extra": 1}

    # The list | list wrapper is the one the core keeps; an extra key still makes
    # it malformed, so neither the wrapper nor its payload is prepared.
    assert decode(signature_of(f), {"value": payload}) == {"value": payload}


def test_a_wrapper_missing_its_value_travels_intact():
    payload = {"$type": "float"}

    assert decode(_wrapped_sig(), {"value": payload}) == {"value": payload}


def test_a_wrapper_missing_its_type_travels_intact():
    payload = {"$value": 3}

    assert decode(_wrapped_sig(), {"value": payload}) == {"value": payload}


def test_a_payload_that_never_reached_its_branch_keeps_the_wrapper():
    schema = _wrapped_sig()

    # The wrapper names an option; it is not itself data. A null is not a float,
    # so consuming the wrapper here would file the null under a branch it never
    # reached, in silence. It survives instead and build() reports the dict.
    null_payload = {"$type": "float", "$value": None}
    assert decode(schema, {"value": null_payload}) == {"value": null_payload}

    # $value absent is not a wrapper at all, so the dict stays whole. Reading it
    # with .get() would have collapsed both cases to the same None.
    absent = {"$type": "float"}
    assert decode(schema, {"value": absent}) == {"value": absent}

    for payload in (null_payload, absent):
        with pytest.raises(Exception):
            schema.build(decode(schema, {"value": payload}))


def test_a_wrapper_with_an_unknown_discriminator_travels_intact():
    payload = {"$type": "unknown", "$value": 3}

    assert decode(_wrapped_sig(), {"value": payload}) == {"value": payload}


def test_a_wrapper_is_not_consumed_when_the_schema_is_not_a_union():
    def plain(value: float) -> None: ...

    def optional(value: Annotated[float, Label("x")] | None) -> None: ...

    payload = {"$type": "float", "$value": 3}

    # A single-branch path never travels wrapped, so a wrapper there is malformed
    # even though "float" does name its shape. Before the fix both came out 3.0,
    # consumed purely on the content of the dict.
    assert decode(signature_of(plain), {"value": payload}) == {"value": payload}
    assert decode(signature_of(optional), {"value": payload}) == {"value": payload}


def test_a_wrapper_whose_discriminator_is_not_in_the_schema_travels_intact():
    def f(value: str) -> None: ...

    payload = {"$type": "float", "$value": 3}

    assert decode(signature_of(f), {"value": payload}) == {"value": payload}


def test_a_malformed_wrapper_inside_a_list_travels_intact():
    def f(value: list[int | float]) -> None: ...

    schema = signature_of(f)

    good = {"$type": "float", "$value": 3}
    bad = {"$type": "float", "$value": 3, "extra": 1}

    assert decode(schema, {"value": [good, bad]}) == {"value": [3.0, bad]}


def test_a_malformed_wrapper_inside_an_object_travels_intact():
    @dataclass
    class P:
        x: Annotated[int | float, Label("x")]

    def f(p: Annotated[P, Label("p")]) -> None: ...

    bad = {"$type": "float", "$value": 3, "extra": 1}

    assert decode(signature_of(f), {"p": {"x": bad}}) == {"p": {"x": bad}}


def test_the_date_and_time_branches_follow_the_same_rule():
    def f(value: date | time) -> None: ...

    schema = signature_of(f)

    assert decode(schema, {"value": {"$type": "date", "$value": "2026-07-22"}}) == {
        "value": date(2026, 7, 22)}
    assert decode(schema, {"value": {"$type": "time", "$value": "14:30:05"}}) == {
        "value": time(14, 30, 5)}

    bad = {"$type": "date", "$value": "2026-07-22", "extra": 1}
    assert decode(schema, {"value": bad}) == {"value": bad}


def test_the_enum_branch_follows_the_same_rule():
    class Estado(Enum):
        A = "a"
        B = "b"

    def f(value: str | Estado) -> None: ...

    schema = signature_of(f)

    assert decode(schema, {"value": {"$type": "Estado", "$value": "A"}}) == {
        "value": Estado.A}

    bad = {"$type": "Estado", "$value": "A", "extra": 1}
    assert decode(schema, {"value": bad}) == {"value": bad}


def test_a_malformed_wrapper_does_not_mutate_the_input():
    def f(value: list[int | float]) -> None: ...

    data = {"value": [{"$type": "float", "$value": 3, "extra": 1}]}
    before = json.loads(json.dumps(data))

    result = decode(signature_of(f), data)

    assert data == before
    assert type(data["value"][0]["$value"]) is int
    # decode still promises a fresh top-level dict.
    assert result is not data


# --- the portable reading belongs to the core --------------------------------
#
# decode() no longer carries a reader of its own: schema.decode() restores the
# portable representation and pytypehintweb adds only the file resolution the
# core deliberately has no opinion about. These pin the behaviour that reading
# gives us, all of which the walker this module used to carry got wrong.

def test_decode_never_raises_on_a_value_of_its_own_accord():
    def f(value: float) -> None: ...

    schema = _sig(f)

    # A JSON document may spell an integer too large for any float. Converting
    # it is not decode's call to make: it hands the value on and build() reports
    # it. The walker that lived here raised OverflowError out of float().
    huge = 10 ** 400
    assert decode(schema, {"value": huge}) == {"value": huge}

    with pytest.raises(Exception):
        schema.build(decode(schema, {"value": huge}))


def test_an_integer_no_float_equals_is_not_restored():
    def f(value: float) -> None: ...

    schema = _sig(f)

    # Above 2**53 the floats thin out, so float(2**53 + 1) answers with a
    # neighbour. Restoring that would hand build() a number the transport never
    # carried, so the integer stands and build() reports the type.
    odd = 2 ** 53 + 1
    assert decode(schema, {"value": odd}) == {"value": odd}
    assert type(decode(schema, {"value": odd})["value"]) is int


def test_only_the_canonical_spelling_of_a_date_is_read():
    def f(value: date) -> None: ...

    schema = _sig(f)

    assert decode(schema, {"value": "2026-07-22"}) == {"value": date(2026, 7, 22)}

    # date.fromisoformat() accepts far more than the canonical spelling, and its
    # grammar overlaps time's. Letting it decide would make the text of a value
    # select an option, so these stand as the strings they arrived as.
    for spelling in ("20260722", "2026-W30-3"):
        assert decode(schema, {"value": spelling}) == {"value": spelling}


def test_only_the_canonical_spelling_of_a_time_is_read():
    def f(value: time) -> None: ...

    schema = _sig(f)

    assert decode(schema, {"value": "14:30:05"}) == {"value": time(14, 30, 5)}
    # "2020" is a year, not twenty past eight in the evening.
    assert decode(schema, {"value": "2020"}) == {"value": "2020"}


@pytest.mark.parametrize("hint, payload", [
    # A date that never parsed, and a canonical spelling naming an unreal day.
    # Both collide with str on the portable spelling, so the wrapper is the one
    # the browser really emits here — this is the union the rule is about.
    (str | date, {"$type": "date", "$value": "not-a-date"}),
    (str | date, {"$type": "date", "$value": "2026-02-31"}),
    # A time whose branch it never reached, beside a date that spells alike.
    (date | time, {"$type": "time", "$value": "not-a-time"}),
    # An enum name no member answers to, beside the str it competes with.
    (str | Estado, {"$type": "Estado", "$value": "ZZZ"}),
])
def test_a_wrapper_is_not_filed_under_the_branch_beside_the_one_it_names(
        hint, payload):
    def f(value: hint) -> None: ...

    schema = signature_of(f)

    # Consuming a wrapper whose payload never read as the option it names would
    # settle a failed date as the str beside it, in silence. The wrapper stays
    # and build() reports it.
    assert decode(schema, {"value": payload}) == {"value": payload}

    with pytest.raises(Exception):
        schema.build(decode(schema, {"value": payload}))


def test_an_unrouted_subtree_is_copied_rather_than_shared():
    def f(value: int) -> None: ...

    data = {"value": 1, "unknown": {"nested": [1, 2]}}
    result = decode(_sig(f), data)

    # An unknown key travels intact, but the tree decode returns is its own:
    # mutating the result must not reach back into the caller's document.
    assert result["unknown"] == data["unknown"]
    assert result["unknown"] is not data["unknown"]

    result["unknown"]["nested"].append(3)
    assert data["unknown"]["nested"] == [1, 2]
