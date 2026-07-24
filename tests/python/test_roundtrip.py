import json
from dataclasses import dataclass
from typing import Annotated

from pytypehint import Label, Min, signature_of
from pytypehintweb import plan_of


@dataclass
class Address:
    street: Annotated[str, Label("Calle")]
    city: str


def signup(
    name: Annotated[str, Min(1)],
    age: int,
    tags: list[str],
    address: Address,
    nickname: str | None = None,
) -> None:
    """Alta de una cuenta."""


def run(node, tmp_path):
    plan = plan_of(signup)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, separators=(",", ":")), encoding="utf-8")

    return plan, node("roundtrip-runner.mjs", str(path))


def test_the_plan_crosses_json_and_builds_a_ready_form(node, tmp_path):
    plan, result = run(node, tmp_path)

    assert result["name"] == "signup"
    assert result["isReady"] is True
    assert result["hasError"] is False


def test_the_transport_carries_every_field_of_the_plan(node, tmp_path):
    plan, result = run(node, tmp_path)

    assert set(result["read"]) == {f["name"] for f in plan["fields"]}


def test_the_core_builds_the_transport_produced_in_the_browser(node, tmp_path):
    _, result = run(node, tmp_path)
    read = result["read"]

    built = signature_of(signup).build(read)

    assert built["name"] == read["name"]
    assert built["age"] == read["age"]
    assert built["tags"] == read["tags"]
    assert built["address"] == Address(**read["address"])
    assert built["nickname"] is None


def test_the_expanded_plan_carries_every_property_explicitly(node, tmp_path):
    plan, result = run(node, tmp_path)
    name_field = plan["fields"][0]

    # There is one representation now: every known property is present, so the
    # browser never has to reconstruct an absence.
    assert name_field["label"] == "name"
    assert "options" in plan["fields"][1]["node"]
    assert plan["v"] == 1
    assert isinstance(result["read"]["age"], int)


def test_an_untouched_optional_travels_as_null(node, tmp_path):
    _, result = run(node, tmp_path)

    assert result["read"]["nickname"] is None
