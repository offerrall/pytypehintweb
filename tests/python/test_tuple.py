"""Tuples that are lists.

On the wire a tuple is a JSON array, so the tuples a single item node can
describe travel as the existing `list` plan node: `tuple[X, ...]`, and a fixed
tuple whose positions are all the same. Every other tuple is refused by
plan_of() with its path. The browser never learns the word "tuple": the plan
stays at v 1 and the tuple comes back out of schema.decode(), the one reader of
the portable transport.
"""

import json
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Annotated

import pytest

from pytypehint import (
    FileHint, Max, Min, immutable, signature_of, struct_of,
)
from pytypehintweb import INLINE, PLAIN, WRAPPED, decode, plan_of


Channel = Annotated[float, Min(0.0), Max(1.0)]
Pdf = Annotated[str, FileHint(extensions=(".pdf",))]


@dataclass
class Point:
    x: int
    y: int = 0


@dataclass
class Other:
    x: int
    y: int = 0


class Suit(Enum):
    CLUBS = 1
    HEARTS = 2


def _signature(annotation, *default):
    if default:
        def form(value: annotation = default[0]) -> None: ...
    else:
        def form(value: annotation) -> None: ...

    return signature_of(form)


def _field(annotation, *default):
    return plan_of(_signature(annotation, *default))["fields"][0]


def _node(annotation):
    return _field(annotation)["node"]


def _refusal(annotation, *default) -> str:
    with pytest.raises(TypeError) as error:
        _field(annotation, *default)

    return str(error.value)


# ------------------------------------------------------------- variadic tuples

@pytest.mark.parametrize("item", [
    int, str, float, bool, date, Suit, Channel, Point, int | str, int | None,
    list[int], Point | Other,
])
def test_a_variadic_tuple_is_the_list_node_of_its_item(item):
    assert _node(tuple[item, ...]) == _node(list[item])


def test_a_variadic_tuple_node_carries_exactly_the_list_keys():
    node = _node(tuple[int, ...])

    assert list(node) == ["kind", "addLabel", "removeLabel", "minItems",
                          "maxItems", "minMessage", "maxMessage", "item"]
    assert node["kind"] == "list"
    assert node["minItems"] is None
    assert node["maxItems"] is None
    assert node["item"]["kind"] == "int"


def test_the_plan_version_does_not_move():
    assert plan_of(_signature(tuple[int, ...]))["v"] == 1


def test_variadic_bounds_become_the_item_limits():
    node = _node(Annotated[tuple[float, ...], Min(1), Max(16)])

    assert node["minItems"] == 1
    assert node["maxItems"] == 16
    assert node == _node(Annotated[list[float], Min(1), Max(16)])


def test_a_variadic_bound_outside_the_safe_integers_is_refused():
    message = _refusal(Annotated[tuple[int, ...], Max(2 ** 60)])

    assert message.startswith("fields.value: Tuple.max: ")
    assert "safe integer range" in message

    assert _refusal(Annotated[tuple[int, ...], Min(2 ** 60)]).startswith(
        "fields.value: Tuple.min: ")


def test_item_constraints_stay_on_the_item():
    node = _node(Annotated[tuple[Annotated[int, Min(3)], ...], Min(2)])

    assert node["minItems"] == 2
    assert node["item"]["options"]["min"] == 3


def test_an_optional_item_is_an_optional_node():
    node = _node(tuple[int | None, ...])

    assert node["item"]["kind"] == "optional"
    assert node["item"]["node"]["kind"] == "int"


# ---------------------------------------------------- fixed, same-typed tuples

def test_a_fixed_tuple_of_one_type_is_a_list_of_exactly_that_size():
    node = _node(tuple[float, float, float])

    assert node["kind"] == "list"
    assert node["minItems"] == 3
    assert node["maxItems"] == 3
    assert node["item"] == _node(list[float])["item"]


def test_a_fixed_tuple_keeps_the_constraints_of_its_shared_position():
    node = _node(tuple[Channel, Channel, Channel, Channel])

    assert node["minItems"] == 4
    assert node["maxItems"] == 4
    assert node["item"]["kind"] == "float"
    assert node["item"]["options"]["min"] == 0.0
    assert node["item"]["options"]["max"] == 1.0


