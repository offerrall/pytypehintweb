from typing import Annotated

import pytest

from pytypehint import Label
from pytypehintweb import WebConfig, plan_of


def choice_node(obj, **kwargs):
    return plan_of(obj, **kwargs)["fields"][0]["node"]


def union(value: Annotated[str | int, Label("Reference")]) -> None: ...


class TestDefaults:
    def test_the_default_mode_labels(self):
        config = WebConfig()

        assert config.mode_previous_label == "Previous mode"
        assert config.mode_next_label == "Next mode"
        assert config.mode_position_label == "Mode {current} of {total}"

    def test_default_mode_labels_are_present_in_the_expanded_plan(self):
        node = choice_node(union)

        assert node["kind"] == "choice"
        assert node["previousLabel"] == "Previous mode"
        assert node["nextLabel"] == "Next mode"
        assert node["positionLabel"] == "Mode {current} of {total}"


class TestCustom:
    def test_custom_mode_labels_travel(self):
        config = WebConfig(
            mode_previous_label="Modo anterior",
            mode_next_label="Modo siguiente",
            mode_position_label="Modo {current} de {total}",
        )

        node = choice_node(union, config=config)

        assert node["previousLabel"] == "Modo anterior"
        assert node["nextLabel"] == "Modo siguiente"
        assert node["positionLabel"] == "Modo {current} de {total}"

    def test_a_changed_label_travels_alongside_the_defaults(self):
        config = WebConfig(mode_next_label="Siguiente")

        node = choice_node(union, config=config)

        assert node["nextLabel"] == "Siguiente"
        assert node["previousLabel"] == "Previous mode"
        assert node["positionLabel"] == "Mode {current} of {total}"

    def test_a_single_branch_union_has_no_choice_node(self):
        def example(value: str | None) -> None: ...

        node = choice_node(example, config=WebConfig(mode_next_label="X"))

        assert node["kind"] != "choice"


class TestValidation:
    def test_a_non_string_label_is_rejected(self):
        with pytest.raises(TypeError, match="must be str"):
            WebConfig(mode_previous_label=1)

    def test_a_previous_label_may_not_carry_placeholders(self):
        with pytest.raises(TypeError, match="must not contain placeholders"):
            WebConfig(mode_previous_label="Previous {current}")

    def test_a_next_label_may_not_carry_placeholders(self):
        with pytest.raises(TypeError, match="must not contain placeholders"):
            WebConfig(mode_next_label="Next {total}")

    def test_the_position_label_needs_current_and_total(self):
        with pytest.raises(TypeError, match="current.*total|total.*current"):
            WebConfig(mode_position_label="Mode {current}")

    def test_the_position_label_rejects_a_repeated_placeholder(self):
        with pytest.raises(TypeError, match="exactly one"):
            WebConfig(mode_position_label="{current} {current} of {total}")

    def test_the_position_label_rejects_an_unknown_placeholder(self):
        with pytest.raises(TypeError, match="current.*total|total.*current"):
            WebConfig(mode_position_label="Mode {index} of {total}")

    def test_the_position_label_rejects_unbalanced_braces(self):
        with pytest.raises(TypeError, match="unbalanced braces"):
            WebConfig(mode_position_label="Mode {current} of {total")

    def test_a_valid_custom_position_label_is_accepted(self):
        config = WebConfig(mode_position_label="{current}/{total}")

        assert config.mode_position_label == "{current}/{total}"

    def test_a_list_label_may_not_carry_placeholders(self):
        with pytest.raises(TypeError, match="must not contain placeholders"):
            WebConfig(list_add_label="Add {value}")

    def test_a_list_label_rejects_unbalanced_braces(self):
        with pytest.raises(TypeError, match="unbalanced braces"):
            WebConfig(list_item_label="Item {")

    def test_a_plain_list_label_is_accepted(self):
        assert WebConfig(list_add_label="Añadir").list_add_label == "Añadir"

    def test_an_empty_button_label_is_rejected(self):
        with pytest.raises(TypeError, match="must not be empty"):
            WebConfig(list_add_label="")

    def test_an_empty_mode_label_is_rejected(self):
        with pytest.raises(TypeError, match="must not be empty"):
            WebConfig(mode_previous_label="")
