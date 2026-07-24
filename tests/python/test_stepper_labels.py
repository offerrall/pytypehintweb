from typing import Annotated

import pytest

from pytypehint import Choices, Max, Min, Slider
from pytypehintweb import WebConfig, plan_of


def int_node(obj, **kwargs):
    return plan_of(obj, **kwargs)["fields"][0]["node"]


def ordinary(value: Annotated[int, Min(0), Max(10)]) -> None: ...


def slider(value: Annotated[int, Min(0), Max(10), Slider()]) -> None: ...


def closed(value: Annotated[int, Choices(values=(1, 2, 3))]) -> None: ...


class TestDefaults:
    def test_the_default_stepper_labels(self):
        config = WebConfig()

        assert config.int_increase_label == "Increase"
        assert config.int_decrease_label == "Decrease"

    def test_default_stepper_labels_are_present_in_the_expanded_plan(self):
        options = int_node(ordinary)["options"]

        assert options["increaseLabel"] == "Increase"
        assert options["decreaseLabel"] == "Decrease"


class TestTransport:
    def test_custom_stepper_labels_travel_for_an_ordinary_integer(self):
        config = WebConfig(int_increase_label="Subir", int_decrease_label="Bajar")

        options = int_node(ordinary, config=config)["options"]

        assert options["increaseLabel"] == "Subir"
        assert options["decreaseLabel"] == "Bajar"

    def test_a_changed_stepper_label_travels_alongside_the_default(self):
        options = int_node(ordinary, config=WebConfig(int_increase_label="Subir"))[
            "options"]

        assert options["increaseLabel"] == "Subir"
        assert options["decreaseLabel"] == "Decrease"

    def test_every_int_node_carries_the_stepper_labels(self):
        # The plan is fully expanded: the labels travel on every int node, and
        # each side decides whether a stepper is actually rendered.
        for obj in (ordinary, slider, closed):
            options = int_node(obj, config=WebConfig(int_increase_label="Subir"))[
                "options"]

            assert options["increaseLabel"] == "Subir"
            assert options["decreaseLabel"] == "Decrease"


class TestValidation:
    def test_a_non_string_stepper_label_is_rejected(self):
        with pytest.raises(TypeError, match="must be str"):
            WebConfig(int_increase_label=1)

    def test_an_empty_stepper_label_is_rejected(self):
        with pytest.raises(TypeError, match="must not be empty"):
            WebConfig(int_increase_label="")

    def test_a_stepper_label_may_not_carry_placeholders(self):
        with pytest.raises(TypeError, match="must not contain placeholders"):
            WebConfig(int_decrease_label="Down {value}")

    def test_a_plain_stepper_label_is_accepted(self):
        assert WebConfig(int_increase_label="Más").int_increase_label == "Más"
