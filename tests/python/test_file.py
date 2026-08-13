import json
from dataclasses import dataclass
from typing import Annotated

import pytest

from pytypehint import (
    Choices, FileHint, IsPassword, Label, Max, Min, Pattern, Placeholder,
    Rows, signature_of, struct_of,
)
from pytypehintweb import WebConfig, decode, plan_of
from pytypehintweb import plan as plan_module


# A file field is a reference passing through four hands, and each of them
# answers for a different thing:
#
#   the core        reads the extension off the text and nothing else. FileHint
#                   declares min_size / max_size and never measures them; it
#                   opens nothing, so existence, regular-file-ness and byte size
#                   are not its business and no longer refuse a schema.
#   pytypehintweb   turns the shape into a `file` node and carries extensions,
#                   minSize and maxSize to the browser. It refuses only what
#                   JSON and JavaScript cannot represent, and never touches
#                   storage.
#   the browser     filters a local pick by extension and weighs its File.size
#                   against the bounds — the one case where bytes are known.
#   the host        owns the bytes. Whether a reference exists, has expired,
#                   belongs to this caller or is the right size is decided in
#                   its file_resolver, the only seam the library offers it.
#
# A reference is not a path and carries no bytes, so no test here needs a real
# file on disk: the values are plain reference strings, which is exactly what
# crosses the wire.

def _node(fn):
    return plan_of(fn)["fields"][0]["node"]


# --- the file node ----------------------------------------------------------

def test_plan_of_emits_a_single_file_node():
    def f(value: Annotated[str, FileHint()]) -> None: ...

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
    def f(value: Annotated[str, FileHint(extensions=(".pdf", ".docx"))]) -> None: ...

    assert _node(f)["options"]["extensions"] == [".pdf", ".docx"]


def test_the_invalid_message_comes_from_the_web_config():
    def f(value: Annotated[str, FileHint()]) -> None: ...

    config = WebConfig(file_invalid_message="Wrong kind of file")
    node = plan_of(f, config=config)["fields"][0]["node"]

    assert node["options"]["invalidMessage"] == "Wrong kind of file"


# --- deferred combinations --------------------------------------------------

# The core allows each of these atoms beside FileHint; the adapter defers the
# combination until a real case asks for it, the same way it defers Float.slider.
@pytest.mark.parametrize("name, atom", [
    ("min", Min(1)),
    ("max", Max(5)),
    ("pattern", Pattern(r"[a-z]+")),
    ("choices", Choices(values=("report.pdf",))),
    ("is_password", IsPassword()),
    ("rows", Rows(3)),
    ("placeholder", Placeholder("Pick a file")),
])
def test_filehint_with_another_str_atom_is_deferred(name, atom):
    def f(value: Annotated[str, FileHint(), atom]) -> None: ...

    with pytest.raises(TypeError,
                       match=f"Str.{name} with FileHint is not supported yet"):
        plan_of(f)


def test_a_plain_filehint_carries_no_size_bounds():
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    node = _node(f)

    assert node["kind"] == "file"
    assert node["options"]["minSize"] is None
    assert node["options"]["maxSize"] is None


# --- byte-size bounds: declared here, weighed only in the browser -----------
#
# FileHint(min_size=..., max_size=...) is a declaration. The core validates its
# shape (a non-negative int, min <= max) and then never measures anything. The
# bounds travel on the node so FileWidget can refuse a local File whose .size
# already breaks one, before any upload. That is the only place a byte count is
# ever known: a reference — a plan default, or one planted with setValue() —
# carries no bytes, so nothing weighs it. An authoritative bound over stored
# bytes belongs to the host, beside the storage it owns.

@pytest.mark.parametrize("mark, expected", [
    (FileHint(min_size=1), (1, None)),
    (FileHint(max_size=1024), (None, 1024)),
    (FileHint(min_size=1, max_size=1_000_000), (1, 1_000_000)),
    (FileHint(min_size=0), (0, None)),
    (FileHint(min_size=512, max_size=512), (512, 512)),
])
def test_byte_size_bounds_travel_on_the_file_node(mark, expected):
    def f(value: Annotated[str, mark]) -> None: ...

    options = _node(f)["options"]

    assert (options["minSize"], options["maxSize"]) == expected


