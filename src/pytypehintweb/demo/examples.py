from dataclasses import dataclass
from datetime import date, time
from enum import Enum
from typing import Annotated, Literal

from pytypehint import (
    Choices, Description, IsPassword, IsPathFile, Label, Max, Min, MultipleOf,
    OptionalToggle, Pattern, Placeholder, Rows, Slider, Step,
)

from pytypehintweb import Color, Email

EMAIL = r"[^@ ]+@[^@ ]+\.[a-z]{2,}"
SKU = r"[A-Z]{3}-[0-9]{4}"
SAFE_MAX = 9_007_199_254_740_991


class Estado(Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    EN_PROCESO = "en_proceso"


class Prioridad(Enum):
    BAJA = 1
    MEDIA = 2
    ALTA = 3


@dataclass
class Shirt:
    size: Annotated[str, Pattern(r"XS|S|M|L|XL", message="XS, S, M, L or XL"),
                    Label("Size")]
    color: Annotated[str, Min(1), Label("Color")]


@dataclass
class Mug:
    capacity_ml: Annotated[int, Min(50), Max(2000), Label("Capacity in ml")]
    color: Annotated[str, Min(1), Label("Color")]


@dataclass
class Address:
    street: Annotated[str, Min(1), Label("Street and number")]
    city: Annotated[str, Min(1), Label("City")]
    postal_code: Annotated[str, Pattern(r"[0-9]{5}", message="Five digits"),
                           Label("Postal code")]


@dataclass
class Ticket:
    code: Annotated[str, Pattern(r"[A-Z]{2}-[0-9]{3}", message="Format AB-123"),
                    Label("Code")]
    seats: Annotated[int, Min(1), Max(4), Label("Seats")]


def str_plain(comment: str) -> None:
    pass


def str_labelled(
    comment: Annotated[str, Label("Comment"),
                       Description("The label and this line come from the schema")],
) -> None:
    pass


def str_min(value: Annotated[str, Min(1), Label("At least one character")]) -> None:
    pass


def str_max(value: Annotated[str, Max(5), Label("At most five characters")]) -> None:
    pass


def str_range(value: Annotated[str, Min(2), Max(4), Label("Between two and four")]) -> None:
    pass


def str_exact(value: Annotated[str, Min(0), Max(0), Label("Only the empty string")]) -> None:
    pass


def str_pattern(
    value: Annotated[str, Pattern(EMAIL, message="An email, like ana@company.com"),
                     Label("With a pattern and a message")],
) -> None:
    pass


def str_pattern_silent(
    value: Annotated[str, Pattern(r"[0-9]{4}"), Label("With a pattern and no message")],
) -> None:
    pass


def str_default(
    value: Annotated[str, Label("With a default")] = "prefilled text",
) -> None:
    pass


def str_placeholder(
    value: Annotated[str, Placeholder("Type your name"), Label("With a placeholder")],
) -> None:
    pass


def str_password(
    value: Annotated[str, Min(8), IsPassword(), Label("Password")],
) -> None:
    pass


def str_rows(
    value: Annotated[str, Rows(5), Min(10), Placeholder("Tell us what happened"),
                     Label("Long description")],
) -> None:
    pass


def str_choices(
    value: Annotated[str, Choices(values=("red", "green", "blue")),
                     Label("Box color")],
) -> None:
    pass


def str_literal(
    value: Annotated[Literal["yes", "no", "maybe"], Label("Answer")],
) -> None:
    pass


def str_choices_default(
    value: Annotated[str, Choices(values=("red", "green", "blue")),
                     Label("With one chosen by default")] = "green",
) -> None:
    pass


def int_plain(value: Annotated[int, Label("No constraints")]) -> None:
    pass


def int_min(value: Annotated[int, Min(0), Label("Zero or more")]) -> None:
    pass


def int_max(value: Annotated[int, Max(10), Label("Ten or less")]) -> None:
    pass


def int_exclusive(
    value: Annotated[int, Min(0, exclusive=True), Max(10, exclusive=True),
                     Label("Greater than 0 and less than 10")],
) -> None:
    pass


def int_multiple(value: Annotated[int, MultipleOf(5), Label("Multiples of five")]) -> None:
    pass


def int_everything(
    value: Annotated[int, Min(10), Max(100), MultipleOf(10),
                     Label("Between 10 and 100, in tens")],
) -> None:
    pass


def int_default(
    value: Annotated[int, Min(1), Max(5), Label("With a default")] = 3,
) -> None:
    pass


def int_safe(
    value: Annotated[int, Label("The largest exact integer in JavaScript")] = SAFE_MAX,
) -> None:
    pass


def int_placeholder(
    value: Annotated[int, Placeholder("0"), Label("Integer with a placeholder")],
) -> None:
    pass


def int_step(
    value: Annotated[int, Min(0), Max(1000), Step(50),
                     Label("Steps by 50, but accepts any number")],
) -> None:
    pass


def int_step_and_multiple(
    value: Annotated[int, MultipleOf(25), Step(25),
                     Label("The arrows step by 25 and it must be a multiple of 25")],
) -> None:
    pass


def int_slider(
    value: Annotated[int, Min(0), Max(100), Step(5), Slider(),
                     Label("With the value on show")] = 50,
) -> None:
    pass


def int_slider_quiet(
    value: Annotated[int, Min(1), Max(10), Slider(show_value=False),
                     Label("Without showing the number")] = 5,
) -> None:
    pass


def int_choices(
    value: Annotated[int, Choices(values=(10, 20, 50, 100)),
                     Label("Amount in euros")],
) -> None:
    pass


def int_literal(value: Annotated[Literal[1, 2, 3], Label("Priority")]) -> None:
    pass


def float_plain(value: float) -> None:
    pass


def float_labelled(
    value: Annotated[float, Label("Temperature"),
                     Description("The label and this line come from the schema")],
) -> None:
    pass


def float_bounds(
    value: Annotated[float, Min(0.0), Max(1.0), Label("Between 0 and 1 inclusive")],
) -> None:
    pass


def float_exclusive(
    value: Annotated[float, Min(0.0, exclusive=True), Label("Strictly greater than 0")],
) -> None:
    pass


def float_choices(
    value: Annotated[float, Choices(values=(0.25, 0.5, 0.75, 1.0)), Label("A fraction")],
) -> None:
    pass


def float_step(
    value: Annotated[float, Min(0.0), Max(10.0), Step(0.1),
                     Label("Steps by 0.1, but accepts any number")],
) -> None:
    pass


def float_default(
    value: Annotated[float, Min(0.0), Max(1.0), Label("With a default")] = 0.5,
) -> None:
    pass


def opt_float(value: Annotated[float, Min(0.0), Label("Optional float")] | None) -> None:
    pass


def list_float(value: Annotated[list[float], Label("List of floats")]) -> None:
    pass


def union_int_float(value: Annotated[int | float, Label("Integer or float")]) -> None:
    pass


def date_plain(value: date) -> None:
    pass


def date_labelled(
    value: Annotated[date, Label("Delivery date"),
                     Description("The label and this line come from the schema")],
) -> None:
    pass


def date_bounds(
    value: Annotated[date, Min(date(2026, 1, 1)), Max(date(2026, 12, 31)),
                     Label("Some day in 2026")],
) -> None:
    pass


def date_exclusive(
    value: Annotated[date, Min(date(2026, 1, 1), exclusive=True),
                     Label("After new year's day")],
) -> None:
    pass


def date_choices(
    value: Annotated[date, Choices(values=(date(2026, 3, 20), date(2026, 6, 21),
                                           date(2026, 9, 22), date(2026, 12, 21))),
                     Label("First day of a season")],
) -> None:
    pass


def date_default(
    value: Annotated[date, Label("With a default")] = date(2026, 7, 22),
) -> None:
    pass


def opt_date(value: Annotated[date, Label("Optional date")] | None) -> None:
    pass


def list_date(value: Annotated[list[date], Label("List of dates")]) -> None:
    pass


def union_str_date(value: Annotated[str | date, Label("Text or a date")]) -> None:
    pass


def time_plain(value: time) -> None:
    pass


def time_labelled(
    value: Annotated[time, Label("Start time"),
                     Description("The label and this line come from the schema")],
) -> None:
    pass


def time_bounds(
    value: Annotated[time, Min(time(9, 0)), Max(time(17, 0)), Label("Office hours")],
) -> None:
    pass


def time_exclusive(
    value: Annotated[time, Min(time(9, 0), exclusive=True),
                     Label("Strictly after 9:00")],
) -> None:
    pass


def time_choices(
    value: Annotated[time, Choices(values=(time(9, 0), time(12, 30), time(17, 0))),
                     Label("Appointment slot")],
) -> None:
    pass


def time_default(
    value: Annotated[time, Label("With a default")] = time(14, 30),
) -> None:
    pass


def opt_time(value: Annotated[time, Label("Optional time")] | None) -> None:
    pass


def list_time(value: Annotated[list[time], Label("List of times")]) -> None:
    pass


def bool_plain(agree: bool) -> None:
    pass


def bool_labelled(
    agree: Annotated[bool, Label("I agree to the terms")],
) -> None:
    pass


def bool_default_true(
    agree: Annotated[bool, Label("Checked by default")] = True,
) -> None:
    pass


def bool_optional(
    agree: Annotated[bool, Label("Optional checkbox")] | None,
) -> None:
    pass


def bool_optional_toggle(
    agree: Annotated[bool | None, OptionalToggle(True),
                     Label("Starts on and unchecked")],
) -> None:
    pass


def list_bool(flags: Annotated[list[bool], Label("List of checkboxes")]) -> None:
    pass


def union_str_bool(value: Annotated[str | bool, Label("Text or a checkbox")]) -> None:
    pass


def enum_plain(value: Estado) -> None:
    pass


def enum_labelled(
    value: Annotated[Estado, Label("Order status"),
                     Description("The label and this line come from the schema")],
) -> None:
    pass


def enum_default(
    value: Annotated[Estado, Label("With a default")] = Estado.EN_PROCESO,
) -> None:
    pass


def opt_enum(value: Annotated[Estado, Label("Optional status")] | None) -> None:
    pass


def list_enum(value: Annotated[list[Estado], Label("List of statuses")]) -> None:
    pass


def union_str_enum(value: Annotated[str | Estado, Label("Text or a status")]) -> None:
    pass


def union_two_enums(
    value: Annotated[Estado | Prioridad, Label("Status or priority")],
) -> None:
    pass


@dataclass
class Profile:
    name: Annotated[str, Min(1), Label("Name")]
    avatar: Annotated[str, IsPathFile(extensions=(".jpg", ".png")), Label("Avatar")]


@dataclass
class Album:
    title: Annotated[str, Min(1), Label("Title")]
    photos: Annotated[list[Annotated[str, IsPathFile(extensions=(".jpg", ".png"))]],
                      Min(1), Max(4), Label("Photos")]


def file_plain(document: Annotated[str, IsPathFile(), Label("Any file")]) -> None:
    pass


def file_extensions(
    document: Annotated[str, IsPathFile(extensions=(".pdf", ".png", ".jpg")),
                        Label("PDF or image")],
) -> None:
    pass


def file_optional(
    document: Annotated[str, IsPathFile(), Label("Optional file")] | None,
) -> None:
    pass


def list_file(
    documents: Annotated[list[Annotated[str, IsPathFile(extensions=(".pdf",))]],
                         Min(1), Max(3), Label("Between one and three PDFs")],
) -> None:
    pass


def color_plain(value: Annotated[Color, Label("Favourite colour")]) -> None:
    pass


def color_default(
    value: Annotated[Color, Label("With a default")] = "#ff5733",
) -> None:
    pass


def color_optional(value: Annotated[Color, Label("Optional colour")] | None) -> None:
    pass


def color_list(value: Annotated[list[Color], Label("Palette")]) -> None:
    pass


def email_plain(value: Email) -> None:
    pass


def email_labelled(value: Annotated[Email, Label("Contact email")]) -> None:
    pass


def opt_str_plain(value: Annotated[str, Label("Optional with no default")] | None) -> None:
    pass


def opt_str_none(
    value: Annotated[str, Label("Default None")] | None = None,
) -> None:
    pass


def opt_str_value(
    value: Annotated[str, Label("Default with a value")] | None = "hello",
) -> None:
    pass


def opt_toggle_off(
    value: Annotated[str | None, OptionalToggle(False), Label("The schema turns it off")],
) -> None:
    pass


def opt_toggle_on(
    value: Annotated[str | None, OptionalToggle(True), Label("The schema turns it on")],
) -> None:
    pass


def opt_toggle_off_value(
    value: Annotated[str | None, OptionalToggle(False),
                     Label("Off, but with text inside")] = "prefilled text",
) -> None:
    pass


def opt_toggle_on_none(
    value: Annotated[str | None, OptionalToggle(True),
                     Label("On with a None default")] = None,
) -> None:
    pass


def opt_toggle_on_value(
    value: Annotated[str | None, OptionalToggle(True),
                     Label("On and with a value")] = "both in agreement",
) -> None:
    pass


def opt_toggle_int_value(
    value: Annotated[int | None, OptionalToggle(False),
                     Label("Integer off with a default")] = 42,
) -> None:
    pass


def opt_int(value: Annotated[int, Min(0), Label("Optional integer")] | None) -> None:
    pass


def list_str(value: Annotated[list[str], Label("List of strings")]) -> None:
    pass


def list_int(
    value: Annotated[list[Annotated[int, Min(0)]], Label("List of non-negative integers")],
) -> None:
    pass


def list_str_default(
    value: Annotated[list[str], Label("With two rows by default")] = ["first", "second"],
) -> None:
    pass


def list_empty_default(
    value: Annotated[list[str], Label("With an empty default")] = [],
) -> None:
    pass


def list_nested(value: Annotated[list[list[str]], Label("Lists inside lists")]) -> None:
    pass


def list_of_optional(
    value: Annotated[list[str | None], Label("Each row can be None")],
) -> None:
    pass


def list_optional(
    value: Annotated[list[str], Label("The whole list is optional")] | None,
) -> None:
    pass


def list_min(value: Annotated[list[str], Min(2), Label("At least two")]) -> None:
    pass


def list_max(value: Annotated[list[str], Max(3), Label("At most three")]) -> None:
    pass


def list_range(value: Annotated[list[str], Min(1), Max(3), Label("Between one and three")]) -> None:
    pass


def list_locked_min(
    value: Annotated[list[str], Min(2),
                     Label("Starts at the minimum")] = ["first", "second"],
) -> None:
    pass


def list_locked_max(
    value: Annotated[list[str], Max(2),
                     Label("Starts at the maximum")] = ["first", "second"],
) -> None:
    pass


def union_scalars(value: Annotated[str | int, Label("Text or number")]) -> None:
    pass


def union_scalars_optional(
    value: Annotated[str | int | None, Label("Text, number or nothing")],
) -> None:
    pass


def union_in_list(value: Annotated[list[str | int], Label("Each row chooses")]) -> None:
    pass


def union_of_lists(
    value: Annotated[list[str] | list[int], Label("Choose the whole list")],
) -> None:
    pass


def union_of_nested_lists(
    value: Annotated[list[list[str]] | list[list[int]], Label("Nested unions")],
) -> None:
    pass


def union_mixed_forms(
    value: Annotated[list[str | int] | list[str] | list[int],
                     Label("Both forms in the same union")],
) -> None:
    pass


def list_of_union_of_lists(
    value: Annotated[list[list[str] | list[int]],
                     Label("Each row is a list that chooses its type")],
) -> None:
    pass


def union_of_lists_default(
    value: Annotated[list[str] | list[int], Label("With a default on the int branch")] = [1, 2],
) -> None:
    pass


def dc_one(value: Annotated[Shirt, Label("A standalone dataclass")]) -> None:
    pass


def dc_nested(
    customer: Annotated[str, Min(1), Label("Customer")],
    address: Annotated[Address, Label("Delivery address")],
) -> None:
    pass


def dc_defaults(
    value: Annotated[Address, Label("Nested and prefilled")] = Address(
        "350 Fifth Ave", "New York", "10001"),
) -> None:
    pass


def dc_optional_field(
    name: Annotated[str, Min(1), Label("Name")],
    age: Annotated[int, Min(0), Label("Age")] | None = None,
) -> None:
    pass


def dc_union(value: Annotated[Shirt | Mug, Label("Shirt or mug")]) -> None:
    pass


def dc_list(value: Annotated[list[Shirt], Label("Several shirts")]) -> None:
    pass


def dc_list_union(
    value: Annotated[list[Shirt | Mug], Label("Each row chooses its type")],
) -> None:
    pass


def dc_union_lists(
    value: Annotated[list[Shirt] | list[Mug], Label("The whole list chooses")],
) -> None:
    pass


def dc_mixed(
    value: Annotated[Shirt | Mug | list[str] | list[int],
                     Label("Inline and wrapped in the same union")],
) -> None:
    pass


def boundary_str_min_optional(
    value: Annotated[str, Min(1), Label("Constraint inside, None outside")] | None,
) -> None:
    pass


def boundary_optional_around(
    value: Annotated[str | None, Min(1), Label("Metadata around the union")],
) -> None:
    pass


def boundary_label_union(
    value: Annotated[str | int, Label("The field's label, not the branches'")],
) -> None:
    pass


def boundary_metadata_branch(value: Annotated[str, Min(3)] | int) -> None:
    pass


def boundary_item_constraint(
    value: Annotated[list[Annotated[str, Min(1)]], Label("Constraint on each row")],
) -> None:
    pass


def boundary_list_constraint(
    value: Annotated[list[str], Min(1), Label("Constraint on the list")],
) -> None:
    pass


def boundary_list_in_optional(
    value: Annotated[list[Annotated[int, Min(0)]], Min(1),
                     Label("List with a minimum, inside an optional")] | None,
) -> None:
    pass


def boundary_struct_in_list(
    value: Annotated[list[Ticket], Label("Constrained dataclass per row")],
) -> None:
    pass


SECTIONS = [
    ("str", "Strings",
     "A str always represents a value, even \"\". What decides whether it is "
     "valid are the constraints.",
     [
         ("str-plain", "Plain str",
          "No Label: the field name shows through. Send it empty: the core "
          "accepts it.",
          str_plain, ()),
         ("str-labelled", "Label and Description",
          "The label is not the field name, and the description comes down "
          "from the schema.",
          str_labelled, ()),
         ("str-min", "Min(1)",
          "\"\" stops being valid, but because of a constraint, not because it "
          "is empty.",
          str_min, ()),
         ("str-max", "Max(5)",
          "Type six characters. Empty is still valid.",
          str_max, ()),
         ("str-range", "Min(2) and Max(4)",
          "Both limits at once.",
          str_range, ()),
         ("str-exact", "Min(0) and Max(0)",
          "Only the empty string is allowed. Type a letter and it breaks.",
          str_exact, ()),
         ("str-pattern", "Pattern with a message",
          "The message shows under the field as you type, not on open.",
          str_pattern, ()),
         ("str-pattern-silent", "Pattern without a message",
          "Since the Pattern carries no message of its own, it uses the "
          "general WebConfig message. The match must span the whole string.",
          str_pattern_silent, ()),
         ("str-default", "With a default",
          "Opens prefilled and untouched. The default is certified by the "
          "core.",
          str_default, ()),
         ("str-placeholder", "Placeholder",
          "Helper text inside the control. It is not a value: the JSON is "
          "still \"\".",
          str_placeholder, ()),
         ("str-password", "IsPassword",
          "The same str, hidden. Min(8) still validates and the value travels "
          "the same.",
          str_password, ()),
         ("str-rows", "Rows(5)",
          "Turns into a textarea. Keeps Min, placeholder and messages.",
          str_rows, ()),
         ("str-choices", "Choices",
          "A closed selection: a StrChoiceWidget, not a text field. You cannot "
          "type anything outside the list.",
          str_choices, ()),
         ("str-literal", "Literal[str]",
          "The core compiles it to Choices, so the same widget appears.",
          str_literal, ()),
         ("str-choices-default", "Choices with a default",
          "Opens on the chosen option with no placeholder in front.",
          str_choices_default, ()),
     ]),
    ("int", "Integers",
     "An empty int does not represent anything yet; 0 is a value. Decimals "
     "and integers JavaScript cannot represent are rejected.",
     [
         ("int-plain", "Plain int",
          "Empty is not 0. Type 0 and compare. Try 1.5 and a huge number.",
          int_plain, ()),
         ("int-min", "Min(0)",
          "Try -1.",
          int_min, ()),
         ("int-max", "Max(10)",
          "Try 11.",
          int_max, ()),
         ("int-exclusive", "Exclusive bounds",
          "Greater than 0 and less than 10: the plan translates it to min=1 "
          "and max=9.",
          int_exclusive, ()),
         ("int-multiple", "MultipleOf(5)",
          "Try 7. MultipleOf validates, but does not change the visual step of "
          "the control.",
          int_multiple, ()),
         ("int-everything", "Everything together",
          "Range and multiple at once: 10, 20, 30… up to 100.",
          int_everything, ()),
         ("int-default", "With a default",
          "Opens with 3 already set.",
          int_default, ()),
         ("int-safe", "The largest exact integer",
          "9007199254740991. Add one and the widget flags it: JavaScript can "
          "no longer represent it.",
          int_safe, ()),
         ("int-placeholder", "Placeholder",
          "Helper text inside the control, without being a value.",
          int_placeholder, ()),
         ("int-step", "Step(50)",
          "The arrows step by 50, but 37 typed by hand is valid: Step is "
          "presentation, not validation.",
          int_step, ()),
         ("int-step-multiple", "Step alongside MultipleOf",
          "Now it does validate: the arrows step by 25 and a 30 typed by hand "
          "is flagged.",
          int_step_and_multiple, ()),
         ("int-slider", "Slider with the value on show",
          "The same integer with another control. It respects min, max and "
          "step.",
          int_slider, ()),
         ("int-slider-quiet", "Slider without showing the value",
          "Slider(show_value=False): the number is not drawn.",
          int_slider_quiet, ()),
         ("int-choices", "Choices",
          "A closed selection of integers: IntChoiceWidget. value() returns "
          "the exact integer, not the select's text.",
          int_choices, ()),
         ("int-literal", "Literal[int]",
          "Compiled to Choices by the core.",
          int_literal, ()),
     ]),
    ("float", "Floats",
     "A float is validated by exact type: the core rejects an int where a float "
     "is expected. JSON cannot tell 3 from 3.0, so decode() prepares the "
     "transport before build() — the int typed in the browser arrives as a "
     "float.",
     [
         ("float-plain", "Plain float",
          "No Label: the field name shows through. Type 3 and send it: decode "
          "turns it into 3.0 before the core builds.",
          float_plain, ()),
         ("float-labelled", "Label and Description",
          "The label is not the field name, and the description comes from the "
          "schema.",
          float_labelled, ()),
         ("float-bounds", "Min(0.0) and Max(1.0)",
          "Inclusive bounds: 0 and 1 are accepted, the widget compares the "
          "double directly.",
          float_bounds, ()),
         ("float-exclusive", "Exclusive bound",
          "Min(0.0, exclusive=True): 0 is rejected, but 0.001 is fine. No ±1 "
          "conversion, unlike int.",
          float_exclusive, ()),
         ("float-choices", "Choices",
          "A closed selection of floats: FloatChoiceWidget. The value is the "
          "exact double from the plan, not typed text.",
          float_choices, ()),
         ("float-step", "Step(0.1)",
          "The arrows step by 0.1, but any number typed by hand is valid: Step "
          "is presentation, not validation. 0.1 + 0.2 lands on the honest "
          "double.",
          float_step, ()),
         ("float-default", "With a default",
          "Opens with 0.5 already set. The default is certified by the core.",
          float_default, ()),
         ("float-optional", "float | None",
          "Off sends null; on and empty is not ready.",
          opt_float, ()),
         ("float-list", "list[float]",
          "Each row is an independent float. decode coerces every int in the "
          "list.",
          list_float, ()),
         ("float-union", "int | float",
          "int and float share one JSON number, so both branches travel "
          "wrapped with a $type. decode reads $type: the float branch coerces "
          "$value, the int branch keeps it, and both unwrap to a bare value the "
          "core routes by type.",
          union_int_float, ()),
     ]),
    ("date", "Dates",
     "A date is a native picker whose value is ISO text (2026-07-22). The core "
     "wants a date object, so decode() converts the string with "
     "date.fromisoformat before build(). Bounds compare lexicographically over "
     "the fixed-width ISO form.",
     [
         ("date-plain", "Plain date",
          "No Label: the field name shows through. Pick a day and send it; "
          "decode turns the ISO string into a date.",
          date_plain, ()),
         ("date-labelled", "Label and Description",
          "The label is not the field name, and the description comes from the "
          "schema.",
          date_labelled, ()),
         ("date-bounds", "Min and Max",
          "Between two dates, inclusive. The picker is constrained and the "
          "widget compares the ISO strings.",
          date_bounds, ()),
         ("date-exclusive", "Exclusive bound",
          "Min(..., exclusive=True): like an integer, plan_of converts it by +1 "
          "day, so the node carries the inclusive neighbour (2026-01-02).",
          date_exclusive, ()),
         ("date-choices", "Choices",
          "A closed set of dates: a select over ISO strings. The value is the "
          "exact ISO the plan carried.",
          date_choices, ()),
         ("date-default", "With a default",
          "Opens on 2026-07-22. The default travels as an ISO string and "
          "decode rebuilds the date.",
          date_default, ()),
         ("date-optional", "date | None",
          "Off sends null; on and empty is not ready.",
          opt_date, ()),
         ("date-list", "list[date]",
          "Each row is an independent date picker. decode converts every ISO "
          "string in the list.",
          list_date, ()),
         ("date-union", "str | date",
          "On the wire both are JSON strings, so the branches collide and travel "
          "wrapped with a $type. decode reads $type: the date branch converts "
          "$value with fromisoformat, the str branch keeps it — it never guesses "
          "from the content, so a str that looks like a date stays a str.",
          union_str_date, ()),
     ]),
    ("time", "Times",
     "A time is a native picker (with seconds, step=1) whose value is ISO text "
     "(14:30:00). decode() converts it with time.fromisoformat. Unlike a date, "
     "a time bound keeps its exclusive flag — the core compares directly, with "
     "no ±1 conversion.",
     [
         ("time-plain", "Plain time",
          "No Label: the field name shows through. The control shows seconds.",
          time_plain, ()),
         ("time-labelled", "Label and Description",
          "The label and the description come from the schema.",
          time_labelled, ()),
         ("time-bounds", "Min and Max",
          "Between two times, inclusive. The widget compares the ISO strings "
          "lexicographically.",
          time_bounds, ()),
         ("time-exclusive", "Exclusive bound",
          "Min(time(9, 0), exclusive=True): 09:00:00 is rejected, 09:00:01 is "
          "fine. The flag travels in the node — no conversion, unlike date.",
          time_exclusive, ()),
         ("time-choices", "Choices",
          "A closed set of times: a select over ISO strings.",
          time_choices, ()),
         ("time-default", "With a default",
          "Opens on 14:30:00. The default travels as an ISO string.",
          time_default, ()),
         ("time-optional", "time | None",
          "Off sends null; on and empty is not ready.",
          opt_time, ()),
         ("time-list", "list[time]",
          "Each row is an independent time picker.",
          list_time, ()),
     ]),
    ("bool", "Booleans",
     "A checkbox always represents a value: unchecked is false, checked is "
     "true. It is never empty and never in error, like a closed choice.",
     [
         ("bool-plain", "Plain bool",
          "No Label: the field name shows through. Unchecked sends false.",
          bool_plain, ()),
         ("bool-labelled", "With a Label",
          "The label comes from the schema, not the field name.",
          bool_labelled, ()),
         ("bool-default", "Default True",
          "Opens checked and untouched. The default is certified by the core.",
          bool_default_true, ()),
         ("bool-optional", "bool | None",
          "The field's toggle expresses None; the checkbox inside never "
          "represents empty. Off sends null.",
          bool_optional, ()),
         ("bool-toggle", "bool | None with OptionalToggle(True)",
          "Starts on, with the checkbox unchecked: it sends false, not null.",
          bool_optional_toggle, ()),
         ("bool-list", "list[bool]",
          "Each row is an independent checkbox.",
          list_bool, ()),
         ("bool-union", "str | bool",
          "A checkbox as one branch of a union: it travels flat as true/false.",
          union_str_bool, ()),
     ]),
    ("enum", "Enums",
     "An enum is a closed set of members, like a bool with more than two "
     "options. Each member travels as its name (.name), never its value, and "
     "decode() rebuilds the exact member the core validates by type.",
     [
         ("enum-plain", "Plain enum",
          "No Label: the field name shows through. A select over the member "
          "names, in declaration order.",
          enum_plain, (Estado,)),
         ("enum-labelled", "Label and Description",
          "The label is not the field name, and the description comes from the "
          "schema.",
          enum_labelled, (Estado,)),
         ("enum-default", "With a default",
          "Opens on EN_PROCESO. The default travels as the member name, not its "
          "value.",
          enum_default, (Estado,)),
         ("enum-optional", "Estado | None",
          "Off sends null; on always holds a member, never empty — a closed set "
          "like a bool.",
          opt_enum, (Estado,)),
         ("enum-list", "list[Estado]",
          "Each row is an independent select over the members.",
          list_enum, (Estado,)),
         ("enum-union-str", "str | Estado",
          "On the wire both are JSON strings, so the branches collide and travel "
          "wrapped with a $type. decode reads $type: the enum branch turns the "
          "name into a member, the str branch keeps it — a str that matches a "
          "member name stays a str.",
          union_str_enum, (Estado,)),
         ("enum-union-two", "Estado | Prioridad",
          "Two enums in one union. They share the string transport, so each "
          "branch carries its class name as $type and decode routes by it.",
          union_two_enums, (Estado, Prioridad)),
     ]),
    ("file", "Files",
     "A file field's value is a reference the widget generates locally the moment "
     "you pick a file — the file's name compressed to bare ASCII (15 characters "
     "at most), a UUID and the file's extension. read() carries it "
     "straight away; the reference is a local promise, not proof of storage. The "
     "host reads file()/files() and value() on change and uploads the bytes "
     "labelled with each reference through its own channel. This demo does exactly "
     "that against a toy /upload endpoint and keeps the send button disabled until "
     "every upload confirms. An existing reference (the host's own truth) can be "
     "planted with setValue() or declared as the field's plan default — the same "
     "thing, since the default reaches the widget through setValue(): it shows as "
     "\"Current file\", starts no upload and read() transports it verbatim — see "
     "the \"Editing a record\" case below, where create and edit are the same "
     "form.",
     [
         ("file-plain", "Any file",
          "IsPathFile with no extensions accepts any file. Pick one: the widget "
          "mints a reference (watch read()), the demo uploads the bytes under it, "
          "and only then does send enable. Try ?document=old.txt to prefill a "
          "current file.",
          file_plain, ()),
         ("file-extensions", "With extensions",
          "IsPathFile(extensions=...) fills the input's accept attribute so the "
          "picker filters. A file whose extension slips through anyway mints no "
          "reference and shows the invalid message.",
          file_extensions, ()),
         ("file-optional", "File | None",
          "Off sends null; on with no file is not ready. The off state is the "
          "toggle, never a default.",
          file_optional, ()),
         ("file-list", "list[File]",
          "One multiple input: pick several files in a single dialog and each "
          "mints and uploads its own reference. Min/Max become file-count bounds.",
          list_file, ()),
         ("file-edit", "Editing a record",
          "Create and edit are the same form. This one opens prefilled with a "
          "record: the avatar is an existing reference, shown as \"Current file\" "
          "and not re-uploaded. Change the name and send — build() returns the "
          "Profile with the avatar intact. Press Replace to drop it and pick a new "
          "one, or leave it empty to send null.",
          Profile, ()),
         ("file-list-edit", "Editing a record with a list",
          "The same, with a list[File]. It opens prefilled with several existing "
          "references, each shown as a \"Current file\" line; send returns them "
          "intact. Press Replace to drop the current photos and rebuild the list "
          "with the native input (which resets) and the + button (which adds).",
          Album, ()),
     ]),
    ("types", "Types",
     "`Color` and `Email` are not new types — they are `Annotated[str, "
     "Pattern(...)]` aliases the library ships for convenience. The plan is a "
     "plain str node; only `Color` gets a presentation trick: a StrWidget whose "
     "pattern is the published `COLOR_PATTERN` mounts a colour picker beside the "
     "text, which stays the source of truth.",
     [
         ("color-plain", "Color",
          "A str node with the hex pattern. The picker writes `#rrggbb` into the "
          "text; typing or pasting a valid colour syncs the picker back.",
          color_plain, ()),
         ("color-default", "Color with a default",
          "Opens on #ff5733, certified by the core, with the picker in step.",
          color_default, ()),
         ("color-optional", "Color | None",
          "Off sends null; on it is a colour field like any other.",
          color_optional, ()),
         ("color-list", "list[Color]",
          "Each row is an independent colour field, picker included.",
          color_list, ()),
         ("email-plain", "Email",
          "A format filter, not a validator: a run of non-space characters, an "
          "@, another run, a dot and a 2+ letter suffix. No picker — it is a "
          "plain str node.",
          email_plain, ()),
         ("email-labelled", "Email with a Label",
          "The alias composes with field metadata: the pattern stays on the "
          "node, the label on the field.",
          email_labelled, ()),
     ]),
    ("optional", "Optionals",
     "A switched-off toggle means None. What decides how it opens: the "
     "default first, and if there is an OptionalToggle it wins.",
     [
         ("opt-plain", "No default and no toggle",
          "Nothing turns it off, so it starts on. Switch it off and watch the "
          "JSON.",
          opt_str_plain, ()),
         ("opt-none", "The default decides: None",
          "With no OptionalToggle, the default decides. None opens off.",
          opt_str_none, ()),
         ("opt-value", "The default decides: with a value",
          "The same case the other way round: a default other than None opens "
          "on and prefilled. Switch it off and on: the text is still there.",
          opt_str_value, ()),
         ("opt-toggle-off", "OptionalToggle(False) with no default",
          "There is no default to look at, so the schema's toggle decides.",
          opt_toggle_off, ()),
         ("opt-toggle-on", "OptionalToggle(True) with no default",
          "The opposite: it starts on and pending.",
          opt_toggle_on, ()),
         ("opt-toggle-off-value", "OptionalToggle(False) against a value default",
          "The default would say \"on\", but the toggle wins and opens off. "
          "The text is not lost: switch it on and it appears.",
          opt_toggle_off_value, ()),
         ("opt-toggle-on-none", "OptionalToggle(True) against a None default",
          "The default would say \"off\", but the toggle wins: it opens on and "
          "empty, so it sends \"\" instead of null.",
          opt_toggle_on_none, ()),
         ("opt-toggle-on-value", "OptionalToggle(True) agreeing with the default",
          "Both say the same. It opens on with the value set.",
          opt_toggle_on_value, ()),
         ("opt-toggle-int-value", "The same with an integer",
          "Off because of the toggle, with 42 waiting inside.",
          opt_toggle_int_value, ()),
         ("opt-int", "int | None",
          "Off sends null; on and empty is not ready.",
          opt_int, ()),
     ]),
    ("list", "Lists",
     "An empty list is [], never None. Each row is an independent widget.",
     [
         ("list-str", "list[str]",
          "Add and remove rows. Empty is already a valid value.",
          list_str, ()),
         ("list-int", "list[int]",
          "Each row has its own state: leave one half-done.",
          list_int, ()),
         ("list-default", "With rows by default",
          "Opens with two rows written and untouched.",
          list_str_default, ()),
         ("list-empty-default", "With an empty default",
          "Opens with no rows and is still ready: [] is a value.",
          list_empty_default, ()),
         ("list-nested", "list[list[str]]",
          "Each row is another list with its own buttons.",
          list_nested, ()),
         ("list-optional-item", "list[str | None]",
          "Each row brings its own toggle: a row can be None.",
          list_of_optional, ()),
         ("list-optional", "list[str] | None",
          "Off sends null; on with no rows sends [].",
          list_optional, ()),
         ("list-min", "Min(2)",
          "Starts empty and is not ready yet. Add two rows to reach the "
          "minimum.",
          list_min, ()),
         ("list-max", "Max(3)",
          "On reaching three, the add button is disabled.",
          list_max, ()),
         ("list-range", "Min(1) and Max(3)",
          "Starts empty. The minimum controls when it is ready and the maximum "
          "when it stops allowing new rows.",
          list_range, ()),
         ("list-locked-min", "Locked at the minimum",
          "Opens with exactly the two default rows. Since it is already at the "
          "minimum, it does not allow removing until you add another.",
          list_locked_min, ()),
         ("list-locked-max", "Locked at the maximum",
          "Opens with two rows and Max(2): the add button is born disabled.",
          list_locked_max, ()),
     ]),
    ("union", "Unions",
     "Use the arrows to move between the available modes; one mode is visible "
     "at a time. Depending on where the union sits, you pick once or per "
     "element. The transport format is decided by the plan, not the widget.",
     [
         ("union-scalars", "str | int",
          "Different types: the core routes on its own and the JSON travels "
          "flat.",
          union_scalars, ()),
         ("union-scalars-optional", "str | int | None",
          "The same union, plus the toggle.",
          union_scalars_optional, ()),
         ("union-in-list", "list[str | int]",
          "The choice is inside: you can mix strings and numbers.",
          union_in_list, ()),
         ("union-of-lists", "list[str] | list[int]",
          "The choice is outside: $type + $value, and you cannot mix.",
          union_of_lists, ()),
         ("union-nested-lists", "list[list[str]] | list[list[int]]",
          "The branch identifier spells out the nesting.",
          union_of_nested_lists, ()),
         ("union-mixed-forms", "list[str | int] | list[str] | list[int]",
          "Both forms living together. Pick the first branch and you can mix "
          "inside; pick either of the other two and the list is a single "
          "type. All three travel wrapped, and $type says which is which.",
          union_mixed_forms, ()),
         ("union-list-of-union-of-lists", "list[list[str] | list[int]]",
          "The other way round: the list is outside and the choice inside. "
          "Each row is a whole list that chooses its type, so each row carries "
          "its $type.",
          list_of_union_of_lists, ()),
         ("union-of-lists-default", "Union with a default",
          "Opens on the int branch because the default is [1, 2], not because "
          "it is the first.",
          union_of_lists_default, ()),
     ]),
    ("dataclass", "Dataclasses",
     "A dataclass becomes a group of fields. Several in the same union are "
     "reached with the mode arrows and carry their $type inside.",
     [
         ("dc-one", "One dataclass",
          "With no union there is no need for a discriminator: the JSON "
          "carries no $type.",
          dc_one, (Shirt,)),
         ("dc-nested", "Nested inside another",
          "The group is drawn inside the field that contains it.",
          dc_nested, (Address,)),
         ("dc-defaults", "Nested with a default",
          "Opens fully prefilled from a core default.",
          dc_defaults, (Address,)),
         ("dc-optional-field", "With an optional field inside",
          "The child's toggle is its own; the parent only summarises.",
          dc_optional_field, ()),
         ("dc-union", "Shirt | Mug",
          "Two dataclasses: the $type travels inside the object.",
          dc_union, (Shirt, Mug)),
         ("dc-list", "list[Shirt]",
          "Each row is a whole dataclass.",
          dc_list, (Shirt,)),
         ("dc-list-union", "list[Shirt | Mug]",
          "Each row chooses and carries its own $type.",
          dc_list_union, (Shirt, Mug)),
         ("dc-union-lists", "list[Shirt] | list[Mug]",
          "The branch decides once; the rows no longer carry $type.",
          dc_union_lists, (Shirt, Mug)),
         ("dc-mixed", "Shirt | Mug | list[str] | list[int]",
          "Two inline branches and two wrapped living together.",
          dc_mixed, (Shirt, Mug)),
     ]),
    ("boundary", "Composition and boundaries",
     "Where each constraint lands when the schema is composed. The first "
     "three cases are not redundant: they put Min on different nodes.",
     [
         ("boundary-str-min-optional", "Annotated[str, Min(1)] | None",
          "The constraint goes inside the str and None stays outside as an "
          "option.",
          boundary_str_min_optional, ()),
         ("boundary-optional-around", "Annotated[str | None, Min(1)]",
          "Metadata around the optional union: the core applies it to the only "
          "real type, never to None.",
          boundary_optional_around, ()),
         ("boundary-label-union", "Annotated[str | int, Label(...)]",
          "Field metadata around a whole union.",
          boundary_label_union, ()),
         ("boundary-metadata-branch", "Annotated[str, Min(3)] | int",
          "Metadata inside one specific branch.",
          boundary_metadata_branch, ()),
         ("boundary-item-constraint", "list[Annotated[str, Min(1)]]",
          "The constraint belongs to each row.",
          boundary_item_constraint, ()),
         ("boundary-list-constraint", "Annotated[list[str], Min(1)]",
          "The constraint belongs to the length of the list.",
          boundary_list_constraint, ()),
         ("boundary-list-in-optional", "List with a minimum inside an optional",
          "Three layers: optional, list length and per-element minimum.",
          boundary_list_in_optional, ()),
         ("boundary-struct-in-list", "Constrained dataclass inside a list",
          "Who shows the error and who only summarises it.",
          boundary_struct_in_list, (Ticket,)),
     ]),
]

CONFIGS = {}