def test_a_tuple_of_one_position_is_a_list_of_one():
    node = _node(tuple[int])

    assert (node["minItems"], node["maxItems"]) == (1, 1)


@pytest.mark.parametrize("annotation, item", [
    (tuple[Point, Point], Point),
    (tuple[Suit, Suit, Suit], Suit),
    (tuple[int | str, int | str], int | str),
    (tuple[int | None, int | None], int | None),
    (tuple[list[Point], list[Point]], list[Point]),
    (tuple[tuple[Point, ...], tuple[Point, ...]], tuple[Point, ...]),
    (tuple[tuple[int, int], tuple[int, int]], tuple[int, int]),
    (tuple[Annotated[str, Min(2)], Annotated[str, Min(2)]],
     Annotated[str, Min(2)]),
])
def test_positions_that_compile_to_the_same_shape_share_one_item(
        annotation, item):
    node = _node(annotation)

    size = len(annotation.__args__)

    assert (node["minItems"], node["maxItems"]) == (size, size)
    assert node["item"] == _node(list[item])["item"]


def test_a_fixed_tuple_own_bounds_add_nothing_to_its_size():
    # The core refuses bounds that exclude the size, so the ones it admits can
    # only repeat it. They are not read: not even an unsafe Max refuses a plan.
    plain = _node(tuple[int, int])

    assert _node(Annotated[tuple[int, int], Min(1), Max(5)]) == plain
    assert _node(Annotated[tuple[int, int], Max(2 ** 60)]) == plain

    with pytest.raises(ValueError, match="length bounds exclude fixed size 2"):
        _signature(Annotated[tuple[int, int], Min(3)])


# ------------------------------------------------------------------- refusals

_SUPPORTED = ("tuple[X, ...] and fixed tuples whose positions are all the same "
              "are supported")


def test_the_empty_tuple_is_refused():
    assert _refusal(tuple[()]) == (
        "fields.value: tuple[()] is not supported: an empty tuple has no "
        "control to show; " + _SUPPORTED)


@pytest.mark.parametrize("annotation, option_id", [
    (tuple[int, str], "tuple[int, str]"),
    (tuple[int, int, str], "tuple[int, int, str]"),
    (tuple[Channel, float], "tuple[float, float]"),
    (tuple[Annotated[int, Min(0)], Annotated[int, Min(1)]], "tuple[int, int]"),
    (tuple[int | str, str | int], "tuple[int | str, str | int]"),
    (tuple[int, int | None], "tuple[int, int | None]"),
    (tuple[Point, Other], "tuple[Point, Other]"),
    (tuple[list[int], list[str]], "tuple[list[int], list[str]]"),
    (tuple[tuple[int, ...], tuple[int, int]],
     "tuple[tuple[int, ...], tuple[int, int]]"),
])
def test_positions_that_differ_are_refused(annotation, option_id):
    assert _refusal(annotation) == (
        f"fields.value: {option_id}: positions that differ in type or "
        f"constraints are not supported yet; " + _SUPPORTED)


def test_a_refused_tuple_is_named_by_its_path():
    @dataclass
    class Holder:
        pair: tuple[int, str]

    cases = [
        (list[tuple[int, str]], "fields.value.item: "),
        (tuple[tuple[int, str], ...], "fields.value.item: "),
        (int | tuple[int, str], "fields.value[tuple[int, str]]: "),
        (Holder, "fields.value.pair: "),
        (list[tuple[()]], "fields.value.item: tuple[()] is not supported"),
    ]

    for annotation, prefix in cases:
        assert _refusal(annotation).startswith(prefix)


def test_a_refused_tuple_is_refused_whatever_its_default():
    assert "positions that differ" in _refusal(tuple[int, str], (1, "a"))
    assert "tuple[()] is not supported" in _refusal(tuple[()], ())


def test_per_item_checks_reach_a_tuple_item():
    from pytypehint import Slider

    message = _refusal(tuple[Annotated[int, Min(2 ** 60)], ...])
    assert message.startswith("fields.value.item: Int.min: ")

    message = _refusal(tuple[Annotated[float, Min(0.0), Max(1.0), Slider()],
                             Annotated[float, Min(0.0), Max(1.0), Slider()]])
    assert message == "fields.value.item: Float.slider is not supported yet"


