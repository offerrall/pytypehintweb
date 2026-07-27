import json
from dataclasses import dataclass
from typing import Annotated

import pytest

from pytypehint import (
    Choices, IsPassword, IsPathFile, Label, Max, Min, Pattern, Placeholder,
    Rows, signature_of, struct_of,
)
from pytypehintweb import WebConfig, decode, plan_of
from pytypehintweb import plan as plan_module


def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


def _stored(tmp_path, name, data=b"bytes"):
    """A real file on disk, returned as the `str` path the core wants.

    `IsPathFile` certifies the file itself now — extension, existence, regular
    file and size — so any value that reaches a `Choices` list, a default or
    `build()` has to point at something real. Tests that only inspect the plan
    never need one: a plan is compiled from the shape, not from a value.
    """
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    return str(path)


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
            "minSize": None,
            "maxSize": None,
            "minMessage": "Add at least {value} files",
            "maxMessage": "Keep at most {value} files",
            "minSizeMessage": "File is too small; minimum {value}",
            "maxSizeMessage": "File is too large; maximum {value}",
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
# The atoms are built lazily because one of them carries a value: a Choices over a
# file has to name a file that exists, so it needs tmp_path.
@pytest.mark.parametrize("name, make_atom", [
    ("min", lambda tmp_path: Min(1)),
    ("max", lambda tmp_path: Max(5)),
    ("pattern", lambda tmp_path: Pattern(r"[a-z]+")),
    ("choices",
     lambda tmp_path: Choices(values=(_stored(tmp_path, "report.pdf"),))),
    ("is_password", lambda tmp_path: IsPassword()),
    ("rows", lambda tmp_path: Rows(3)),
    ("placeholder", lambda tmp_path: Placeholder("Pick a file")),
])
def test_ispathfile_with_another_str_atom_is_deferred(name, make_atom, tmp_path):
    atom = make_atom(tmp_path)

    def f(value: Annotated[str, IsPathFile(), atom]) -> None: ...

    with pytest.raises(TypeError,
                       match=f"Str.{name} with IsPathFile is not supported yet"):
        plan_of(f)


def test_a_plain_ispathfile_carries_no_size_bounds():
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    node = _node(f)

    assert node["kind"] == "file"
    assert node["options"]["minSize"] is None
    assert node["options"]["maxSize"] is None


# --- byte-size bounds -------------------------------------------------------

# A restriction the browser cannot weigh must not stop the type from being
# representable. The bounds travel on the node so a local File can be refused
# before it is uploaded; a reference carries no bytes, so only the core's
# verdict on the real file is final.

@pytest.mark.parametrize("mark, expected", [
    (IsPathFile(min_size=1), (1, None)),
    (IsPathFile(max_size=1024), (None, 1024)),
    (IsPathFile(min_size=1, max_size=1_000_000), (1, 1_000_000)),
    (IsPathFile(min_size=0), (0, None)),
    (IsPathFile(min_size=512, max_size=512), (512, 512)),
])
def test_byte_size_bounds_travel_on_the_file_node(mark, expected):
    def f(value: Annotated[str, mark]) -> None: ...

    options = _node(f)["options"]

    assert (options["minSize"], options["maxSize"]) == expected


def test_the_size_messages_come_from_the_web_config():
    def f(value: Annotated[str, IsPathFile(min_size=1, max_size=2)]) -> None: ...

    config = WebConfig(file_min_size_message="Under {value}",
                       file_max_size_message="Over {value}")
    options = plan_of(f, config=config)["fields"][0]["node"]["options"]

    assert options["minSizeMessage"] == "Under {value}"
    assert options["maxSizeMessage"] == "Over {value}"


def test_a_size_bound_beyond_the_safe_integer_range_is_refused():
    # The plan is JSON read by JavaScript. The core has no reason to care, so
    # this is the one thing left to check here.
    def f(value: Annotated[str, IsPathFile(max_size=2 ** 60)]) -> None: ...

    with pytest.raises(TypeError, match="IsPathFile.max_size"):
        plan_of(f)


def test_the_bounds_survive_json():
    def f(value: Annotated[str, IsPathFile(min_size=1, max_size=1024)]) -> None: ...

    options = json.loads(json.dumps(_node(f)))["options"]

    assert options["minSize"] == 1
    assert options["maxSize"] == 1024


