import json
from dataclasses import dataclass, field
from typing import Annotated

import pytest

from pytypehint import Choices, Max, Min, MultipleOf, Pattern, Slider, Step
from pytypehintweb import plan_of


@dataclass
class Inner:
    a: Annotated[str, Min(2)] = "abcd"
    b: Annotated[int, Min(0), Max(100)] = 5


@dataclass
class DefaultsConfig:
    """A default is producer configuration and must satisfy every node
    constraint, so plan_of() must never emit one the browser would reject."""

    text_len: Annotated[str, Min(3), Max(10)] = "hello"
    text_pattern: Annotated[str, Pattern("[a-z]+")] = "abc"
    text_choice: Annotated[str, Choices(values=("a", "b"))] = "b"
    number: Annotated[int, Min(0), Max(100), MultipleOf(5)] = 10
    number_choice: Annotated[int, Choices(values=(1, 2, 3))] = 2
    exclusive: Annotated[int, Min(0, exclusive=True), Max(10, exclusive=True)] = 5
    slider_plain: Annotated[int, Min(0), Max(20), Step(5), Slider()] = 10
    slider_multiple: Annotated[
        int, Min(0), Max(30), Step(3), MultipleOf(3), Slider()] = 6
    nested: Inner = field(default_factory=Inner)
    tags: list[Annotated[str, Min(1)]] = field(
        default_factory=lambda: ["x", "y"])
    maybe: str | None = "present"
    either: Annotated[int, Min(0)] | Annotated[str, Min(1)] = 7


def defaulted_signature(
    name: Annotated[str, Min(1), Max(20)] = "ada",
    amount: Annotated[int, Min(0), Max(100), MultipleOf(10)] = 30,
    ratio: Annotated[int, Min(-50), Max(50), Step(25), Slider()] = -25,
) -> None:
    """Every parameter default must survive conversion and browser checks."""


def test_every_generated_default_is_accepted_by_javascript(node, tmp_path):
    # Covers string min/max/pattern/choices, integer min/max/multipleOf/choices,
    # slider defaults, exclusive bounds after conversion, nested object, list,
    # optional and union defaults.
    plans = {
        "config": plan_of(DefaultsConfig),
        "signature": plan_of(defaulted_signature),
    }

    path = tmp_path / "default-plans.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["checked"] == len(plans)
    assert result["mounted"] == len(plans)


def test_a_slider_default_off_the_step_grid_is_rejected_by_the_adapter():
    def example(
        value: Annotated[int, Min(0), Max(20), Step(5), Slider()] = 7,
    ) -> None: ...

    # 7 is within [0, 20] and the core accepts it, but it is not a step
    # position, so the adapter rejects it before emitting the plan.
    with pytest.raises(TypeError, match="not on the grid"):
        plan_of(example)


def test_an_on_grid_slider_default_is_accepted():
    def example(
        value: Annotated[int, Min(0), Max(20), Step(5), Slider()] = 15,
    ) -> None: ...

    assert plan_of(example)["fields"][0]["default"] == 15