def test_a_dataclass_that_contains_itself_through_a_tuple_is_refused():
    @dataclass
    class Node:
        children: "tuple[Node, ...]" = ()

    @dataclass
    class Pair:
        both: "tuple[Pair, Pair] | None" = None

    Node.__annotations__["children"] = tuple[Node, ...]
    Pair.__annotations__["both"] = tuple[Pair, Pair] | None

    with pytest.raises(TypeError) as error:
        plan_of(Node)
    assert str(error.value).startswith(
        "fields.children.item: Node contains itself")

    with pytest.raises(TypeError) as error:
        plan_of(Pair)
    assert str(error.value).startswith("fields.both.item: Pair contains itself")


# --------------------------------------------------------------------- unions

def _modes(annotation):
    return {branch["value"]: branch["mode"]
            for branch in _node(annotation)["branches"]}


def test_a_tuple_and_a_list_collide_on_the_wire():
    assert _modes(list[int] | tuple[int, ...]) == {
        "list[int]": WRAPPED, "tuple[int, ...]": WRAPPED}


def test_two_tuples_collide_on_the_wire():
    assert _modes(tuple[int, ...] | tuple[str, ...]) == {
        "tuple[int, ...]": WRAPPED, "tuple[str, ...]": WRAPPED}
    assert _modes(tuple[int, ...] | tuple[int, int]) == {
        "tuple[int, ...]": WRAPPED, "tuple[int, int]": WRAPPED}


def test_a_lone_tuple_in_a_union_travels_plain():
    assert _modes(tuple[int, ...] | int | str) == {
        "tuple[int, ...]": PLAIN, "int": PLAIN, "str": PLAIN}
    assert _modes(tuple[int, ...] | Point) == {
        "tuple[int, ...]": PLAIN, "Point": PLAIN}


def test_a_tuple_does_not_disturb_the_other_groups():
    assert _modes(tuple[int, ...] | list[int] | int | float | Point | Other) == {
        "tuple[int, ...]": WRAPPED, "list[int]": WRAPPED,
        "int": WRAPPED, "float": WRAPPED,
        "Point": INLINE, "Other": INLINE}


@pytest.mark.parametrize("annotation", [
    list[int] | tuple[int, ...],
    tuple[int, ...] | tuple[str, ...],
    tuple[int, ...] | tuple[int, int],
    tuple[int, ...] | int,
    tuple[float, float] | list[float] | float | None,
])
def test_the_modes_are_the_ones_the_core_writes(annotation):
    # Struct.encode() is the core writing its own portable transport. A branch
    # the plan sends wrapped must be one the core wraps, under the same $type.
    schema = _signature(annotation)
    values = {"tuple[int, ...]": (1, 2), "tuple[str, ...]": ("a",),
              "tuple[int, int]": (1, 2), "list[int]": [1], "int": 3,
              "tuple[float, float]": (1.5, 2.5), "list[float]": [1.5],
              "float": 1.5}

    for branch in plan_of(schema)["fields"][0]["node"]["branches"]:
        value = values[branch["value"]]

        if branch["value"] == "tuple[int, int]" and "..." in str(annotation):
            # (1, 2) is claimed by the variadic branch declared first.
            continue

        written = schema.encode({"value": value})["value"]

        if branch["mode"] == WRAPPED:
            assert written == {"$type": branch["value"],
                               "$value": list(value) if type(value) is tuple
                               else value}
        else:
            assert written == (list(value) if type(value) is tuple else value)


# ------------------------------------------------------------------- defaults

def test_a_tuple_default_is_written_as_an_array():
    field = _field(tuple[int, ...], (1, 2, 3))

    assert field["hasDefault"] is True
    assert field["default"] == [1, 2, 3]
    assert _field(tuple[int, ...], ())["default"] == []
    assert _field(tuple[float, float], (0.5, 1.5))["default"] == [0.5, 1.5]


def test_a_tuple_without_a_default_has_none():
    field = _field(tuple[int, int])

    assert field["hasDefault"] is False
    assert "default" not in field


