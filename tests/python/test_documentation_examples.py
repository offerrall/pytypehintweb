import json
import re
from pathlib import Path
from typing import Annotated

from pytypehint import Label, Min, signature_of
from pytypehintweb import plan_of

ROOT = Path(__file__).resolve().parents[2]

FENCE = re.compile(r"```(\w+)\n(.*?)```", re.DOTALL)


def blocks(path: Path, language: str) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    return [body for fence, body in FENCE.findall(text) if fence == language]


def test_the_readme_quick_start_plan_matches_plan_of():
    def create_user(
        username: Annotated[str, Min(3), Label("Username")],
        age: Annotated[int, Min(0), Label("Age")],
    ) -> None:
        pass

    documented = json.loads(blocks(Path("README.md"), "json")[0])

    assert documented == plan_of(create_user)


def test_the_getting_started_plan_matches_plan_of():
    def create_user(
        username: Annotated[str, Min(3), Label("Username")],
        age: Annotated[int, Min(0), Label("Age")],
    ) -> None:
        """Create a user account."""

    documented = json.loads(blocks(Path("docs/getting-started.md"), "json")[0])

    assert documented == plan_of(create_user)
    assert documented["description"] == "Create a user account."


def test_the_getting_started_build_example_returns_the_documented_value():
    def create_user(
        username: Annotated[str, Min(3), Label("Username")],
        age: Annotated[int, Min(0), Label("Age")],
    ) -> None:
        """Create a user account."""

    schema = signature_of(create_user)

    assert schema.build({"username": "ada", "age": 36}) == {
        "username": "ada",
        "age": 36,
    }


def test_every_documented_json_block_parses():
    invalid = []

    for name in ["README.md", "docs/plan.md", "docs/getting-started.md",
                 "docs/python.md", "docs/javascript.md"]:
        for index, body in enumerate(blocks(Path(name), "json")):
            try:
                json.loads(body)
            except ValueError as error:
                invalid.append(f"{name} block {index}: {error}")

    assert invalid == []


def test_the_documented_web_config_matches_the_dataclass():
    from dataclasses import fields as dataclass_fields

    from pytypehintweb import WebConfig

    source = next(body for body in blocks(Path("docs/python.md"), "python")
                  if "class WebConfig" in body)

    documented = dict(re.findall(r"^    (\w+): str = (\".*\")$", source,
                                 re.MULTILINE))
    actual = {f.name: json.dumps(f.default)
              for f in dataclass_fields(WebConfig)}

    assert documented == actual
