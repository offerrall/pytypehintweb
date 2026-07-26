import json
from dataclasses import dataclass
from typing import Annotated

import pytest

from pytypehint import (
    Choices, IsPassword, IsPathFile, Label, Max, Min, Pattern, Placeholder,
    Rows, signature_of, struct_of,
)
from pytypehintweb import WebConfig, decode, plan_of


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


# --- the file node ----------------------------------------------------------

def test_plan_of_emits_a_single_file_node():
    def f(value: Annotated[str, IsPathFile()]) -> None: ...

    assert _node(f) == {
        "kind": "file",
        "options": {
            "extensions": [],
            "invalidMessage": "Not an accepted file type",
            "multiple": False,
            "minFiles": None,
            "maxFiles": None,
            "minMessage": "Add at least {value} files",
            "maxMessage": "Keep at most {value} files",
            "currentLabel": "Current file: {value}",
            "currentRemoveLabel": "Remove current file",
            "currentReplaceLabel": "Replace file",
            "currentRestoreLabel": "Restore current file",
        },
    }


def test_extensions_travel_lowercase_in_declaration_order():
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf", ".docx"))]) -> None: ...

    assert _node(f)["options"]["extensions"] == [".pdf", ".docx"]


def test_the_invalid_message_comes_from_the_web_config():
    def f(value: Annotated[str, IsPathFile()]) -> None: ...

    config = WebConfig(file_invalid_message="Wrong kind of file")
    node = plan_of(f, config=config)["fields"][0]["node"]

    assert node["options"]["invalidMessage"] == "Wrong kind of file"


# --- deferred combinations --------------------------------------------------

# The core allows each of these atoms beside IsPathFile; the adapter defers the
# combination until a real case asks for it, the same way it defers Float.slider.
@pytest.mark.parametrize("atom, name", [
    (Min(1), "min"),
    (Max(5), "max"),
    (Pattern(r"[a-z]+"), "pattern"),
    (Choices(values=("report.pdf",)), "choices"),
    (IsPassword(), "is_password"),
    (Rows(3), "rows"),
    (Placeholder("Pick a file"), "placeholder"),
])
def test_ispathfile_with_another_str_atom_is_deferred(atom, name):
    def f(value: Annotated[str, IsPathFile(), atom]) -> None: ...

    with pytest.raises(TypeError,
                       match=f"Str.{name} with IsPathFile is not supported yet"):
        plan_of(f)


def test_ispathfile_composes_with_field_label_and_description():
    # Label and Description are the field's, not the Str's, so they are not among
    # the deferred atoms: a labelled file field is fine.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",)), Label("Resume")]) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["label"] == "Resume"
    assert field["node"]["kind"] == "file"


# --- a file carries no default ----------------------------------------------

def test_a_file_field_with_a_default_is_rejected_at_compile():
    # The reference is minted locally from the user's choice, so a pre-set one is
    # meaningless: plan_of rejects a default on a file field while compiling.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",)),
                           Label("Doc")] = "existing-doc.pdf") -> None: ...

    with pytest.raises(TypeError, match="a file field cannot carry a default"):
        plan_of(f)


def test_an_optional_file_with_a_none_default_is_rejected():
    # Even the None a switched-off optional would use is refused: the off state of
    # an optional file is expressed by its toggle, never by a default.
    def f(value: Annotated[str, IsPathFile(), Label("Doc")] | None = None) -> None: ...

    with pytest.raises(TypeError, match="a file field cannot carry a default"):
        plan_of(f)


def test_a_file_nested_in_a_list_default_is_rejected():
    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           Label("Docs")] = ["x.pdf"]) -> None: ...

    with pytest.raises(TypeError, match="a file field cannot carry a default"):
        plan_of(f)


def test_a_list_of_files_with_any_default_is_rejected():
    # list[File] is a file field now (a multiple one), so it carries no default —
    # not even an empty list.
    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           Label("Docs")] = []) -> None: ...

    with pytest.raises(TypeError, match="a file field cannot carry a default"):
        plan_of(f)


def test_an_optional_file_without_a_default_is_fine():
    def f(value: Annotated[str, IsPathFile(), Label("Optional file")] | None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["hasDefault"] is False
    assert field["node"]["kind"] == "file"


# --- transport: a file is a str on the wire ---------------------------------

def test_a_generated_reference_round_trips_through_decode_and_build():
    # The widget mints a reference shaped like <name>-<uuid>.<ext>; on the wire it
    # is a plain string, so decode passes it through untouched and build accepts
    # it.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    reference = "informe-anual-550e8400-e29b-41d4-a716-446655440000.pdf"

    prepared = decode(schema, {"value": reference})
    assert prepared == {"value": reference}

    built = schema.build(prepared)
    assert built == {"value": reference}


def test_build_still_filters_the_reference_by_extension():
    # The extension is a filter for honest mistakes, applied by the core on the
    # way in exactly as the widget mints it. It never checks the bytes exist.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)

    with pytest.raises(Exception):
        schema.build(decode(schema, {"value": "note.txt"}))


# --- unions -----------------------------------------------------------------

def test_str_and_file_share_the_option_id_str_and_the_core_rejects_the_union():
    # A file is a Str, so option_id() is "str" for both branches. str | file is
    # two branches with the same option id: the core rejects it while compiling
    # the field (duplicate option types), before plan_of ever runs.
    def f(value: str | Annotated[str, IsPathFile()]) -> None: ...

    with pytest.raises(ValueError, match="duplicate option types"):
        signature_of(f)


def test_a_file_in_a_sane_union_compiles_with_the_str_branch_id():
    # file | int: distinct transports (string vs number) and distinct option ids
    # ("str" vs "int"), so the union is sound.
    def f(value: Annotated[str, IsPathFile()] | int) -> None: ...

    node = _node(f)

    assert node["kind"] == "choice"
    assert {b["value"]: b["node"]["kind"] for b in node["branches"]} == {
        "str": "file", "int": "int"}
    assert {b["value"]: b["mode"] for b in node["branches"]} == {
        "str": "plain", "int": "plain"}


def test_a_file_collides_with_a_date_on_transport_and_travels_wrapped():
    from datetime import date

    def f(value: Annotated[str, IsPathFile()] | date) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"str": "wrapped", "date": "wrapped"}