def test_an_optional_tuple_default_none_starts_disabled():
    field = _field(tuple[int, int] | None, None)

    assert field["optional"] is True
    assert field["enabled"] is False
    assert field["default"] is None


def test_default_items_are_written_like_any_item():
    assert _field(tuple[date, ...], (date(2026, 1, 2),))["default"] == [
        "2026-01-02"]
    assert _field(tuple[Suit, Suit], (Suit.HEARTS, Suit.CLUBS))["default"] == [
        "HEARTS", "CLUBS"]
    assert _field(tuple[Point, ...], (Point(1), Point(2, 3)))["default"] == [
        {"x": 1, "y": 0}, {"x": 2, "y": 3}]
    assert _field(tuple[int | None, ...], (1, None))["default"] == [1, None]
    assert _field(tuple[int | str, ...], (1, "a"))["default"] == [
        {"branch": 0, "value": 1}, {"branch": 1, "value": "a"}]


def test_nested_tuple_defaults_are_nested_arrays():
    field = _field(tuple[tuple[int, int], ...], ((1, 2), (3, 4)))

    assert field["default"] == [[1, 2], [3, 4]]
    assert field["node"]["item"]["minItems"] == 2

    field = _field(list[tuple[float, float]], [(0.5, 1.5)])
    assert field["default"] == [[0.5, 1.5]]


def test_a_default_tuple_selects_its_branch():
    field = _field(list[int] | tuple[int, ...], (1, 2))
    assert field["default"] == {"branch": 1, "value": [1, 2]}

    field = _field(list[int] | tuple[int, ...], [1, 2])
    assert field["default"] == {"branch": 0, "value": [1, 2]}

    field = _field(tuple[int, ...] | tuple[str, ...], ("a",))
    assert field["default"] == {"branch": 1, "value": ["a"]}

    field = _field(int | tuple[int, int] | None, (4, 5))
    assert field["default"] == {"branch": 1, "value": [4, 5]}


def test_a_fixed_branch_only_takes_a_default_of_its_size():
    annotation = tuple[int, int] | tuple[int, ...]

    assert _field(annotation, (1, 2))["default"]["branch"] == 0
    assert _field(annotation, (1, 2, 3))["default"]["branch"] == 1
    assert _field(annotation, ())["default"]["branch"] == 1


def test_the_first_declared_branch_that_accepts_wins_as_in_the_core():
    annotation = tuple[int, ...] | tuple[int, int]
    schema = _signature(annotation, (1, 2))
    field = plan_of(schema)["fields"][0]

    assert field["default"] == {"branch": 0, "value": [1, 2]}
    assert schema.encode({"value": (1, 2)})["value"]["$type"] == (
        field["node"]["branches"][0]["value"])


def test_per_item_default_checks_reach_a_tuple_item():
    message = _refusal(tuple[int, ...], (1, 2 ** 60))
    assert message.startswith("fields.value[1]: Int default: ")

    message = _refusal(tuple[float, float], (0.5, 1e-9))
    assert message.startswith("fields.value[1]: Float default: ")

    message = _refusal(tuple[tuple[int, int], ...], ((1, 2), (3, 2 ** 60)))
    assert message.startswith("fields.value[1][1]: Int default: ")


# ---------------------------------------------------------------------- files

def test_a_tuple_of_files_is_a_list_of_single_file_nodes():
    node = _node(tuple[Pdf, ...])

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "file"
    assert node["item"]["options"]["multiple"] is False
    assert node["item"] == _node(Pdf)

    fixed = _node(tuple[Pdf, Pdf])
    assert (fixed["minItems"], fixed["maxItems"]) == (2, 2)
    assert fixed["item"] == _node(Pdf)


def test_the_multiple_shortcut_stays_exactly_list_of_file():
    node = _node(list[Pdf])

    assert node["kind"] == "file"
    assert node["options"]["multiple"] is True


def test_a_tuple_of_file_references_is_a_default_like_any_other():
    assert _field(tuple[Pdf, ...], ("a.pdf", "b.pdf"))["default"] == [
        "a.pdf", "b.pdf"]


def _resolve(reference):
    return f"/srv/{reference}"