def test_the_size_messages_come_from_the_web_config():
    def f(value: Annotated[str, FileHint(min_size=1, max_size=2)]) -> None: ...

    config = WebConfig(file_min_size_message="Under {value}",
                       file_max_size_message="Over {value}")
    options = plan_of(f, config=config)["fields"][0]["node"]["options"]

    assert options["minSizeMessage"] == "Under {value}"
    assert options["maxSizeMessage"] == "Over {value}"


def test_a_size_bound_beyond_the_safe_integer_range_is_refused():
    # The plan is JSON read by JavaScript. The core has no reason to care, so
    # this is the one thing left to check here.
    def f(value: Annotated[str, FileHint(max_size=2 ** 60)]) -> None: ...

    with pytest.raises(TypeError, match="FileHint.max_size"):
        plan_of(f)


def test_the_bounds_survive_json():
    def f(value: Annotated[str, FileHint(min_size=1, max_size=1024)]) -> None: ...

    options = json.loads(json.dumps(_node(f)))["options"]

    assert options["minSize"] == 1
    assert options["maxSize"] == 1024


@pytest.mark.parametrize("name, mark", [
    ("under the minimum", FileHint(min_size=1_000_000)),
    ("over the maximum", FileHint(max_size=1)),
])
def test_a_default_reference_is_never_weighed_against_the_bounds(name, mark):
    # Nothing here can weigh a reference: it names bytes it does not carry. The
    # core does not open it, the adapter does not either, and the browser shows
    # it as the current file without a size beside it. The bound still travels,
    # for the next local pick.
    def f(value: Annotated[str, mark] = "already-stored.bin") -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == "already-stored.bin"
    assert field["node"]["options"]["minSize"] == mark.min_size
    assert field["node"]["options"]["maxSize"] == mark.max_size


def test_build_does_not_weigh_a_value_against_the_bounds_either():
    # The same on the way back. A host that needs the guarantee enforces it over
    # its own storage; the pipeline only carries the declaration.
    def f(value: Annotated[str, FileHint(min_size=1000, max_size=2000)]) -> None: ...

    schema = signature_of(f)

    assert schema.build(decode(schema, {"value": "anything.bin"})) == {
        "value": "anything.bin"}


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


_BOUNDED = Annotated[str, FileHint(extensions=(".pdf",),
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


def test_filehint_composes_with_field_label_and_description():
    # Label and Description are the field's, not the Str's, so they are not among
    # the deferred atoms: a labelled file field is fine.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",)), Label("Resume")]) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["label"] == "Resume"
    assert field["node"]["kind"] == "file"


# --- what the core still refuses --------------------------------------------
#
# One thing, and it is a text check: the extension. It applies to a default
# while the schema compiles and to a value at build(), with the same words.

def test_the_core_refuses_a_default_with_the_wrong_extension():
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]
          = "note.txt") -> None: ...

    with pytest.raises(Exception, match="not an accepted file type"):
        plan_of(f)


def test_the_core_refuses_a_default_that_is_not_a_string():
    def f(value: Annotated[str, FileHint()] = 7) -> None: ...

    with pytest.raises(Exception, match="expected str"):
        plan_of(f)


def test_the_core_names_the_offending_element_of_a_list_default():
    def f(value: Annotated[list[Annotated[str, FileHint(extensions=(".pdf",))]],
                           Label("Docs")] = ["ok.pdf", "note.txt"]) -> None: ...

    with pytest.raises(Exception, match=r"\[1\]: not an accepted file type"):
        plan_of(f)


@pytest.mark.parametrize("name, mark, default", [
    ("below the minimum", Min(2), ["one.pdf"]),
    ("above the maximum", Max(1), ["one.pdf", "two.pdf"]),
])
def test_the_core_still_counts_a_list_default_against_its_bounds(
        name, mark, default):
    # A count is not a filesystem question, so this one survived 1.0.0 intact.
    def f(value: Annotated[list[Annotated[str, FileHint()]],
                           mark, Label("Docs")] = default) -> None: ...

    with pytest.raises(Exception, match="too few items|too many items"):
        plan_of(f)


# --- what the core no longer refuses ----------------------------------------
#
# The line that moved in 1.0.0. A file value used to have to be a real local
# file: `file does not exist`, `not a file`, `file too small` and `file too
# large` refused the schema before a plan could exist. The core opens nothing
# now, so a reference written in the host's own vocabulary compiles, renders and
# travels — which is the point, since a host whose storage is an object store
# never had a local path to offer in the first place.

