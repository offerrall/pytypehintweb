import json
from typing import Annotated

import pytest

from pytypehint import (
    Choices, Label, Max, Min, Placeholder, Slider, Step, signature_of,
)
from pytypehintweb import plan_of


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


def test_plan_of_emits_a_float_node():
    def f(value: Annotated[float, Min(0.5, exclusive=True), Max(10.0), Step(0.1),
                           Placeholder("0.0")]) -> None: ...

    node = _node(f)

    assert node == {
        "kind": "float",
        "options": {
            "min": 0.5,
            "max": 10.0,
            "minExclusive": True,
            "maxExclusive": False,
            "step": 0.1,
            "choices": None,
            "placeholder": "0.0",
            "invalidMessage": "Enter a valid number",
            "finiteMessage": "Must be a finite number",
            "minMessage": "Must be at least {value}",
            "maxMessage": "Must be at most {value}",
            "increaseLabel": "Increase",
            "decreaseLabel": "Decrease",
        },
    }


def test_a_plain_float_carries_the_exclusive_flags_as_false():
    def f(value: float) -> None: ...

    options = _node(f)["options"]

    assert options["min"] is None
    assert options["max"] is None
    assert options["minExclusive"] is False
    assert options["maxExclusive"] is False


def test_the_min_and_max_travel_without_conversion():
    def f(value: Annotated[float, Min(0.5, exclusive=True),
                           Max(1.5, exclusive=True)]) -> None: ...

    options = _node(f)["options"]

    # Unlike Int, the bound value is emitted verbatim; the exclusivity rides
    # beside it as a flag, never converted to a ±1 neighbour.
    assert options["min"] == 0.5
    assert options["max"] == 1.5
    assert options["minExclusive"] is True
    assert options["maxExclusive"] is True


def test_float_choices_are_emitted_as_numbers():
    def f(value: Annotated[float, Choices(values=(0.25, 0.5, 1.0))]) -> None: ...

    assert _node(f)["options"]["choices"] == [0.25, 0.5, 1.0]


def test_a_slider_on_a_float_is_rejected():
    def f(value: Annotated[float, Min(0.0), Max(1.0), Slider()]) -> None: ...

    with pytest.raises(TypeError, match="Float.slider is not supported yet"):
        plan_of(f)


def test_choices_and_placeholder_are_rejected_together():
    def f(value: Annotated[float, Choices(values=(1.0, 2.0)),
                           Placeholder("x")]) -> None: ...

    with pytest.raises(TypeError, match="Choices and Placeholder"):
        plan_of(f)


def test_a_float_default_travels_as_a_float():
    def f(value: Annotated[float, Min(0.0), Max(1.0)] = 0.5) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == 0.5


def test_int_and_float_collide_on_the_wire_and_both_travel_wrapped():
    def f(value: int | float) -> None: ...

    node = _node(f)

    assert node["kind"] == "choice"
    modes = {b["value"]: b["mode"] for b in node["branches"]}
    assert modes == {"int": "wrapped", "float": "wrapped"}


def test_str_and_int_are_unaffected_and_stay_plain():
    def f(value: str | int) -> None: ...

    node = _node(f)
    modes = {b["value"]: b["mode"] for b in node["branches"]}

    # str is a JSON string, int a JSON number: distinct groups, no wrapper.
    assert modes == {"str": "plain", "int": "plain"}


def test_list_of_float():
    def f(value: list[float]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "float"


def test_the_full_round_trip_with_float(node, tmp_path):
    def f(
        ratio: Annotated[float, Min(0.0), Max(1.0), Label("Ratio")],
        amount: Annotated[float, Label("Amount")] = 2.5,
    ) -> None:
        """Float round trip."""

    plan = plan_of(f)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node("roundtrip-runner.mjs", str(path))

    assert result["isReady"] is True
    assert result["hasError"] is False