def _decoded(annotation, value, resolver=_resolve):
    schema = _signature(annotation)
    prepared = decode(schema, {"value": value}, file_resolver=resolver)

    return prepared["value"], schema.build(prepared)["value"]


def test_the_resolver_reaches_the_files_of_a_tuple_and_returns_a_tuple():
    prepared, built = _decoded(tuple[Pdf, ...], ["a.pdf", "b.pdf"])

    assert prepared == ("/srv/a.pdf", "/srv/b.pdf")
    assert type(prepared) is tuple
    assert built == ("/srv/a.pdf", "/srv/b.pdf")

    prepared, built = _decoded(tuple[Pdf, Pdf], ["a.pdf", "b.pdf"])
    assert type(prepared) is tuple
    assert built == ("/srv/a.pdf", "/srv/b.pdf")


def test_the_resolver_is_called_once_per_reference_in_order():
    seen = []

    def resolve(reference):
        seen.append(reference)
        return reference

    _decoded(tuple[Pdf, ...], ["a.pdf", "b.pdf", "c.pdf"], resolve)

    assert seen == ["a.pdf", "b.pdf", "c.pdf"]


def test_without_a_resolver_a_tuple_of_references_comes_back_as_it_is():
    schema = _signature(tuple[Pdf, ...])

    assert decode(schema, {"value": ["a.pdf"]}) == {"value": ("a.pdf",)}


def test_the_resolver_skips_what_is_not_a_file_inside_a_tuple():
    prepared, built = _decoded(tuple[Pdf | None, ...], ["a.pdf", None])
    assert built == ("/srv/a.pdf", None)

    prepared, built = _decoded(tuple[Pdf | int, ...], ["a.pdf", 3])
    assert built == ("/srv/a.pdf", 3)

    prepared, built = _decoded(tuple[str, ...], ["a.pdf"])
    assert built == ("a.pdf",)

    prepared, built = _decoded(tuple[Pdf, ...], [])
    assert prepared == ()


def test_the_resolver_goes_through_nested_tuples_lists_and_dataclasses():
    @dataclass
    class Report:
        document: Pdf
        attachments: tuple[Pdf, ...] = ()

    prepared, built = _decoded(tuple[tuple[Pdf, Pdf], ...],
                               [["a.pdf", "b.pdf"], ["c.pdf", "d.pdf"]])
    assert built == (("/srv/a.pdf", "/srv/b.pdf"), ("/srv/c.pdf", "/srv/d.pdf"))

    prepared, built = _decoded(list[tuple[Pdf, ...]], [["a.pdf"], []])
    assert built == [("/srv/a.pdf",), ()]

    prepared, built = _decoded(tuple[list[Pdf], ...], [["a.pdf"], []])
    assert built == (["/srv/a.pdf"], [])

    prepared, built = _decoded(
        tuple[Report, ...],
        [{"document": "a.pdf", "attachments": ["b.pdf", "c.pdf"]}])
    assert built == (Report("/srv/a.pdf", ("/srv/b.pdf", "/srv/c.pdf")),)


def test_the_resolver_follows_a_tuple_named_beside_a_list():
    # A list and a tuple differ in Python, so the core consumes the wrapper and
    # leaves the exact container; the resolver hands back the same one.
    annotation = list[Pdf] | tuple[Pdf, ...]

    prepared, built = _decoded(
        annotation, {"$type": "tuple[str, ...]", "$value": ["a.pdf"]})
    assert prepared == ("/srv/a.pdf",)
    assert type(built) is tuple

    prepared, built = _decoded(
        annotation, {"$type": "list[str]", "$value": ["a.pdf"]})
    assert prepared == ["/srv/a.pdf"]
    assert type(built) is list


def test_the_resolver_follows_a_wrapper_the_core_kept_between_tuples():
    annotation = tuple[Pdf, ...] | tuple[int, ...]

    prepared, built = _decoded(
        annotation, {"$type": "tuple[str, ...]", "$value": ["a.pdf"]})
    assert prepared == {"$type": "tuple[str, ...]", "$value": ("/srv/a.pdf",)}
    assert built == ("/srv/a.pdf",)

    prepared, built = _decoded(
        annotation, {"$type": "tuple[int, ...]", "$value": [1, 2]})
    assert prepared == {"$type": "tuple[int, ...]", "$value": (1, 2)}
    assert built == (1, 2)


