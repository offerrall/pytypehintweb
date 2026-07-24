import json
from typing import Annotated

import pytest

from pytypehint import Choices, Max, Min, MultipleOf, Placeholder, Slider, Step
from pytypehintweb import WebConfig, plan_of
from pytypehintweb.plan import _inclusive_length, _int_node, _str_node


class _Bound:
    def __init__(self, value, exclusive):
        self.value = value
        self.exclusive = exclusive


class _Value:
    def __init__(self, value):
        self.value = value


class _SliderMeta:
    show_value = True


class _FakeInt:
    """A duck-typed Int shape that bypasses the core, to reach the adapter's
    own boundary guards directly."""

    choices = None
    placeholder = None

    def __init__(self, minimum=None, maximum=None, multiple_of=None,
                 step=None, slider=None):
        self.min = minimum
        self.max = maximum
        self.multiple_of = multiple_of
        self.step = step
        self.slider = slider


class _FakeStr:
    """A duck-typed Str shape that bypasses the core, to reach the adapter's
    own length-bound guards directly."""

    is_path_file = None
    is_password = None
    rows = None
    choices = None
    pattern = None
    placeholder = None

    def __init__(self, minimum=None, maximum=None):
        self.min = minimum
        self.max = maximum


def test_exclusive_bounds_that_convert_to_an_empty_range_are_rejected():
    # x > 5 and x < 6 -> min 6, max 5 after conversion: no integer remains.
    shape = _FakeInt(minimum=_Bound(5, True), maximum=_Bound(6, True))

    with pytest.raises(TypeError, match="empty range"):
        _int_node(shape, WebConfig(), "fields.value")


def test_a_valid_exclusive_range_still_converts():
    shape = _FakeInt(minimum=_Bound(5, True), maximum=_Bound(7, True))

    options = _int_node(shape, WebConfig(), "fields.value")["options"]

    assert (options["min"], options["max"]) == (6, 6)


def test_a_slider_without_a_reachable_position_is_rejected_by_the_adapter():
    shape = _FakeInt(minimum=_Bound(1, False), maximum=_Bound(9, False),
                     multiple_of=_Value(10), step=_Value(4),
                     slider=_SliderMeta())

    with pytest.raises(TypeError, match="no reachable position"):
        _int_node(shape, WebConfig(), "fields.value")


def test_a_slider_missing_a_bound_is_rejected_by_the_adapter():
    shape = _FakeInt(minimum=_Bound(0, False), maximum=None,
                     slider=_SliderMeta())

    with pytest.raises(TypeError, match="requires both min and max"):
        _int_node(shape, WebConfig(), "fields.value")


# --- exclusive string / list length bounds ----------------------------------

def test_the_core_rejects_exclusive_string_bounds():
    def example(value: Annotated[str, Min(3, exclusive=True)]) -> None: ...

    with pytest.raises(ValueError, match="exclusive"):
        plan_of(example)


def test_the_core_rejects_exclusive_list_bounds():
    def example(value: Annotated[list[str], Max(4, exclusive=True)]) -> None: ...

    with pytest.raises(ValueError, match="exclusive"):
        plan_of(example)


def test_the_adapter_defensively_rejects_an_exclusive_string_minimum():
    shape = _FakeStr(minimum=_Bound(3, True))

    with pytest.raises(TypeError, match="exclusive length bounds are not"):
        _str_node(shape, WebConfig(), "fields.value")


def test_the_adapter_defensively_rejects_an_exclusive_string_maximum():
    shape = _FakeStr(maximum=_Bound(5, True))

    with pytest.raises(TypeError, match="exclusive length bounds are not"):
        _str_node(shape, WebConfig(), "fields.value")


def test_a_string_empty_length_range_is_rejected():
    shape = _FakeStr(minimum=_Bound(5, False), maximum=_Bound(2, False))

    with pytest.raises(TypeError, match="empty range"):
        _str_node(shape, WebConfig(), "fields.value")


def test_inclusive_length_converts_and_guards():
    assert _inclusive_length(None, "p", "w") is None
    assert _inclusive_length(_Bound(3, False), "p", "w") == 3

    with pytest.raises(TypeError, match="exclusive length bounds are not"):
        _inclusive_length(_Bound(3, True), "p", "w")


