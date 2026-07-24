import json
from dataclasses import dataclass
from typing import Annotated

import pytest

from pytypehint import (
    Choices, Max, Min, MultipleOf, Rows, Slider, Step, struct_of,
)
from pytypehintweb import plan_of
from pytypehintweb.plan import _check_branches


def build(annotations, base=str):
    def example(value: Annotated[base, *annotations]) -> None: ...

    return plan_of(example)


class TestOwnedByTheCore:
    """Invariants the schema model makes unconstructable before plan_of()."""

    @pytest.mark.parametrize("value", [0, -1])
    def test_rows_must_be_positive(self, value):
        with pytest.raises(ValueError, match="must be > 0"):
            Rows(value)

    def test_a_positive_rows_reaches_the_plan(self):
        assert build((Rows(5),))["fields"][0]["node"]["options"]["rows"] == 5

    @pytest.mark.parametrize("value", [0, -2])
    def test_step_must_be_positive(self, value):
        with pytest.raises(ValueError, match="must be > 0"):
            Step(value)

    def test_multiple_of_must_be_positive(self):
        with pytest.raises(ValueError, match="must be > 0"):
            MultipleOf(0)

    def test_choices_must_not_be_empty(self):
        with pytest.raises(ValueError, match="must not be empty"):
            Choices(values=())

    def test_choices_must_not_repeat(self):
        with pytest.raises(ValueError, match="must not repeat"):
            Choices(values=("a", "a"))

    def test_string_length_range_must_not_be_empty(self):
        with pytest.raises(ValueError, match="empty range"):
            build((Min(5), Max(2)))

    def test_integer_range_must_not_be_empty(self):
        with pytest.raises(ValueError, match="empty range"):
            build((Min(5), Max(2)), int)

    def test_exclusive_bounds_that_collapse_are_rejected(self):
        with pytest.raises(ValueError, match="empty range"):
            build((Min(5, exclusive=True), Max(6, exclusive=True)), int)

    def test_list_length_range_must_not_be_empty(self):
        with pytest.raises(ValueError, match="empty range"):
            build((Min(3), Max(1)), list[str])

    def test_a_slider_needs_both_bounds(self):
        with pytest.raises(ValueError, match="slider requires min and max"):
            build((Slider(),), int)

    def test_a_slider_needs_a_reachable_multiple(self):
        with pytest.raises(ValueError, match="no multiple of"):
            build((Min(1), Max(9), Step(4), MultipleOf(10), Slider()), int)

    def test_an_ordinary_range_without_a_multiple_is_unconstructible(self):
        # The core rejects an ordinary [min, max] range that admits no multiple
        # of multipleOf when it compiles the schema, so the adapter need not
        # re-check it (it used to, redundantly).
        with pytest.raises(ValueError, match="no multiple of"):
            build((Min(1), Max(4), MultipleOf(7)), int)

    def test_a_slider_default_outside_the_range_is_rejected(self):
        def example(value: Annotated[int, Min(0), Max(10), Slider()] = 50
                    ) -> None: ...

        # The core rejects an out-of-range default when it compiles the
        # signature; match the stable part of its message, not its exact wording.
        with pytest.raises(ValueError, match="too large"):
            plan_of(example)

    def test_a_valid_slider_reaches_the_plan(self):
        options = build((Min(0), Max(10), Step(2), Slider()), int)[
            "fields"][0]["node"]["options"]

        assert options["slider"] is True
        assert (options["min"], options["max"], options["step"]) == (0, 10, 2)

    def test_choices_must_satisfy_their_constraints(self):
        with pytest.raises(ValueError, match="below minimum"):
            build((Min(10), Choices(values=(5, 20))), int)

    def test_a_union_cannot_repeat_an_option_type(self):
        def example(value: Annotated[str, Min(1)] | Annotated[str, Min(2)]
                    ) -> None: ...

        with pytest.raises(ValueError, match="duplicate option types"):
            plan_of(example)


class TestOwnedByTheAdapter:
    """Invariants only pytypehintweb can know, checked during plan_of()."""

    def test_a_nested_object_needs_at_least_one_field(self):
        @dataclass
        class Empty:
            pass

        @dataclass
        class Outer:
            inner: Empty

        with pytest.raises(TypeError, match="has no fields"):
            plan_of(Outer)

    def test_an_empty_dataclass_is_still_valid_as_the_form_root(self):
        @dataclass
        class Empty:
            pass

        assert plan_of(Empty) == {
            "v": 1, "kind": "form", "name": "Empty", "description": None,
            "fields": []}

    def test_branch_option_ids_must_be_unique_across_the_whole_choice(self):
        @dataclass
        class Thing:
            value: str

        duplicated = [struct_of(Thing), struct_of(Thing)]

        with pytest.raises(TypeError, match="share the option id"):
            _check_branches(duplicated, "fields.value")

    def test_branch_option_ids_are_checked_regardless_of_transport_type(self):
        @dataclass
        class Thing:
            value: str

        class FakeScalar:
            pytype = str

            def option_id(self):
                return "Thing"

        mixed = [struct_of(Thing), FakeScalar()]

        with pytest.raises(TypeError, match="share the option id"):
            _check_branches(mixed, "fields.value")

    def test_unique_branch_option_ids_are_accepted(self):
        def example(value: str | int) -> None: ...

        branches = plan_of(example)["fields"][0]["node"]["branches"]

        assert [b["value"] for b in branches] == ["str", "int"]
        assert [b["mode"] for b in branches] == ["plain", "plain"]

    def test_an_unsafe_integer_is_rejected(self):
        with pytest.raises(TypeError, match="safe integer range"):
            build((Min(2 ** 60),), int)

    def test_incompatible_controls_are_rejected(self):
        with pytest.raises(TypeError, match="different controls"):
            build((Rows(3), Choices(values=("a", "b"))))


def test_every_demo_plan_passes_javascript_validation(node, tmp_path):
    from pytypehintweb.demo import app

    plans = {form["id"]: form["plan"]
             for section in app.PLANS for form in section["forms"]}

    path = tmp_path / "demo-plans.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["checked"] == len(plans)
    assert result["mounted"] == len(plans)
