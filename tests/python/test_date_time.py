import json
from datetime import date, time
from typing import Annotated

import pytest

from pytypehint import Choices, Label, Max, Min, Placeholder, signature_of
from pytypehintweb import decode, plan_of


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


# --- date nodes -------------------------------------------------------------

def test_plan_of_emits_a_date_node():
    def f(value: Annotated[date, Min(date(2026, 1, 1)), Max(date(2026, 12, 31)),
                           Placeholder("pick a day")]) -> None: ...

    assert _node(f) == {
        "kind": "date",
        "options": {
            "min": "2026-01-01",
            "max": "2026-12-31",
            "placeholder": "pick a day",
            "choices": None,
            "invalidMessage": "Enter a valid date",
            "minMessage": "Must be on or after {value}",
            "maxMessage": "Must be on or before {value}",
        },
    }


def test_a_date_exclusive_bound_is_converted_by_one_day():
    def f(value: Annotated[date, Min(date(2026, 1, 1), exclusive=True),
                           Max(date(2026, 12, 31), exclusive=True)]) -> None: ...

    options = _node(f)["options"]

    # Exclusive after Jan 1 becomes on-or-after Jan 2; before Dec 31 becomes
    # on-or-before Dec 30. The node carries only inclusive bounds, like an int.
    assert options["min"] == "2026-01-02"
    assert options["max"] == "2026-12-30"
    assert "minExclusive" not in options
    assert "maxExclusive" not in options


def test_date_choices_are_iso_strings():
    def f(value: Annotated[date, Choices(values=(date(2026, 3, 20),
                                                 date(2026, 6, 21)))]) -> None: ...

    assert _node(f)["options"]["choices"] == ["2026-03-20", "2026-06-21"]


def test_a_date_default_travels_as_iso():
    def f(value: Annotated[date, Label("d")] = date(2026, 7, 22)) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == "2026-07-22"


# --- time nodes -------------------------------------------------------------

def test_plan_of_emits_a_time_node_with_exclusive_flags():
    def f(value: Annotated[time, Min(time(9, 0), exclusive=True),
                           Max(time(17, 30))]) -> None: ...

    assert _node(f) == {
        "kind": "time",
        "options": {
            "min": "09:00:00",
            "max": "17:30:00",
            "minExclusive": True,
            "maxExclusive": False,
            "placeholder": None,
            "choices": None,
            "invalidMessage": "Enter a valid time",
            "minMessage": "Must be at or after {value}",
            "maxMessage": "Must be at or before {value}",
        },
    }


def test_time_bounds_are_not_converted():
    def f(value: Annotated[time, Min(time(9, 0), exclusive=True)]) -> None: ...

    options = _node(f)["options"]

    # No ±1: the bound value is emitted verbatim, the flag rides beside it.
    assert options["min"] == "09:00:00"
    assert options["minExclusive"] is True


def test_time_choices_travel_as_iso_with_seconds():
    def f(value: Annotated[time, Choices(values=(time(9, 0),
                                                 time(17, 30)))]) -> None: ...

    # The canonical is isoformat(): always HH:MM:SS. The core pins a time to
    # whole seconds, so no sub-second fraction can ever appear here.
    assert _node(f)["options"]["choices"] == ["09:00:00", "17:30:00"]


def test_a_time_default_travels_as_iso_with_seconds():
    def f(value: Annotated[time, Label("t")] = time(14, 30)) -> None: ...

    assert plan_of(f)["fields"][0]["default"] == "14:30:00"


# The core is the single source of the whole-seconds rule: it
# rejects a microsecond time in a bound, a choice or a default at compile time, so
# plan_of() can never emit one. plan_of does not re-validate what the core owns.
def test_the_core_rejects_a_microsecond_time_bound():
    def f(value: Annotated[time, Min(time(9, 0, 0, 1))]) -> None: ...

    with pytest.raises(ValueError):
        plan_of(f)


def test_the_core_rejects_a_microsecond_time_choice():
    def f(value: Annotated[time, Choices(values=(time(9, 0),
                                                 time(17, 30, 0, 500000)))]) -> None: ...

    with pytest.raises(ValueError):
        plan_of(f)


def test_the_core_rejects_a_microsecond_time_default():
    def f(value: Annotated[time, Label("t")] = time(14, 30, 0, 500000)) -> None: ...

    with pytest.raises(ValueError):
        plan_of(f)


# --- union transport (string group) -----------------------------------------

def test_str_and_date_collide_on_the_wire_and_travel_wrapped():
    def f(value: str | date) -> None: ...

    node = _node(f)
    modes = {b["value"]: b["mode"] for b in node["branches"]}

    assert modes == {"str": "wrapped", "date": "wrapped"}


def test_date_and_time_collide_and_travel_wrapped():
    def f(value: date | time) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"date": "wrapped", "time": "wrapped"}


def test_str_and_int_are_unaffected_by_the_string_group():
    def f(value: str | int) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"str": "plain", "int": "plain"}


def test_list_of_date_and_of_time():
    def f(d: list[date], t: list[time]) -> None: ...

    fields = plan_of(f)["fields"]

    assert fields[0]["node"]["item"]["kind"] == "date"
    assert fields[1]["node"]["item"]["kind"] == "time"


# --- star round trips through the browser -----------------------------------

def _star(node_fixture, tmp_path, fn, raw):
    plan = plan_of(fn)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node_fixture("float-star-runner.mjs", str(path), raw)
    return result["read"]


def test_a_picked_date_builds_the_exact_python_date(node, tmp_path):
    def f(value: Annotated[date, Label("Day")]) -> None: ...

    read = _star(node, tmp_path, f, "2026-07-22")
    assert read["value"] == "2026-07-22"

    schema = signature_of(f)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built == {"value": date(2026, 7, 22)}
    assert type(built["value"]) is date


def test_a_picked_time_with_seconds_builds_the_exact_python_time(node, tmp_path):
    def f(value: Annotated[time, Label("At")]) -> None: ...

    read = _star(node, tmp_path, f, "14:30:05")
    assert read["value"] == "14:30:05"

    schema = signature_of(f)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built == {"value": time(14, 30, 5)}
    assert type(built["value"]) is time


def test_a_picked_whole_minute_time_survives_the_round_trip(node, tmp_path):
    # A whole-minute time is canonical "HH:MM:SS" (never "HH:MM"), so the picked
    # value survives the full journey read -> JSON -> decode -> build -> time(9, 0).
    def f(value: Annotated[time, Label("At")]) -> None: ...

    read = _star(node, tmp_path, f, "09:00:00")
    assert read["value"] == "09:00:00"

    schema = signature_of(f)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built == {"value": time(9, 0)}
    assert type(built["value"]) is time