def _file_options(plan):
    """Every file node in a plan, however deep, in document order."""
    found = []

    def walk(value):
        if type(value) is dict:
            if value.get("kind") == "file":
                found.append(value["options"])

            for item in value.values():
                walk(item)
        elif type(value) is list:
            for item in value:
                walk(item)

    walk(plan)

    return found


_BOUNDED = Annotated[str, IsPathFile(extensions=(".pdf",),
                                     min_size=10, max_size=2048)]


@dataclass
class _Report:
    document: _BOUNDED
    title: str = "x"


@pytest.mark.parametrize("name, annotation, nodes", [
    ("File", _BOUNDED, 1),
    ("File | None", _BOUNDED | None, 1),
    ("list[File]", list[_BOUNDED], 1),
    ("list[File | None]", list[_BOUNDED | None], 1),
    ("list[File | int]", list[_BOUNDED | int], 1),
    ("list[list[File]]", list[list[_BOUNDED]], 1),
    ("dataclass with File", _Report, 1),
    ("list[dataclass with File]", list[_Report], 1),
])
def test_the_bounds_reach_every_file_node_however_composed(
        name, annotation, nodes):
    # The bounds belong to the file node, so they arrive wherever a file node
    # arrives. Nothing in the adapter says "top level only".
    def f(value: annotation) -> None: ...

    found = _file_options(plan_of(f))

    assert len(found) == nodes, name
    assert all(o["minSize"] == 10 for o in found), name
    assert all(o["maxSize"] == 2048 for o in found), name


def test_ispathfile_composes_with_field_label_and_description():
    # Label and Description are the field's, not the Str's, so they are not among
    # the deferred atoms: a labelled file field is fine.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",)), Label("Resume")]) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["label"] == "Resume"
    assert field["node"]["kind"] == "file"


# --- a file default is an existing reference --------------------------------
#
# It means exactly what FileWidget.setValue() means: a reference the host
# declares, shown as the current file and transported back untouched. It carries
# no bytes and starts no upload.
#
# Every default here points at a real file, and not for the adapter's sake: the
# core certifies a `IsPathFile` value while compiling the schema, so a default
# that does not exist never reaches plan_of() at all. That is the seam described
# in test_a_reference_the_core_cannot_certify_never_reaches_the_plan.

def test_a_file_field_carries_its_default_reference_into_the_plan(tmp_path):
    existing = _stored(tmp_path, "existing-doc.pdf")

    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",)),
                           Label("Doc")] = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == existing
    assert isinstance(field["default"], str)
    assert field["node"]["kind"] == "file"


def test_an_optional_file_accepts_a_none_default():
    # The off state of an optional file is the toggle; `None` is how the plan
    # spells it, exactly as for every other optional scalar.
    def f(value: Annotated[str, IsPathFile(), Label("Doc")] | None = None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["hasDefault"] is True
    assert field["default"] is None
    assert field["enabled"] is False


def test_an_optional_file_accepts_a_reference_default(tmp_path):
    existing = _stored(tmp_path, "kept.pdf")

    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",)),
                           Label("Doc")] | None = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["default"] == existing
    assert field["enabled"] is True


def test_a_list_of_files_carries_a_list_of_references(tmp_path):
    existing = [_stored(tmp_path, "one.pdf"), _stored(tmp_path, "two.pdf")]

    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           Label("Docs")] = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["node"]["options"]["multiple"] is True
    assert field["default"] == existing              # order preserved
    assert all(isinstance(item, str) for item in field["default"])


def test_a_list_of_files_accepts_an_empty_default():
    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           Label("Docs")] = []) -> None: ...

    assert plan_of(f)["fields"][0]["default"] == []


def test_a_file_default_survives_json_as_plain_text(tmp_path):
    existing = _stored(tmp_path, "report.pdf")

    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))] = existing,
          docs: Annotated[list[Annotated[str, IsPathFile()]],
                          Label("Docs")] = []) -> None: ...

    plan = plan_of(f)
    restored = json.loads(json.dumps(plan))

    assert restored == plan
    assert isinstance(restored["fields"][0]["default"], str)
    assert "Path(" not in json.dumps(plan)


