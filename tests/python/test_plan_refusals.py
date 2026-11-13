"""Shapes and defaults a plan cannot carry are refused by plan_of() with a path.

Two refusals that used to surface later and without coordinates: a float default
JavaScript only writes in exponent notation, which reached the browser and failed
there, and a dataclass that contains itself, which ended in a bare RecursionError.
"""

from dataclasses import dataclass, field

import pytest

from pytypehintweb import plan_of


# --------------------------------------------------- float defaults in exponent

@pytest.mark.parametrize("value", [
    1e-7, -1e-7, 9.99e-7, 5e-324, 1e21, -1e21, 1.5e300,
])
def test_a_float_default_javascript_writes_as_an_exponent_is_refused(value):
    def amount(x: float = value):
        pass

    with pytest.raises(TypeError) as error:
        plan_of(amount)

    assert str(error.value).startswith(f"fields.x: Float default: {value!r} ")
    assert "exponent notation" in str(error.value)


@pytest.mark.parametrize("value", [
    0.0, -0.0, 1e-6, -1e-6, 0.0000011, 0.1, 1.5, 123456.789,
    999999999999999900000.0, -999999999999999900000.0,
])
def test_a_float_default_javascript_writes_as_a_decimal_travels(value):
    def amount(x: float = value):
        pass

    assert plan_of(amount)["fields"][0]["default"] == value


def test_the_refusal_reaches_a_float_at_any_depth():
    @dataclass
    class Inner:
        ratio: float = 1e-9

    def in_list(values: list[float] = [0.5, 1e-9]):
        pass

    def in_union(value: int | float = 1e30):
        pass

    def in_struct(inner: Inner = Inner()):
        pass

    for fn, path in ((in_list, "fields.values[1]"), (in_union, "fields.value"),
                     (in_struct, "fields.inner.ratio")):
        with pytest.raises(TypeError) as error:
            plan_of(fn)
        assert str(error.value).startswith(f"{path}: Float default: ")


def test_float_bounds_and_choices_in_exponent_notation_still_travel():
    from typing import Annotated

    from pytypehint import Choices, Max, Min

    def bounded(x: Annotated[float, Min(1e-9), Max(1e30)]):
        pass

    def chosen(x: Annotated[float, Choices(values=(1e-9, 1e30))] = 1e-9):
        pass

    assert plan_of(bounded)["fields"][0]["node"]["options"]["min"] == 1e-9
    assert plan_of(chosen)["fields"][0]["node"]["options"]["choices"] == [1e-9, 1e30]


# ------------------------------------------------------------ recursive shapes

@dataclass
class _Node:
    name: str
    child: "_Node | None" = None


@dataclass
class _Tree:
    label: str
    children: list["_Tree"] = field(default_factory=list)


@dataclass
class _Ping:
    pong: "_Pong | None" = None


@dataclass
class _Pong:
    ping: _Ping | None = None


@dataclass
class _Leaf:
    value: int = 0


@dataclass
class _Twice:
    left: _Leaf
    right: _Leaf
    more: list[_Leaf]


@pytest.mark.parametrize("cls, message", [
    (_Node, "fields.child: _Node contains itself"),
    (_Tree, "fields.children.item: _Tree contains itself"),
    (_Ping, "fields.pong.ping: _Ping contains itself"),
])
def test_a_dataclass_that_contains_itself_is_refused_with_its_path(cls, message):
    with pytest.raises(TypeError) as error:
        plan_of(cls)

    assert str(error.value).startswith(message)
    assert "recursive shape" in str(error.value)


def test_a_recursive_parameter_of_a_function_is_refused_too():
    def save(node: _Node):
        pass

    with pytest.raises(TypeError) as error:
        plan_of(save)

    assert str(error.value).startswith("fields.node.child: _Node contains itself")


def test_a_dataclass_used_more_than_once_is_not_a_cycle():
    plan = plan_of(_Twice)

    assert [f["name"] for f in plan["fields"]] == ["left", "right", "more"]