# --- multi-file: list[File] is one multiple file node -----------------------

def test_a_list_of_files_is_one_multiple_file_node():
    def f(value: Annotated[list[Annotated[str, IsPathFile(extensions=(".pdf",))]],
                           Min(1), Max(3), Label("Attachments")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "file"
    assert node["options"]["multiple"] is True
    assert node["options"]["extensions"] == [".pdf"]
    assert node["options"]["minFiles"] == 1
    assert node["options"]["maxFiles"] == 3


def test_a_list_of_files_without_bounds_has_null_file_counts():
    def f(value: Annotated[list[Annotated[str, IsPathFile()]], Label("Docs")]) -> None: ...

    options = _node(f)["options"]

    assert options["multiple"] is True
    assert options["minFiles"] is None
    assert options["maxFiles"] is None


def test_a_file_inside_a_list_union_is_not_supported():
    def f(value: Annotated[list[Annotated[str, IsPathFile()] | None],
                           Label("Docs")]) -> None: ...

    with pytest.raises(TypeError, match="not supported yet"):
        plan_of(f)


def test_a_nested_list_of_files_is_not_supported():
    def f(value: Annotated[list[list[Annotated[str, IsPathFile()]]],
                           Label("Docs")]) -> None: ...

    with pytest.raises(TypeError, match="not supported yet"):
        plan_of(f)


def test_a_list_of_references_round_trips_through_build():
    def f(value: Annotated[list[Annotated[str, IsPathFile(extensions=(".pdf",))]],
                           Label("Docs")]) -> None: ...

    schema = signature_of(f)
    references = ["550e8400-e29b-41d4-a716-446655440000.pdf",
                  "550e8400-e29b-41d4-a716-446655440001.pdf"]

    prepared = decode(schema, {"value": references})
    assert prepared == {"value": references}
    assert schema.build(prepared) == {"value": references}


# --- the star round trip: a struct through a create/edit form ----------------

@dataclass
class User:
    name: Annotated[str, Label("Name")]
    avatar: Annotated[str, IsPathFile(extensions=(".jpg",)), Label("Avatar")]


@dataclass
class Gallery:
    photos: Annotated[list[Annotated[str, IsPathFile(extensions=(".jpg",))]],
                      Label("Photos")]


def _file_star(node, tmp_path, obj, ops):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan_of(obj), separators=(",", ":")),
                         encoding="utf-8")

    ops_path = tmp_path / "ops.json"
    ops_path.write_text(json.dumps(ops), encoding="utf-8")

    return node("file-star-runner.mjs", str(plan_path), str(ops_path))["read"]


def test_editing_without_touching_the_file_returns_it_byte_identical(node, tmp_path):
    # The guarantee: a struct with an internal path goes to the form and back
    # complete without moving bytes. The record is set on the widgets, only the
    # name is edited, and build() returns the User with the avatar untouched.
    read = _file_star(node, tmp_path, User,
                      {"set": {"name": "Ada Lovelace", "avatar": "avatars/ada.jpg"}})

    assert read == {"name": "Ada Lovelace", "avatar": "avatars/ada.jpg"}

    schema = struct_of(User)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built == User("Ada Lovelace", "avatars/ada.jpg")
    assert built.avatar == "avatars/ada.jpg"                 # byte-identical


def test_replacing_the_file_transports_a_fresh_generated_reference(node, tmp_path):
    read = _file_star(node, tmp_path, User, {
        "set": {"name": "Ada", "avatar": "avatars/ada.jpg"},
        "choose": {"avatar": ["new-photo.jpg"]},
    })

    assert read["name"] == "Ada"
    assert read["avatar"] != "avatars/ada.jpg"               # a new local choice
    assert read["avatar"].endswith(".jpg")

    schema = struct_of(User)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built.avatar == read["avatar"]


def test_the_chosen_file_name_leads_the_reference_across_the_wire(node, tmp_path):
    # The name the widget slugs is part of the reference, so it has to survive the
    # crossing intact: JSON, decode() and build() all treat it as plain text.
    read = _file_star(node, tmp_path, User,
                      {"choose": {"avatar": ["Informe Añual.jpg"]}})

    assert read["avatar"].startswith("informe-anual-")
    assert read["avatar"].endswith(".jpg")

    schema = struct_of(User)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built.avatar == read["avatar"]


def test_a_multi_file_struct_carries_distinct_references(node, tmp_path):
    read = _file_star(node, tmp_path, Gallery,
                      {"choose": {"photos": ["a.jpg", "b.jpg", "c.jpg"]}})

    assert len(read["photos"]) == 3
    assert len(set(read["photos"])) == 3                     # distinct references
    assert all(ref.endswith(".jpg") for ref in read["photos"])

    schema = struct_of(Gallery)
    built = schema.build(decode(schema, json.loads(json.dumps(read))))

    assert built.photos == read["photos"]