@pytest.mark.parametrize("name, reference", [
    ("a name no local file answers to", "no-such-file.pdf"),
    ("an object-store key", "records/2011/summer/ada.pdf"),
    ("an absolute-looking path that is not there", "/var/records/2011.pdf"),
])
def test_a_reference_that_names_no_local_file_reaches_the_plan(name, reference):
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]
          = reference) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == reference


def test_a_directory_is_no_longer_a_special_case(tmp_path):
    # `not a file` went with the rest: to the core the value is text, and this
    # one happens to name a directory that exists. Nothing looks.
    def f(value: Annotated[str, FileHint()] = str(tmp_path)) -> None: ...

    assert plan_of(f)["fields"][0]["default"] == str(tmp_path)


# --- a file default is an existing reference --------------------------------
#
# It means exactly what FileWidget.setValue() means: a reference the host
# declares, shown as the current file and transported back untouched. It carries
# no bytes and starts no upload.

def test_a_file_field_carries_its_default_reference_into_the_plan():
    existing = "records/existing-doc.pdf"

    def f(value: Annotated[str, FileHint(extensions=(".pdf",)),
                           Label("Doc")] = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["hasDefault"] is True
    assert field["default"] == existing
    assert isinstance(field["default"], str)
    assert field["node"]["kind"] == "file"


def test_an_optional_file_accepts_a_none_default():
    # The off state of an optional file is the toggle; `None` is how the plan
    # spells it, exactly as for every other optional scalar.
    def f(value: Annotated[str, FileHint(), Label("Doc")] | None = None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["hasDefault"] is True
    assert field["default"] is None
    assert field["enabled"] is False


def test_an_optional_file_accepts_a_reference_default():
    existing = "records/kept.pdf"

    def f(value: Annotated[str, FileHint(extensions=(".pdf",)),
                           Label("Doc")] | None = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["default"] == existing
    assert field["enabled"] is True


def test_a_list_of_files_carries_a_list_of_references():
    existing = ["records/one.pdf", "records/two.pdf"]

    def f(value: Annotated[list[Annotated[str, FileHint()]],
                           Label("Docs")] = existing) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["node"]["options"]["multiple"] is True
    assert field["default"] == existing              # order preserved
    assert all(isinstance(item, str) for item in field["default"])


def test_a_list_of_files_accepts_an_empty_default():
    def f(value: Annotated[list[Annotated[str, FileHint()]],
                           Label("Docs")] = []) -> None: ...

    assert plan_of(f)["fields"][0]["default"] == []


def test_a_file_default_survives_json_as_plain_text():
    existing = "records/report.pdf"

    def f(value: Annotated[str, FileHint(extensions=(".pdf",))] = existing,
          docs: Annotated[list[Annotated[str, FileHint()]],
                          Label("Docs")] = []) -> None: ...

    plan = plan_of(f)
    restored = json.loads(json.dumps(plan))

    assert restored == plan
    assert isinstance(restored["fields"][0]["default"], str)
    assert "Path(" not in json.dumps(plan)


def test_a_reference_in_the_hosts_own_vocabulary_can_be_a_schema_default():
    # The architectural seam, stated as a test. A default used to have to be a
    # local path, so a host whose references were object-store keys could not
    # express a prefill in a schema at all and had to plant it with setValue()
    # after mounting. Both roads are open now, and they are the same road: the
    # plan default reaches the widget through setValue(), and the reference is
    # redeemed on the way back with decode(file_resolver=...).
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]
          = "s3://reports/9f3a1c.pdf") -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == "s3://reports/9f3a1c.pdf"
    assert field["node"]["kind"] == "file"


def test_a_file_default_inside_a_dataclass_reaches_the_nested_node():
    # A nested default follows the same walk as any other initial value: the
    # object travels whole and the file inside it is not dropped on the way.
    avatar = "avatars/ada.jpg"

    @dataclass
    class Profile:
        name: Annotated[str, Label("Name")]
        avatar: Annotated[str, FileHint(extensions=(".jpg",)), Label("Avatar")]

    def f(profile: Profile = Profile("Ada", avatar)) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == {"name": "Ada", "avatar": avatar}
    assert field["node"]["kind"] == "object"


def test_a_list_of_files_inside_a_dataclass_keeps_its_references():
    photos = ["albums/a.jpg", "albums/b.jpg"]

    @dataclass
    class Album:
        photos: Annotated[list[Annotated[str, FileHint(extensions=(".jpg",))]],
                          Label("Photos")]

    def f(album: Album = Album(photos)) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["default"] == {"photos": photos}


def test_an_optional_file_without_a_default_is_fine():
    def f(value: Annotated[str, FileHint(), Label("Optional file")] | None) -> None: ...

    field = plan_of(f)["fields"][0]

    assert field["optional"] is True
    assert field["hasDefault"] is False
    assert field["node"]["kind"] == "file"


# --- transport: a file is a str on the wire ---------------------------------

def test_a_generated_reference_travels_untouched_through_decode():
    # The widget mints a reference shaped like <name>-<uuid>.<ext>; on the wire it
    # is a plain string. decode prepares, it does not validate, so with no
    # resolver the reference reaches the core exactly as it was typed into JSON.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    reference = "informe-anual-550e8400-e29b-41d4-a716-446655440000.pdf"

    assert decode(schema, {"value": reference}) == {"value": reference}


def test_build_accepts_a_reference_no_resolver_ever_redeemed():
    # The guarantee that went away, written down as what it became. build() used
    # to refuse a reference whose bytes were never stored, so a host that forgot
    # to wire its resolver found out here. Nothing between the browser and the
    # core knows what storage means any more, so the reference builds into the
    # plain string it always was. Refusing it is the host's call, made in the
    # file_resolver — see the tests below.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)

    assert schema.build(decode(schema, {"value": "never-uploaded-1234.pdf"})) == {
        "value": "never-uploaded-1234.pdf"}


def test_build_still_filters_the_reference_by_extension():
    # The extension is a filter for honest mistakes, applied by the core on the
    # way in exactly as the widget applies it on the way out.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)

    with pytest.raises(Exception, match="not an accepted file type"):
        schema.build(decode(schema, {"value": "note.txt"}))


# --- the resolver is the host's seam ----------------------------------------

def test_the_resolver_receives_the_reference_byte_identical():
    # The mapping the host owns: reference in, whatever the host wants to hand
    # the pipeline out. It is called once, with the reference exactly as the
    # browser minted it, and its answer continues as the value.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    reference = "informe-anual-550e8400-e29b-41d4-a716-446655440000.pdf"
    stored = "/srv/uploads/informe-anual.pdf"

    seen = []

    def resolve(value):
        seen.append(value)
        return stored

    prepared = decode(schema, {"value": reference}, file_resolver=resolve)

    assert seen == [reference]
    assert schema.build(prepared) == {"value": stored}


def test_a_resolver_that_refuses_a_reference_raises_through_decode():
    # How a host says no now that the core has stopped saying it. decode() does
    # not catch: the host's own exception — unknown, expired, not yours — reaches
    # the caller unchanged, with its own type and its own message.
    class UnknownUpload(LookupError):
        pass

    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    def resolve(reference):
        raise UnknownUpload(f"no such upload: {reference}")

    with pytest.raises(UnknownUpload, match="no such upload: ghost.pdf"):
        decode(signature_of(f), {"value": "ghost.pdf"},
               file_resolver=resolve)


def test_a_resolver_refusal_inside_a_list_stops_the_walk():
    # The same, reached through a list: nothing swallows it and nothing carries
    # on to the next element with a half-decoded object.
    class UnknownUpload(LookupError):
        pass

    def f(value: Annotated[list[Annotated[str, FileHint()]],
                           Label("Docs")]) -> None: ...

    seen = []

    def resolve(reference):
        seen.append(reference)

        if reference == "gone.pdf":
            raise UnknownUpload(reference)

        return f"/srv/{reference}"

    with pytest.raises(UnknownUpload):
        decode(signature_of(f), {"value": ["here.pdf", "gone.pdf", "next.pdf"]},
               file_resolver=resolve)

    assert seen == ["here.pdf", "gone.pdf"]          # stopped where it failed


def test_the_core_reads_the_extension_of_what_the_resolver_returned():
    # The resolver's answer is the value that continues, so it faces the one
    # check the core still makes. A host answering with a bare key fails at
    # build() — not because bytes are missing, which nothing here can tell, but
    # because the resolved text carries no accepted extension.
    def f(value: Annotated[str, FileHint(extensions=(".pdf",))]) -> None: ...

    schema = signature_of(f)
    prepared = decode(schema, {"value": "report.pdf"},
                      file_resolver=lambda reference: "s3://bucket/9f3a1c")

    with pytest.raises(Exception, match="not an accepted file type"):
        schema.build(prepared)

    # An answer that keeps an accepted extension goes through, which is why the
    # demo resolves to a path and not to a bare key.
    kept = decode(schema, {"value": "report.pdf"},
                  file_resolver=lambda reference: "s3://bucket/9f3a1c.pdf")

    assert schema.build(kept) == {"value": "s3://bucket/9f3a1c.pdf"}


def test_a_resolver_answer_is_not_weighed_against_the_byte_bounds():
    # Whatever the host answers, it is text to everything downstream. The bounds
    # were the browser's business and stayed there.
    def f(value: Annotated[str, FileHint(min_size=10_000)]) -> None: ...

    schema = signature_of(f)
    prepared = decode(schema, {"value": "tiny.bin"},
                      file_resolver=lambda reference: "/srv/tiny.bin")

    assert schema.build(prepared) == {"value": "/srv/tiny.bin"}


# --- unions -----------------------------------------------------------------

def test_str_and_file_share_the_option_id_str_and_the_core_rejects_the_union():
    # A file is a Str, so option_id() is "str" for both branches. str | file is
    # two branches with the same option id: the core rejects it while compiling
    # the field (duplicate option types), before plan_of ever runs.
    def f(value: str | Annotated[str, FileHint()]) -> None: ...

    with pytest.raises(ValueError, match="duplicate option types"):
        signature_of(f)


def test_a_list_of_file_or_str_is_rejected_by_the_core_as_well():
    # New in pytypehint 1.0.0: the identity rule reaches inside lists too, in its
    # own words rather than the field's. list[File | str] used to compile and
    # arrive here, where the adapter's own guard refused it; the collision is now
    # named earlier and better, so the adapter's guard is defense in depth for
    # shapes assembled off the compiler's path (see test_adapter_hardening).
    def f(value: Annotated[list[Annotated[str, FileHint()] | str],
                           Label("V")]) -> None: ...

    with pytest.raises(ValueError, match="both compile to str"):
        signature_of(f)


def test_a_file_in_a_sane_union_compiles_with_the_str_branch_id():
    # file | int: distinct transports (string vs number) and distinct option ids
    # ("str" vs "int"), so the union is sound.
    def f(value: Annotated[str, FileHint()] | int) -> None: ...

    node = _node(f)

    assert node["kind"] == "choice"
    assert {b["value"]: b["node"]["kind"] for b in node["branches"]} == {
        "str": "file", "int": "int"}
    assert {b["value"]: b["mode"] for b in node["branches"]} == {
        "str": "plain", "int": "plain"}


def test_a_file_collides_with_a_date_on_transport_and_travels_wrapped():
    from datetime import date

    def f(value: Annotated[str, FileHint()] | date) -> None: ...

    modes = {b["value"]: b["mode"] for b in _node(f)["branches"]}

    assert modes == {"str": "wrapped", "date": "wrapped"}


# --- multi-file: list[File] is one multiple file node -----------------------

def test_a_list_of_files_is_one_multiple_file_node():
    def f(value: Annotated[list[Annotated[str, FileHint(extensions=(".pdf",))]],
                           Min(1), Max(3), Label("Attachments")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "file"
    assert node["options"]["multiple"] is True
    assert node["options"]["extensions"] == [".pdf"]
    assert node["options"]["minFiles"] == 1
    assert node["options"]["maxFiles"] == 3


def test_a_list_of_files_without_bounds_has_null_file_counts():
    def f(value: Annotated[list[Annotated[str, FileHint()]], Label("Docs")]) -> None: ...

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
    document: Annotated[str, FileHint(), Label("Doc")]


def test_a_list_of_optional_files_is_a_list_of_optional_nodes():
    def f(value: Annotated[list[Annotated[str, FileHint()] | None],
                           Label("Docs")]) -> None: ...

    node = _node(f)

    assert node["kind"] == "list"
    assert node["item"]["kind"] == "optional"
    assert node["item"]["node"]["kind"] == "file"


def test_a_list_of_file_or_int_is_a_list_of_choices():
    def f(value: Annotated[list[Annotated[str, FileHint()] | int],
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
    def f(value: Annotated[list[list[Annotated[str, FileHint()]]],
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
        docs: Annotated[list[Annotated[str, FileHint()]], Label("Docs")]

    def f(value: Annotated[list[Bundle], Label("Bundles")]) -> None: ...

    node = _node(f)

    assert node["item"]["fields"][0]["node"]["options"]["multiple"] is True


def test_no_rule_rejects_a_shape_merely_for_holding_a_file():
    # The regression guard for the block this replaced. Each of these used to
    # raise "a file inside a list is only supported as a plain list[File]".
    @dataclass
    class Holder:
        doc: Annotated[str, FileHint(), Label("Doc")]

    def optional_items(v: Annotated[list[Annotated[str, FileHint()] | None],
                                    Label("V")]) -> None: ...
    def union_items(v: Annotated[list[Annotated[str, FileHint()] | int],
                                 Label("V")]) -> None: ...
    def nested(v: Annotated[list[list[Annotated[str, FileHint()]]],
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
        avatar: Annotated[str, FileHint(), Label("Avatar")]

    @dataclass
    class Album:
        photos: Annotated[list[Annotated[str, FileHint()]], Label("Photos")]

    def one(value: Annotated[str, FileHint(), Label("V")]) -> None: ...
    def optional(value: Annotated[str, FileHint(), Label("V")] | None) -> None: ...
    def many(value: Annotated[list[Annotated[str, FileHint()]],
                              Label("V")]) -> None: ...
    def in_struct(value: Profile) -> None: ...
    def many_in_struct(value: Album) -> None: ...
    def in_union(value: Annotated[str, FileHint()] | int) -> None: ...
    def list_optional(value: Annotated[list[Annotated[str, FileHint()] | None],
                                       Label("V")]) -> None: ...
    def list_union(value: Annotated[list[Annotated[str, FileHint()] | int],
                                    Label("V")]) -> None: ...
    def list_list(value: Annotated[list[list[Annotated[str, FileHint()]]],
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


def test_decode_resolves_a_file_inside_a_list_of_optionals():
    def f(value: Annotated[list[Annotated[str, FileHint()] | None],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": ["a.pdf", None]},
                 file_resolver=resolve)

    assert seen == ["a.pdf"]                 # None never reaches the resolver
    assert out == {"value": ["/resolved/a.pdf", None]}


def test_decode_resolves_only_the_file_branch_of_a_mixed_list():
    def f(value: Annotated[list[Annotated[str, FileHint()] | int],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": ["a.pdf", 7]}, file_resolver=resolve)

    assert seen == ["a.pdf"]
    assert out == {"value": ["/resolved/a.pdf", 7]}


def test_decode_resolves_every_file_of_a_nested_list_in_order():
    def f(value: Annotated[list[list[Annotated[str, FileHint()]]],
                           Label("V")]) -> None: ...

    seen, resolve = _recording_resolver()
    out = decode(signature_of(f), {"value": [["a.pdf"], ["b.pdf", "a.pdf"]]},
                 file_resolver=resolve)

    assert seen == ["a.pdf", "b.pdf", "a.pdf"]   # once per reference, in order
    assert out == {"value": [["/resolved/a.pdf"],
                             ["/resolved/b.pdf", "/resolved/a.pdf"]]}


def test_a_list_of_structs_with_a_file_round_trips_through_build(tmp_path):
    # The whole way round for the shape that used to be refused: plan, transport,
    # decode with a resolver, and the core building the real objects.
    a, b = "uploads/a.pdf", "uploads/b.pdf"

    def f(items: Annotated[list[Attachment], Label("Items")]) -> None: ...

    schema = signature_of(f)
    body = {"items": [{"title": "one", "document": a},
                      {"title": "two", "document": b}]}

    storage = _Storage(tmp_path)
    built = schema.build(decode(schema, json.loads(json.dumps(body)),
                                file_resolver=storage.resolve))

    assert storage.seen == [a, b]
    assert [row.title for row in built["items"]] == ["one", "two"]
    assert [row.document for row in built["items"]] == [
        storage.path_of(a), storage.path_of(b)]


def test_a_deep_default_survives_json_and_carries_no_path_objects():
    a, b = "uploads/a.pdf", "uploads/b.pdf"

    def f(
        holes: Annotated[list[Annotated[str, FileHint()] | None],
                         Label("H")] = [a, None],
        mixed: Annotated[list[Annotated[str, FileHint()] | int],
                         Label("M")] = [a, 7],
        nested: Annotated[list[list[Annotated[str, FileHint()]]],
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


def test_a_list_of_references_round_trips_through_build():
    def f(value: Annotated[list[Annotated[str, FileHint(extensions=(".pdf",))]],
                           Label("Docs")]) -> None: ...

    schema = signature_of(f)
    references = ["550e8400-e29b-41d4-a716-446655440000.pdf",
                  "550e8400-e29b-41d4-a716-446655440001.pdf"]

    # Untouched without a resolver, one call per reference and in order with one.
    assert decode(schema, {"value": references}) == {"value": references}

    stored = {reference: f"/srv/doc-{index}.pdf"
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
    avatar: Annotated[str, FileHint(extensions=(".jpg",)), Label("Avatar")]


@dataclass
class Gallery:
    photos: Annotated[list[Annotated[str, FileHint(extensions=(".jpg",))]],
                      Label("Photos")]


def _file_star_result(node, tmp_path, obj, ops):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan_of(obj), separators=(",", ":")),
                         encoding="utf-8")

    ops_path = tmp_path / "ops.json"
    ops_path.write_text(json.dumps(ops), encoding="utf-8")

    return node("file-star-runner.mjs", str(plan_path), str(ops_path))


def _file_star(node, tmp_path, obj, ops):
    return _file_star_result(node, tmp_path, obj, ops)["read"]


class _Storage:
    """The host's side of the star: it maps references to whatever it stores.

    The browser mints an opaque reference and the core only ever reads an
    extension off it, so something has to know where the bytes went. That
    something is the host, and the seam the library gives it is
    `decode(..., file_resolver=...)`. This stands in for it: every reference it
    is asked for is recorded, so the tests can prove the reference crossed
    byte-identical, and it answers with the path it would have stored under. It
    touches no disk, because nothing downstream of it does either.
    """

    def __init__(self, tmp_path):
        self.root = tmp_path / "storage"
        self.seen = []

    def resolve(self, reference):
        self.seen.append(reference)

        return self.path_of(reference)

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
    avatar = "avatars/ada.jpg"

    def prefilled(
        name: Annotated[str, Label("Name")] = "Ada",
        avatar_: Annotated[str, FileHint(extensions=(".jpg",)),
                           Label("Avatar")] = avatar,
    ) -> None: ...

    read = _file_star(node, tmp_path, prefilled, {})

    assert read == {"name": "Ada", "avatar_": avatar}


def test_a_multi_file_prefill_arrives_in_order(node, tmp_path):
    photos = ["albums/a.jpg", "albums/b.jpg"]

    def prefilled(
        photos_: Annotated[list[Annotated[str, FileHint(extensions=(".jpg",))]],
                           Label("Photos")] = photos,
    ) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {"photos_": photos}


def test_a_nested_file_prefill_reaches_the_widget_inside_the_struct(
        node, tmp_path):
    avatar = "avatars/nested.jpg"

    @dataclass
    class Inner:
        name: Annotated[str, Label("Name")]
        avatar: Annotated[str, FileHint(extensions=(".jpg",)), Label("Avatar")]

    def prefilled(profile: Inner = Inner("Ada", avatar)) -> None: ...

    read = _file_star(node, tmp_path, prefilled, {})

    assert read == {"profile": {"name": "Ada", "avatar": avatar}}


def test_an_optional_file_prefilled_with_none_arrives_switched_off(
        node, tmp_path):
    def prefilled(
        doc: Annotated[str, FileHint(), Label("Doc")] | None = None,
    ) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {"doc": None}


def test_a_list_prefill_inside_a_dataclass_reaches_the_multiple_widget(
        node, tmp_path):
    photos = ["albums/p1.jpg", "albums/p2.jpg"]

    @dataclass
    class Gallery2:
        photos: Annotated[list[Annotated[str, FileHint(extensions=(".jpg",))]],
                          Label("Photos")]

    def prefilled(gallery: Gallery2 = Gallery2(photos)) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {
        "gallery": {"photos": photos}}


@pytest.mark.parametrize("name, reference", [
    ("a key with no local counterpart", "s3://records/9f3a1c.pdf"),
    ("a name nothing on this machine answers to", "long-gone.pdf"),
])
def test_a_prefill_the_host_alone_understands_reaches_the_widget(
        node, tmp_path, name, reference):
    # What the strict route used to forbid. A prefill is a temporary default, so
    # it used to need a real local file and a host with an object store could not
    # render an edit form at all. The plan carries the reference now and the
    # widget shows it as the current file; whether it still stands for anything
    # is answered later, by the host's resolver.
    def prefilled(
        doc: Annotated[str, FileHint(extensions=(".pdf",)),
                       Label("Doc")] = reference,
    ) -> None: ...

    assert _file_star(node, tmp_path, prefilled, {}) == {"doc": reference}


def test_a_list_prefill_with_one_wrong_extension_never_produces_a_plan():
    # The one refusal left on the prefill road, and it is about the text: a form
    # is never rendered around a value its own field could not accept back.
    def prefilled(
        docs: Annotated[list[Annotated[str, FileHint(extensions=(".pdf",))]],
                        Label("Docs")] = ["here.pdf", "gone.txt"],
    ) -> None: ...

    with pytest.raises(Exception, match=r"\[1\]: not an accepted file type"):
        plan_of(prefilled)


def test_a_prefilled_default_matches_the_same_reference_set_afterwards(
        node, tmp_path):
    # The equivalence, across the real boundary: compiling with the default and
    # compiling without it then calling setValue() report the same read().
    avatar = "avatars/same.jpg"

    def with_default(
        avatar_: Annotated[str, FileHint(extensions=(".jpg",)),
                           Label("Avatar")] = avatar,
    ) -> None: ...

    def without_default(
        avatar_: Annotated[str, FileHint(extensions=(".jpg",)),
                           Label("Avatar")],
    ) -> None: ...

    planted = _file_star(node, tmp_path, without_default,
                         {"set": {"avatar_": avatar}})

    assert _file_star(node, tmp_path, with_default, {}) == planted


# --- the widget's local limits, driven from the plan -------------------------
#
# minSize / maxSize are enforced in exactly one place now, and this is it: a
# local File whose .size the browser can read. These drive the real modules over
# a plan plan_of() generated, so the bound is followed from the Python
# declaration to the message the user sees.

def _bounded_upload(node, tmp_path, size):
    def upload(
        doc: Annotated[str, FileHint(extensions=(".pdf",),
                                     min_size=100, max_size=1000),
                       Label("Doc")],
    ) -> None: ...

    return _file_star_result(node, tmp_path, upload,
                             {"choose": {"doc": [{"name": "report.pdf",
                                                  "size": size}]}})


def test_a_local_pick_inside_the_byte_bounds_mints_a_reference(node, tmp_path):
    result = _bounded_upload(node, tmp_path, 500)

    assert result["errors"]["doc"] is None
    assert result["read"]["doc"].endswith(".pdf")


@pytest.mark.parametrize("name, size, message", [
    ("too small", 10, "File is too small; minimum"),
    ("too large", 5000, "File is too large; maximum"),
])
def test_a_local_pick_outside_the_byte_bounds_is_refused_by_the_widget(
        node, tmp_path, name, size, message):
    result = _bounded_upload(node, tmp_path, size)

    assert message in result["errors"]["doc"]
    assert result["read"]["doc"] is None             # nothing minted, no upload


def test_a_planted_reference_is_not_weighed_because_it_carries_no_bytes(
        node, tmp_path):
    # The asymmetry the documentation insists on, as a test. The same field that
    # refuses a 10-byte local pick accepts a reference of unknown size, because
    # there is nothing to read a size from. Only the host can close that gap.
    def upload(
        doc: Annotated[str, FileHint(extensions=(".pdf",),
                                     min_size=100, max_size=1000),
                       Label("Doc")],
    ) -> None: ...

    result = _file_star_result(node, tmp_path, upload,
                               {"set": {"doc": "records/huge-or-tiny.pdf"}})

    assert result["errors"]["doc"] is None
    assert result["read"]["doc"] == "records/huge-or-tiny.pdf"


def test_editing_without_touching_the_file_returns_it_byte_identical(node, tmp_path):
    # The guarantee: a struct with a stored reference goes to the form and back
    # complete without moving bytes. The record is set on the widgets, only the
    # name is edited, and read() returns the User with the avatar untouched. The
    # reference reaches the host's resolver exactly as it went in — that identity
    # is the point, because it is all the host has to find the bytes with.
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