def test_the_resolver_leaves_what_the_core_did_not_route():
    seen = []

    def resolve(reference):
        seen.append(reference)
        return reference

    # A bare array between two tuples names no branch: the core keeps the list.
    schema = _signature(tuple[Pdf, ...] | tuple[int, ...])
    assert decode(schema, {"value": ["a.pdf"]}, file_resolver=resolve) == {
        "value": ["a.pdf"]}

    # Positions past a fixed size belong to no slot; build() reports the length.
    schema = _signature(tuple[Pdf, Pdf])
    prepared = decode(schema, {"value": ["a.pdf", "b.pdf", "c.pdf"]},
                      file_resolver=resolve)
    assert prepared == {"value": ("a.pdf", "b.pdf", "c.pdf")}
    assert seen == ["a.pdf", "b.pdf"]

    with pytest.raises(ValueError, match="expected 2 items, got 3"):
        schema.build(prepared)


def test_the_resolver_reads_each_position_of_a_tuple_the_plan_refuses():
    # decode() serves any compiled schema, not only the ones plan_of() accepts:
    # a host writing its own transport still gets its references resolved.
    prepared, built = _decoded(tuple[Pdf, str, Pdf], ["a.pdf", "b.pdf", "c.pdf"])

    assert built == ("/srv/a.pdf", "b.pdf", "/srv/c.pdf")


def test_a_python_tuple_handed_to_decode_is_resolved_too():
    prepared, built = _decoded(tuple[Pdf, ...], ("a.pdf",))

    assert built == ("/srv/a.pdf",)


# ------------------------------------------------------------------ @immutable

@immutable
class Stop:
    name: str
    at: tuple[float, float] = (0.0, 0.0)


@immutable
class Route:
    tags: tuple[str, ...]
    stops: tuple[Stop, ...] = ()
    color: tuple[Channel, Channel, Channel] = (0.0, 0.5, 1.0)
    bounds: tuple[Stop, Stop] | None = None


def test_an_immutable_model_gets_a_plan():
    fields = {field["name"]: field for field in plan_of(Route)["fields"]}

    assert fields["tags"]["node"]["kind"] == "list"
    assert fields["tags"]["node"]["minItems"] is None
    assert fields["stops"]["node"]["item"]["kind"] == "object"
    assert fields["stops"]["default"] == []
    assert fields["color"]["node"]["minItems"] == 3
    assert fields["color"]["node"]["maxItems"] == 3
    assert fields["color"]["default"] == [0.0, 0.5, 1.0]
    assert fields["bounds"]["optional"] is True
    assert fields["bounds"]["node"]["minItems"] == 2

    at = fields["stops"]["node"]["item"]["fields"][1]
    assert at["default"] == [0.0, 0.0]
    assert (at["node"]["minItems"], at["node"]["maxItems"]) == (2, 2)


def test_an_immutable_model_is_built_from_the_transport():
    schema = struct_of(Route)
    transport = json.loads(json.dumps({
        "tags": ["a", "b"],
        "stops": [{"name": "north", "at": [1, 2.5]}],
        "color": [0, 1, 0.25],
        "bounds": [{"name": "a", "at": [0, 0]}, {"name": "b", "at": [9, 9]}],
    }))

    route = schema.build(decode(schema, transport))

    assert route == Route(
        tags=("a", "b"),
        stops=(Stop(name="north", at=(1.0, 2.5)),),
        color=(0.0, 1.0, 0.25),
        bounds=(Stop(name="a"), Stop(name="b", at=(9.0, 9.0))))
    assert type(route.tags) is tuple
    assert type(route.stops[0].at) is tuple


# ------------------------------------------------- through the browser and back

@dataclass
class Swatch:
    color: tuple[Channel, Channel, Channel, Channel]
    samples: Annotated[tuple[float, ...], Min(1), Max(16)]