def test_a_reference_the_core_cannot_certify_never_reaches_the_plan():
    # The architectural seam, stated as a test. A Python default is certified by
    # `IsPathFile` while the schema compiles, so plan_of() only ever sees one the
    # core already accepted. A host whose references are not local paths — an
    # object-store key, say — cannot smuggle one in through a schema default; it
    # sets it on the widget with setValue() after mounting, and resolves it on
    # the way back with decode(file_resolver=...).
    with pytest.raises(Exception, match="file does not exist"):
        def f(value: Annotated[str, IsPathFile()] = "bucket/key.pdf") -> None: ...

        plan_of(f)


def test_a_file_default_inside_a_dataclass_reaches_the_nested_node(tmp_path):
    # A nested default follows the same walk as any other initial value: the
    # object travels whole and the file inside it is not dropped on the way.
    avatar = _stored(tmp_path, "ada.jpg")

    @dataclass
    class Profile:
        name: Annotated[str, Label("Name")]
        avatar: Annotated[str, IsPathFile(extensions=(".jpg",)), Label("Avatar")]

    def f(profile: Profile = Profile("Ada", avatar)) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == {"name": "Ada", "avatar": avatar}
    assert field["node"]["kind"] == "object"


def test_a_list_of_files_inside_a_dataclass_keeps_its_references(tmp_path):
    photos = [_stored(tmp_path, "a.jpg"), _stored(tmp_path, "b.jpg")]

    @dataclass
    class Album:
        photos: Annotated[list[Annotated[str, IsPathFile(extensions=(".jpg",))]],
                          Label("Photos")]

    def f(album: Album = Album(photos)) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == {"photos": photos}


# The core is the source of truth for a schema default, and it certifies before
# plan_of() ever runs. These pin each refusal to the core, at its own message, so
# a regression that moved one of them into the adapter would be visible.

def test_the_core_refuses_a_default_that_names_no_file(tmp_path):
    def f(value: Annotated[str, IsPathFile()] = "no-such-file.pdf") -> None: ...

    with pytest.raises(Exception, match="file does not exist"):
        plan_of(f)


def test_the_core_refuses_a_default_that_is_a_directory(tmp_path):
    directory = tmp_path / "folder"
    directory.mkdir()

    def f(value: Annotated[str, IsPathFile()] = str(directory)) -> None: ...

    with pytest.raises(Exception, match="not a file"):
        plan_of(f)


def test_the_core_refuses_a_default_with_the_wrong_extension(tmp_path):
    wrong_kind = _stored(tmp_path, "note.txt")

    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]
          = wrong_kind) -> None: ...

    with pytest.raises(Exception, match="not an accepted file type"):
        plan_of(f)


def test_the_core_refuses_a_default_that_is_not_a_string(tmp_path):
    def f(value: Annotated[str, IsPathFile()] = 7) -> None: ...

    with pytest.raises(Exception, match="expected str"):
        plan_of(f)


def test_the_core_refuses_a_list_default_holding_one_missing_file(tmp_path):
    present = _stored(tmp_path, "present.pdf")

    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           Label("Docs")] = [present, "gone.pdf"]) -> None: ...

    with pytest.raises(Exception, match=r"\[1\]: file does not exist"):
        plan_of(f)


@pytest.mark.parametrize("name, mark, size, message", [
    ("min_size", IsPathFile(min_size=100), 1, "file too small"),
    ("max_size", IsPathFile(max_size=100), 5000, "file too large"),
])
def test_the_core_checks_byte_sizes_on_a_default(
        tmp_path, name, mark, size, message):
    # A default is a real file the core weighs before the plan exists, so a
    # form is never rendered around a value that already breaks its own bound.
    too_wrong = _stored(tmp_path, f"{name}.pdf", b"x" * size)

    def f(value: Annotated[str, mark] = too_wrong) -> None: ...

    with pytest.raises(Exception, match=message):
        plan_of(f)


@pytest.mark.parametrize("name, size", [
    ("exactly the minimum", 100),
    ("exactly the maximum", 1000),
    ("between the two", 500),
])
def test_a_default_inside_the_bounds_reaches_the_plan(tmp_path, name, size):
    right_size = _stored(tmp_path, f"{size}.pdf", b"x" * size)

    def f(value: Annotated[str, IsPathFile(min_size=100, max_size=1000)]
          = right_size) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == right_size
    assert field["node"]["options"]["minSize"] == 100
    assert field["node"]["options"]["maxSize"] == 1000


