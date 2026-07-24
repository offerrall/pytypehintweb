import json
from typing import Annotated

from pytypehint import Label, signature_of
from pytypehintweb import plan_of


def test_plan_of_emits_a_bool_node():
    def f(agree: bool) -> None: ...

    node = plan_of(f)["fields"][0]["node"]

    assert node == {"kind": "bool", "options": {}}


def test_a_bool_default_is_certified_and_travels():
    def f(agree: bool = True) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] is True
    assert field["optional"] is False


def test_a_false_default_travels_as_false():
    def f(agree: bool = False) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] is False


def test_bool_or_none_is_optional():
    def f(agree: bool | None = None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["node"]["kind"] == "bool"


def test_list_of_bool():
    def f(flags: list[bool]) -> None: ...

    node = plan_of(f)["fields"][0]["node"]

    assert node["kind"] == "list"
    assert node["item"] == {"kind": "bool", "options": {}}


def test_bool_in_a_union_participates_as_a_plain_branch():
    def f(x: str | bool) -> None: ...

    node = plan_of(f)["fields"][0]["node"]

    assert node["kind"] == "choice"
    modes = {b["value"]: b["mode"] for b in node["branches"]}
    assert modes["bool"] == "plain"


def test_schema_build_accepts_a_bool():
    def f(agree: bool) -> None: ...

    schema = signature_of(f)

    assert schema.build({"agree": True}) == {"agree": True}
    assert schema.build({"agree": False}) == {"agree": False}


def test_the_full_round_trip_with_bool(node, tmp_path):
    def f(
        agree: Annotated[bool, Label("Agree")],
        subscribed: Annotated[bool, Label("Subscribed")] = True,
    ) -> None:
        """Bool round trip."""

    plan = plan_of(f)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    result = node("roundtrip-runner.mjs", str(path))

    assert result["isReady"] is True
    assert result["hasError"] is False
    # roundtrip-runner checks every checkbox, so both booleans read True.
    assert result["read"] == {"agree": True, "subscribed": True}

    built = signature_of(f).build(result["read"])
    assert built == {"agree": True, "subscribed": True}