# --- ordinary integer bound conversion ---------------------------------------
# The adapter no longer re-checks that an ordinary [min, max] range admits a
# multiple of multipleOf: the core rejects that schema at compile time (see
# test_plan_invariants). These tests only cover the bound conversion the adapter
# still owns.

def test_a_reachable_ordinary_integer_range_travels():
    shape = _FakeInt(minimum=_Bound(-8, False), maximum=_Bound(-1, False),
                     multiple_of=_Value(7))

    options = _int_node(shape, WebConfig(), "fields.value")["options"]

    assert options["multipleOf"] == 7


def test_an_exclusive_range_uses_the_converted_bounds():
    # x > 1 and x < 8 -> converted [2, 7].
    shape = _FakeInt(minimum=_Bound(1, True), maximum=_Bound(8, True),
                     multiple_of=_Value(7))

    options = _int_node(shape, WebConfig(), "fields.value")["options"]

    assert (options["min"], options["max"], options["multipleOf"]) == (2, 7, 7)


# --- slider + placeholder ----------------------------------------------------

def test_slider_with_a_placeholder_is_rejected():
    def example(
        value: Annotated[int, Min(0), Max(10), Slider(), Placeholder("pick")],
    ) -> None: ...

    with pytest.raises(TypeError, match="Slider and Placeholder"):
        plan_of(example)


def slider_step(value: Annotated[int, Min(0), Max(100), Step(5), Slider()]):
    ...


def slider_step_multiple(
    value: Annotated[int, Min(0), Max(100), Step(5), MultipleOf(25), Slider()],
):
    ...


def slider_plain(value: Annotated[int, Min(1), Max(10), Slider()]):
    ...


def slider_negative(
    value: Annotated[int, Min(-20), Max(20), Step(2), MultipleOf(6), Slider()],
):
    ...


def slider_exclusive(
    value: Annotated[
        int, Min(0, exclusive=True), Max(100, exclusive=True), Step(5), Slider(),
    ],
):
    ...


def slider_exclusive_multiple(
    value: Annotated[
        int,
        Min(-1, exclusive=True), Max(30, exclusive=True),
        Step(5), MultipleOf(5), Slider(),
    ],
):
    # After conversion: min 0, max 29. Positions 0, 5, 10 ... are multiples
    # of 5, so 0 is a reachable valid start.
    ...


def test_every_generated_slider_plan_is_accepted_by_javascript(node, tmp_path):
    # Inclusive bounds, exclusive bounds after integer conversion, negative
    # bounds, Step, MultipleOf and Step + MultipleOf: every slider plan_of()
    # can emit must be accepted by the browser's checkPlan().
    plans = {
        name: plan_of(fn)
        for name, fn in [
            ("step", slider_step),
            ("step_multiple", slider_step_multiple),
            ("plain", slider_plain),
            ("negative", slider_negative),
            ("exclusive", slider_exclusive),
            ("exclusive_multiple", slider_exclusive_multiple),
        ]
    }

    path = tmp_path / "sliders.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["checked"] == len(plans)
    assert result["mounted"] == len(plans)


def int_range(value: Annotated[int, Min(0), Max(100), MultipleOf(5)]): ...


def int_min_only(value: Annotated[int, Min(3), MultipleOf(7)]): ...


def int_max_only(value: Annotated[int, Max(20), MultipleOf(7)]): ...


def int_zero_crossing(value: Annotated[int, Min(-10), Max(10), MultipleOf(3)]): ...


def int_exclusive_multiple(
    value: Annotated[
        int, Min(1, exclusive=True), Max(8, exclusive=True), MultipleOf(7)],
): ...


def int_choices(value: Annotated[int, Choices(values=(2, 4, 8))]): ...


def test_every_generated_integer_plan_is_accepted_by_javascript(node, tmp_path):
    # Ordinary integer ranges (two-sided, one-sided, zero-crossing, exclusive
    # after conversion), a reachable multipleOf and choices all stay valid for
    # the browser's checkPlan().
    plans = {
        name: plan_of(fn)
        for name, fn in [
            ("range", int_range),
            ("min_only", int_min_only),
            ("max_only", int_max_only),
            ("zero_crossing", int_zero_crossing),
            ("exclusive_multiple", int_exclusive_multiple),
            ("choices", int_choices),
        ]
    }

    path = tmp_path / "ints.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["checked"] == len(plans)
    assert result["mounted"] == len(plans)
