from typing import Annotated

import pytest

from pytypehint import Choices, Placeholder
from pytypehintweb import plan_of


def options_of(obj, **kwargs) -> dict:
    return plan_of(obj, **kwargs)["fields"][0]["node"]["options"]


def test_a_plain_str_input_has_a_null_placeholder():
    def example(value: str) -> None: ...

    assert options_of(example)["placeholder"] is None


def test_a_plain_int_input_has_a_null_placeholder():
    def example(value: int) -> None: ...

    assert options_of(example)["placeholder"] is None


def test_str_choices_carry_a_null_placeholder():
    def example(value: Annotated[str, Choices(values=("a", "b"))]) -> None: ...

    options = options_of(example)

    assert options["choices"] == ["a", "b"]
    assert options["placeholder"] is None


def test_int_choices_carry_a_null_placeholder():
    def example(value: Annotated[int, Choices(values=(1, 2))]) -> None: ...

    options = options_of(example)

    assert options["choices"] == [1, 2]
    assert options["placeholder"] is None


def test_a_custom_placeholder_travels_on_a_plain_input():
    def example(value: Annotated[str, Placeholder("Name")]) -> None: ...

    assert options_of(example)["placeholder"] == "Name"


def test_a_placeholder_on_choices_is_rejected():
    def example(value: Annotated[str, Choices(values=("a", "b")),
                                 Placeholder("Size")]) -> None: ...

    with pytest.raises(TypeError, match="Choices and Placeholder"):
        plan_of(example)


def test_a_placeholder_on_int_choices_is_rejected():
    def example(value: Annotated[int, Choices(values=(1, 2)),
                                 Placeholder("Pick")]) -> None: ...

    with pytest.raises(TypeError, match="Choices and Placeholder"):
        plan_of(example)