def _plans():
    def unions(
        either: list[int] | tuple[int, ...] = (1, 2),
        tuples: tuple[int, ...] | tuple[str, ...] = ("a",),
        fixed: tuple[int, int] | tuple[int, ...] | None = (1, 2, 3),
        mixed: tuple[int, ...] | int | Point = 3,
    ) -> None: ...

    def nested(
        grid: tuple[tuple[int, int], ...] = ((1, 2), (3, 4)),
        points: tuple[Point, Point] = (Point(1), Point(2, 3)),
        rows: list[tuple[float, float]] = [(0.5, 1.5)],
        choices: tuple[int | str, ...] = (1, "a"),
        holes: tuple[int | None, ...] = (1, None),
        days: tuple[date, date] = (date(2026, 1, 2), date(2026, 1, 3)),
        suits: tuple[Suit, ...] = (Suit.HEARTS,),
    ) -> None: ...

    def files(
        documents: tuple[Pdf, ...] = ("a.pdf", "b.pdf"),
        pair: tuple[Pdf, Pdf] | None = None,
        either: list[Pdf] | tuple[Pdf, ...] = ("a.pdf",),
    ) -> None: ...

    def bare(
        fixed: tuple[int, int, int],
        variadic: Annotated[tuple[str, ...], Min(1), Max(3)],
        optional: tuple[bool, bool] | None,
    ) -> None: ...

    return {"swatch": plan_of(Swatch), "route": plan_of(Route),
            "unions": plan_of(unions), "nested": plan_of(nested),
            "files": plan_of(files), "bare": plan_of(bare)}


def test_every_tuple_plan_passes_javascript_validation(node, tmp_path):
    plans = _plans()
    path = tmp_path / "tuple-plans.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["checked"] == len(plans)
    assert result["mounted"] == len(plans)


def _through_the_browser(node, tmp_path, schema):
    # roundtrip-runner.mjs mounts the plan, adds one row to every list that
    # still takes one, types a counter into every text, int and float control
    # and reports form.read(). The result crosses JSON twice, as it does between
    # a real browser and a real server.
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan_of(schema), separators=(",", ":")),
                    encoding="utf-8")

    return node("roundtrip-runner.mjs", str(path))


def test_tuples_round_trip_through_the_browser_into_build(node, tmp_path):
    def form(
        samples: tuple[int, ...],
        rgb: tuple[float, float, float] = (0.0, 0.0, 0.0),
        grid: tuple[tuple[int, int], tuple[int, int]] = ((7, 7), (7, 7)),
        points: tuple[Point, Point] = (Point(0), Point(0)),
    ) -> None: ...

    schema = signature_of(form)
    result = _through_the_browser(node, tmp_path, schema)

    assert result["isReady"] is True
    assert result["hasError"] is False

    read = result["read"]
    assert type(read["samples"]) is list and len(read["samples"]) == 1
    assert len(read["rgb"]) == 3
    assert all(type(value) is int for value in read["rgb"])

    built = schema.build(decode(schema, read))

    assert built["samples"] == tuple(read["samples"])
    assert type(built["samples"]) is tuple
    assert built["rgb"] == tuple(float(value) for value in read["rgb"])
    assert all(type(value) is float for value in built["rgb"])
    assert built["grid"] == tuple(tuple(row) for row in read["grid"])
    assert all(type(row) is tuple for row in built["grid"])
    assert built["points"] == tuple(Point(**point) for point in read["points"])


def test_a_variadic_tuple_of_fixed_tuples_is_built_from_the_transport():
    # The runner cannot fill this one: the row it adds to the outer list holds
    # an empty inner list it then gives a single item. The transport a complete
    # form reads is written here by hand instead.
    schema = _signature(tuple[tuple[int, int], ...])
    transport = json.loads(json.dumps({"value": [[1, 2], [3, 4]]}))

    assert schema.build(decode(schema, transport)) == {
        "value": ((1, 2), (3, 4))}


def test_a_fixed_tuple_takes_no_row_beyond_its_size(node, tmp_path):
    def form(pair: tuple[int, int] = (5, 6)) -> None: ...

    schema = signature_of(form)
    result = _through_the_browser(node, tmp_path, schema)

    # The runner asked for one more row and the list refused it.
    assert len(result["read"]["pair"]) == 2
    assert result["isReady"] is True