@pytest.mark.parametrize("name, bounds", [
    ("below the minimum", (Min(2), [1])),
    ("above the maximum", (Max(1), [2])),
])
def test_the_core_checks_list_bounds_on_a_file_default(tmp_path, name, bounds):
    mark, counts = bounds
    files = [_stored(tmp_path, f"{name[:5]}-{i}.pdf") for i in range(counts[0])]

    def f(value: Annotated[list[Annotated[str, IsPathFile()]],
                           mark, Label("Docs")] = files) -> None: ...

    with pytest.raises(Exception, match="too few items|too many items"):
        plan_of(f)


def test_an_optional_file_without_a_default_is_fine():
    def f(value: Annotated[str, IsPathFile(), Label("Optional file")] | None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["hasDefault"] is False
    assert field["node"]["kind"] == "file"


# --- transport: a file is a str on the wire ---------------------------------

def test_a_generated_reference_travels_untouched_through_decode():
    # The widget mints a reference shaped like <name>-<uuid>.<ext>; on the wire it
    # is a plain string. decode prepares, it does not validate, so with no
    # resolver the reference reaches the core exactly as it was typed into JSON.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    reference = "informe-anual-550e8400-e29b-41d4-a716-446655440000.pdf"

    assert decode(schema, {"value": reference}) == {"value": reference}


def test_the_host_resolver_is_what_makes_a_reference_buildable(tmp_path):
    # pytypehint 0.0.7 certifies the file itself — existence, regular file, size —
    # so a reference only becomes buildable once the host maps it to wherever it
    # actually stored the bytes. That mapping is decode()'s file_resolver, and it
    # receives the reference byte-identical.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    reference = "informe-anual-550e8400-e29b-41d4-a716-446655440000.pdf"
    stored = _stored(tmp_path, "informe-anual.pdf")

    seen = []

    def resolve(value):
        seen.append(value)
        return stored

    prepared = decode(schema, {"value": reference}, file_resolver=resolve)

    assert seen == [reference]
    assert schema.build(prepared) == {"value": stored}


def test_build_rejects_a_reference_whose_bytes_were_never_stored():
    # The counterpart: an unresolved reference is refused rather than accepted as
    # a promise. A host that mints references and never uploads now finds out at
    # build() instead of shipping a string that points at nothing.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)

    with pytest.raises(Exception, match="file does not exist"):
        schema.build(decode(schema, {"value": "never-uploaded-1234.pdf"}))


def test_build_still_filters_the_reference_by_extension(tmp_path):
    # The extension is a filter for honest mistakes, applied by the core on the
    # way in exactly as the widget mints it. The file is real, so the refusal is
    # demonstrably about the extension and not about the bytes being missing.
    def f(value: Annotated[str, IsPathFile(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    wrong_kind = _stored(tmp_path, "note.txt")

    with pytest.raises(Exception, match="not an accepted file type"):
        schema.build(decode(schema, {"value": wrong_kind}))


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


# --- a file composes like any other node ------------------------------------
#
# There is no rule about files in lists. A file node is representable, so a list
# of them, a list of optionals holding one, a list of choices with one branch,
# a nested list and a list of structs are all just the recursion doing its job.
# The only special case is the *shortcut*: a bare list[File] becomes one
# `multiple` file node instead of a list of single-file widgets.

@dataclass
class Attachment:
    title: Annotated[str, Label("Title")]
    document: Annotated[str, IsPathFile(), Label("Doc")]


def test_a_list_of_optional_files_is_a_list_of_optional_nodes():
    def f(value: Annotated[list[Annotated[str, IsPathFile()] | None],
                           Label("Docs")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "optional"
    assert node["item"]["node"]["kind"] == "file"


def test_a_list_of_file_or_int_is_a_list_of_choices():
    def f(value: Annotated[list[Annotated[str, IsPathFile()] | int],
                           Label("Docs")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "choice"
    assert {b["value"]: b["node"]["kind"] for b in node["item"]["branches"]} == {
        "str": "file", "int": "int"}


def test_a_nested_list_of_files_nests_the_nodes():
    # The inner list is itself a bare list[File], so the shortcut applies there
    # and the outer list holds one multiple file node per row. The structure is
    # not flattened: the outer list is still a list.
    def f(value: Annotated[list[list[Annotated[str, IsPathFile()]]],
                           Label("Docs")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "file"
    assert node["item"]["options"]["multiple"] is True


def test_a_list_of_structs_holding_a_file_is_a_list_of_objects():
    def f(value: Annotated[list[Attachment], Label("Docs")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "object"
    assert [(f_["name"], f_["node"]["kind"]) for f_ in node["item"]["fields"]] == [
        ("title", "str"), ("document", "file")]


def test_a_file_two_levels_below_a_list_still_compiles():
    # Nothing counts depth: a struct inside a list holding a list of files.
    @dataclass
    class Bundle:
        docs: Annotated[list[Annotated[str, IsPathFile()]], Label("Docs")]

    def f(value: Annotated[list[Bundle], Label("Bundles")]) -> None: ...

    node = _node(f)

    assert node["item"]["fields"][0]["node"]["options"]["multiple"] is True


def test_no_rule_rejects_a_shape_merely_for_holding_a_file():
    # The regression guard for the block this replaced. Each of these used to
    # raise "a file inside a list is only supported as a plain list[File]".
    @dataclass
    class Holder:
        doc: Annotated[str, IsPathFile(), Label("Doc")]

    def optional_items(v: Annotated[list[Annotated[str, IsPathFile()] | None],
                                    Label("V")]) -> None: ...
    def union_items(v: Annotated[list[Annotated[str, IsPathFile()] | int],
                                 Label("V")]) -> None: ...
    def nested(v: Annotated[list[list[Annotated[str, IsPathFile()]]],
                            Label("V")]) -> None: ...
    def structs(v: Annotated[list[Holder], Label("V")]) -> None: ...

    for fn in (optional_items, union_items, nested, structs):
        assert plan_of(fn)["fields"][0]["node"]["kind"] == "list"

    assert not hasattr(plan_module, "_contains_file"), (
        "the blanket 'does this contain a file' predicate is gone; a shape is "
        "representable when each of its nodes is, not when it avoids files")


def test_the_supported_file_compositions_all_compile():
    # Every shape the documentation claims, as a test rather than a sentence.
    @dataclass
    class Profile:
        avatar: Annotated[str, IsPathFile(), Label("Avatar")]

    @dataclass
    class Album:
        photos: Annotated[list[Annotated[str, IsPathFile()]], Label("Photos")]

    def one(value: Annotated[str, IsPathFile(), Label("V")]) -> None: ...
    def optional(value: Annotated[str, IsPathFile(), Label("V")] | None) -> None: ...
    def many(value: Annotated[list[Annotated[str, IsPathFile()]],
                              Label("V")]) -> None: ...
    def in_struct(value: Profile) -> None: ...
    def many_in_struct(value: Album) -> None: ...
    def in_union(value: Annotated[str, IsPathFile()] | int) -> None: ...
    def list_optional(value: Annotated[list[Annotated[str, IsPathFile()] | None],
                                       Label("V")]) -> None: ...
    def list_union(value: Annotated[list[Annotated[str, IsPathFile()] | int],
                                    Label("V")]) -> None: ...
    def list_list(value: Annotated[list[list[Annotated[str, IsPathFile()]]],
                                   Label("V")]) -> None: ...
    def list_struct(value: Annotated[list[Attachment], Label("V")]) -> None: ...

    kinds = {}

    for name, fn in [("file", one), ("optional", optional), ("list", many),
                     ("struct", in_struct), ("struct-list", many_in_struct),
                     ("union", in_union), ("list-optional", list_optional),
                     ("list-union", list_union), ("list-list", list_list),
                     ("list-struct", list_struct)]:
        kinds[name] = plan_of(fn)["fields"][0]["node"]["kind"]

    assert kinds == {
        "file": "file", "optional": "file", "list": "file",
        "struct": "object", "struct-list": "object", "union": "choice",
        "list-optional": "list", "list-union": "list", "list-list": "list",
        "list-struct": "list",
    }


# --- decode reaches a file at any depth -------------------------------------
#
# decode() walks the core's shapes, not the plan, so it never needed a rule about
# files in lists either. These pin the walk: one call per reference, in order,
# nothing else touched.

def _recording_resolver():
    seen = []

    def resolve(reference):
        seen.append(reference)
        return f"/resolved/{reference}"

    return seen, resolve


def test_decode_resolves_a_file_inside_a_list_of_optionals(tmp_path):
    a = _stored(tmp_path, "a.pdf")

    def f(value: Annotated[list[Annotated[str, IsPathFile()] | None],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": [a, None]}, file_resolver=resolve)

    assert seen == [a]                       # None never reaches the resolver
    assert out == {"value": [f"/resolved/{a}", None]}


def test_decode_resolves_only_the_file_branch_of_a_mixed_list(tmp_path):
    a = _stored(tmp_path, "a.pdf")

    def f(value: Annotated[list[Annotated[str, IsPathFile()] | int],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": [a, 7]}, file_resolver=resolve)

    assert seen == [a]
    assert out == {"value": [f"/resolved/{a}", 7]}


def test_decode_resolves_every_file_of_a_nested_list_in_order(tmp_path):
    a, b = _stored(tmp_path, "a.pdf"), _stored(tmp_path, "b.pdf")

    def f(value: Annotated[list[list[Annotated[str, IsPathFile()]]],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": [[a], [b, a]]}, file_resolver=resolve)

    assert seen == [a, b, a]                 # once per reference, in order
    assert out == {"value": [[f"/resolved/{a}"],
                             [f"/resolved/{b}", f"/resolved/{a}"]]}


def test_a_list_of_structs_with_a_file_round_trips_through_build(tmp_path):
    # The whole way round for the shape that used to be refused: plan, transport,
    # decode with a resolver, and the core building the real objects.
    a, b = _stored(tmp_path, "a.pdf"), _stored(tmp_path, "b.pdf")

    def f(items: Annotated[list[Attachment], Label("Items")]) -> None: ...

    schema = signature_of(f)
    body = {"items": [{"title": "one", "document": a},
                      {"title": "two", "document": b}]}

    # build() certifies the resolved path, so the host has to answer with a real
    # one — the same _Storage stand-in the star round trip uses.
    storage = _Storage(tmp_path)
    built = schema.build(decode(schema, json.loads(json.dumps(body)),
                                file_resolver=storage.resolve))

    assert storage.seen == [a, b]
    assert [row.title for row in built["items"]] == ["one", "two"]
    assert [row.document for row in built["items"]] == [
        storage.path_of(a), storage.path_of(b)]


def test_a_deep_default_survives_json_and_carries_no_path_objects(tmp_path):
    a, b = _stored(tmp_path, "a.pdf"), _stored(tmp_path, "b.pdf")

    def f(
        holes: Annotated[list[Annotated[str, IsPathFile()] | None],
                         Label("H")] = [a, None],
        mixed: Annotated[list[Annotated[str, IsPathFile()] | int],
                         Label("M")] = [a, 7],
        nested: Annotated[list[list[Annotated[str, IsPathFile()]]],
                          Label("N")] = [[a], [b]],
        rows: Annotated[list[Attachment], Label("R")] = [Attachment("t", a)],
    ) -> None: ...

    plan = plan_of(f)
    text = json.dumps(plan)

    assert json.loads(text) == plan
    assert "Path(" not in text
    assert "WindowsPath" not in text and "PosixPath" not in text

    defaults = {field["name"]: field["default"] for field in plan["fields"]}

    assert defaults["holes"] == [a, None]
    assert defaults["nested"] == [[a], [b]]
    assert defaults["rows"] == [{"title": "t", "document": a}]
    assert defaults["mixed"][1] == {"branch": 1, "value": 7}


def test_a_list_of_references_round_trips_through_build(tmp_path):
    def f(value: Annotated[list[Annotated[str, IsPathFile(extensions=(".pdf",))]],
                           Label("Docs")]) -> None: ...

    schema = signature_of(f)
    references = ["550e8400-e29b-41d4-a716-446655440000.pdf",
                  "550e8400-e29b-41d4-a716-446655440001.pdf"]

    # Untouched without a resolver, one call per reference and in order with one.
    assert decode(schema, {"value": references}) == {"value": references}

    stored = {reference: _stored(tmp_path, f"doc-{index}.pdf")
              for index, reference in enumerate(references)}

    seen = []

    def resolve(value):
        seen.append(value)
        return stored[value]

    prepared = decode(schema, {"value": references}, file_resolver=resolve)

    assert seen == references
    assert schema.build(prepared) == {"value": [stored[r] for r in references]}


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


class _Storage:
    """The host's side of the star: it stores bytes and maps references to paths.

    The browser mints an opaque reference and the core certifies a real file, so
    something has to sit between them. That something is the host, and the seam
    the library gives it is `decode(..., file_resolver=...)`. This stands in for
    it: every reference it is asked for is recorded, so the tests can still prove
    the reference crossed byte-identical, and answers with a real path.
    """

    def __init__(self, tmp_path):
        self.root = tmp_path / "storage"
        self.root.mkdir(parents=True, exist_ok=True)
        self.seen = []

    def resolve(self, reference):
        self.seen.append(reference)

        path = self.root / reference.replace("/", "_")
        path.write_bytes(b"bytes")

        return str(path)

    def path_of(self, reference):
        return str(self.root / reference.replace("/", "_"))


def _build(schema, read, storage):
    return schema.build(decode(schema, json.loads(json.dumps(read)),
                               file_resolver=storage.resolve))


# --- prefill: a default reaches the widget exactly as setValue() would ------
#
# A host prefills by compiling a schema whose defaults hold the record's current
# values, so the reference travels plan_of() -> JSON -> compileForm(). These
# drive the real browser modules over that whole path and compare the result
# against the same reference applied afterwards through setValue().

def test_a_single_file_prefill_arrives_as_the_widgets_current_reference(
        node, tmp_path):
    avatar = _stored(tmp_path, "ada.jpg")

    def prefilled(
        name: Annotated[str, Label("Name")] = "Ada",
        avatar_: Annotated[str, IsPathFile(extensions=(".jpg",)),
                           Label("Avatar")] = avatar,
    ) -> None: ...

    read = _file_star(node, tmp_path, prefilled, {})

    assert read == {"name": "Ada", "avatar_": avatar}


def test_a_multi_file_prefill_arrives_in_order(node, tmp_path):
    photos = [_stored(tmp_path, "a.jpg"), _stored(tmp_path, "b.jpg")]

    def prefilled(
        photos_: Annotated[list[Annotated[str, IsPathFile(extensions=(".jpg",))]],
                           Label("Photos")] = photos,
    ) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {"photos_": photos}


def test_a_nested_file_prefill_reaches_the_widget_inside_the_struct(
        node, tmp_path):
    avatar = _stored(tmp_path, "nested.jpg")

    @dataclass
    class Inner:
        name: Annotated[str, Label("Name")]
        avatar: Annotated[str, IsPathFile(extensions=(".jpg",)), Label("Avatar")]

    def prefilled(profile: Inner = Inner("Ada", avatar)) -> None: ...

    read = _file_star(node, tmp_path, prefilled, {})

    assert read == {"profile": {"name": "Ada", "avatar": avatar}}


def test_an_optional_file_prefilled_with_none_arrives_switched_off(
        node, tmp_path):
    def prefilled(
        doc: Annotated[str, IsPathFile(), Label("Doc")] | None = None,
    ) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {"doc": None}


def test_a_list_prefill_inside_a_dataclass_reaches_the_multiple_widget(
        node, tmp_path):
    photos = [_stored(tmp_path, "p1.jpg"), _stored(tmp_path, "p2.jpg")]

    @dataclass
    class Gallery2:
        photos: Annotated[list[Annotated[str, IsPathFile(extensions=(".jpg",))]],
                          Label("Photos")]

    def prefilled(gallery: Gallery2 = Gallery2(photos)) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {
        "gallery": {"photos": photos}}


@pytest.mark.parametrize("name, make", [
    ("missing", lambda tmp: "prefill-does-not-exist.pdf"),
    ("directory", lambda tmp: str(tmp)),
])
def test_a_prefill_the_core_cannot_certify_never_produces_a_plan(
        tmp_path, name, make):
    # The point of the strict route: a prefill is a temporary default, so it gets
    # the same certification. A path the core cannot certify fails *before* the
    # plan exists, which is what stops the form from showing a file that is not
    # there. There is nothing to work around here.
    value = make(tmp_path)

    def prefilled(doc: Annotated[str, IsPathFile(), Label("Doc")] = value) -> None: ...

    with pytest.raises(Exception, match="file does not exist|not a file"):
        plan_of(prefilled)


def test_a_list_prefill_with_one_missing_element_never_produces_a_plan(tmp_path):
    present = _stored(tmp_path, "here.pdf")

    def prefilled(
        docs: Annotated[list[Annotated[str, IsPathFile()]],
                        Label("Docs")] = [present, "gone.pdf"],
    ) -> None: ...

    with pytest.raises(Exception, match="file does not exist"):
        plan_of(prefilled)


def test_a_prefilled_default_matches_the_same_reference_set_afterwards(
        node, tmp_path):
    # The equivalence, across the real boundary: compiling with the default and
    # compiling without it then calling setValue() report the same read().
    avatar = _stored(tmp_path, "same.jpg")

    def with_default(
        avatar_: Annotated[str, IsPathFile(extensions=(".jpg",)),
                           Label("Avatar")] = avatar,
    ) -> None: ...

    def without_default(
        avatar_: Annotated[str, IsPathFile(extensions=(".jpg",)),
                           Label("Avatar")],
    ) -> None: ...

    planted = _file_star(node, tmp_path, without_default,
                         {"set": {"avatar_": avatar}})

    assert _file_star(node, tmp_path, with_default, {}) == planted


def test_editing_without_touching_the_file_returns_it_byte_identical(node, tmp_path):
    # The guarantee: a struct with an internal path goes to the form and back
    # complete without moving bytes. The record is set on the widgets, only the
    # name is edited, and read() returns the User with the avatar untouched. The
    # reference reaches the host's resolver exactly as it went in — that identity
    # is the point, and it is what survives the crossing now that build() wants a
    # real path rather than a promise.
    read = _file_star(node, tmp_path, User,
                      {"set": {"name": "Ada Lovelace", "avatar": "avatars/ada.jpg"}})

    assert read == {"name": "Ada Lovelace", "avatar": "avatars/ada.jpg"}

    schema = struct_of(User)
    storage = _Storage(tmp_path)
    built = _build(schema, read, storage)

    assert storage.seen == ["avatars/ada.jpg"]               # byte-identical
    assert built == User("Ada Lovelace", storage.path_of("avatars/ada.jpg"))


def test_replacing_the_file_transports_a_fresh_generated_reference(node, tmp_path):
    read = _file_star(node, tmp_path, User, {
        "set": {"name": "Ada", "avatar": "avatars/ada.jpg"},
        "choose": {"avatar": ["new-photo.jpg"]},
    })

    assert read["name"] == "Ada"
    assert read["avatar"] != "avatars/ada.jpg"               # a new local choice
    assert read["avatar"].endswith(".jpg")

    schema = struct_of(User)
    storage = _Storage(tmp_path)
    built = _build(schema, read, storage)

    assert storage.seen == [read["avatar"]]
    assert built.avatar == storage.path_of(read["avatar"])


def test_the_chosen_file_name_leads_the_reference_across_the_wire(node, tmp_path):
    # The name the widget slugs is part of the reference, so it has to survive the
    # crossing intact: JSON and decode() both treat it as plain text.
    read = _file_star(node, tmp_path, User,
                      {"choose": {"avatar": ["Informe Añual.jpg"]}})

    assert read["avatar"].startswith("informe-anual-")
    assert read["avatar"].endswith(".jpg")

    schema = struct_of(User)
    storage = _Storage(tmp_path)
    built = _build(schema, read, storage)

    assert storage.seen == [read["avatar"]]
    assert built.avatar == storage.path_of(read["avatar"])


def test_a_multi_file_struct_carries_distinct_references(node, tmp_path):
    read = _file_star(node, tmp_path, Gallery,
                      {"choose": {"photos": ["a.jpg", "b.jpg", "c.jpg"]}})

    assert len(read["photos"]) == 3
    assert len(set(read["photos"])) == 3                     # distinct references
    assert all(ref.endswith(".jpg") for ref in read["photos"])

    schema = struct_of(Gallery)
    storage = _Storage(tmp_path)
    built = _build(schema, read, storage)

    assert storage.seen == read["photos"]                    # once each, in order
    assert built.photos == [storage.path_of(r) for r in read["photos"]]