def test_a_fixed_tuple_short_of_its_size_is_not_ready(node, tmp_path):
    def form(triple: tuple[int, int, int]) -> None: ...

    schema = signature_of(form)
    result = _through_the_browser(node, tmp_path, schema)

    # No default, so the list starts empty and the runner added a single row.
    assert len(result["read"]["triple"]) == 1
    assert result["isReady"] is False

    with pytest.raises(ValueError, match="expected 3 items, got 1"):
        schema.build(decode(schema, result["read"]))


def test_colliding_tuple_branches_round_trip_wrapped(node, tmp_path):
    def form(
        either: list[int] | tuple[int, ...] = (1, 2),
        as_list: list[int] | tuple[int, ...] = [1, 2],
        tuples: tuple[int, ...] | tuple[str, ...] = ("a",),
        lone: tuple[int, ...] | str = (1,),
    ) -> None: ...

    schema = signature_of(form)
    result = _through_the_browser(node, tmp_path, schema)
    read = result["read"]

    assert result["isReady"] is True
    assert read["either"]["$type"] == "tuple[int, ...]"
    assert read["as_list"]["$type"] == "list[int]"
    assert read["tuples"]["$type"] == "tuple[str, ...]"
    assert type(read["lone"]) is list

    prepared = decode(schema, read)

    # A list and a tuple are told apart by Python itself, so the core consumes
    # that wrapper; two tuples are not, and theirs is kept for build().
    assert prepared["either"] == tuple(read["either"]["$value"])
    assert prepared["as_list"] == read["as_list"]["$value"]
    assert prepared["tuples"] == {"$type": "tuple[str, ...]",
                                  "$value": tuple(read["tuples"]["$value"])}

    built = schema.build(prepared)

    assert type(built["either"]) is tuple and len(built["either"]) == 3
    assert type(built["as_list"]) is list and len(built["as_list"]) == 3
    assert built["tuples"] == tuple(read["tuples"]["$value"])
    assert type(built["tuples"]) is tuple
    assert built["lone"] == tuple(read["lone"])


def test_tuples_of_files_round_trip_through_the_resolver(node, tmp_path):
    def form(
        documents: tuple[Pdf, ...] = ("a.pdf", "b.pdf"),
        pair: tuple[Pdf, Pdf] = ("c.pdf", "d.pdf"),
        either: list[Pdf] | tuple[Pdf, ...] = ("e.pdf",),
        tuples: tuple[Pdf, ...] | tuple[int, ...] = ("f.pdf",),
    ) -> None: ...

    schema = signature_of(form)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan_of(schema)), encoding="utf-8")
    ops = tmp_path / "ops.json"
    ops.write_text("{}", encoding="utf-8")

    # file-star-runner.mjs mounts the plan and reports form.read() untouched, so
    # the default references are what travels.
    read = node("file-star-runner.mjs", str(path), str(ops))["read"]

    assert read["documents"] == ["a.pdf", "b.pdf"]
    assert read["either"] == {"$type": "tuple[str, ...]", "$value": ["e.pdf"]}

    built = schema.build(decode(schema, read, file_resolver=_resolve))

    assert built == {
        "documents": ("/srv/a.pdf", "/srv/b.pdf"),
        "pair": ("/srv/c.pdf", "/srv/d.pdf"),
        "either": ("/srv/e.pdf",),
        "tuples": ("/srv/f.pdf",),
    }


def test_an_immutable_model_round_trips_through_the_browser(node, tmp_path):
    @immutable
    class Mark:
        label: str
        at: tuple[int, int] = (0, 0)

    @immutable
    class Board:
        names: tuple[str, ...]
        size: tuple[float, float] = (1.0, 1.0)
        marks: tuple[Mark, ...] = (Mark(label="start"),)

    schema = struct_of(Board)
    result = _through_the_browser(node, tmp_path, schema)

    assert result["isReady"] is True

    board = schema.build(decode(schema, result["read"]))
    read = result["read"]

    assert type(board) is Board
    assert board.names == tuple(read["names"])
    assert board.size == tuple(float(value) for value in read["size"])
    assert type(board.size) is tuple
    assert len(board.marks) == 2
    assert all(type(mark) is Mark for mark in board.marks)
    assert all(type(mark.at) is tuple for mark in board.marks)
