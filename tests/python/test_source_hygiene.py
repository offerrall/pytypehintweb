import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The classic UTF-8-as-CP1252 mojibake prefix, built from escapes so this test
# does not itself count as an offender.
MOJIBAKE = chr(0x00D4) + chr(0x00C7)

SUFFIXES = {".py", ".js", ".mjs", ".css", ".md"}


def source_files():
    for base in (ROOT / "src", ROOT / "tests", ROOT / "docs"):
        for path in base.rglob("*"):
            if (path.is_file() and path.suffix in SUFFIXES
                    and "__pycache__" not in path.parts):
                yield path

    yield ROOT / "README.md"


def docs():
    for path in (ROOT / "docs").glob("*.md"):
        yield path

    yield ROOT / "README.md"


def test_no_committed_mojibake_sequence():
    offenders = [
        str(path.relative_to(ROOT))
        for path in source_files()
        if MOJIBAKE in path.read_text(encoding="utf-8", errors="replace")
    ]

    assert offenders == []


def test_no_document_claims_plans_lack_a_version():
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs()
        if "no version field" in path.read_text(encoding="utf-8")
        or "carries no version" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_no_document_keeps_the_old_choice_placeholder():
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs()
        if "choice_placeholder" in path.read_text(encoding="utf-8")
        or "Choose one" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_no_document_keeps_the_contextual_placeholder_heading():
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs()
        if "ontextual placeholder" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_the_plan_documents_branch_value_as_a_string_identifier():
    text = (ROOT / "docs" / "plan.md").read_text(encoding="utf-8")

    assert "non-empty transport identifier string" in text
    assert "A branch has no `label`" in text


def test_the_architecture_documents_the_adapter_slider_and_range_checks():
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "sliders with a reachable valid position" in text
    assert "contract it is about to emit" in text


def test_the_docs_document_step_versus_multiple_of():
    plan = (ROOT / "docs" / "plan.md").read_text(encoding="utf-8")
    python = (ROOT / "docs" / "python.md").read_text(encoding="utf-8")

    assert "used as the slider stride" in plan
    assert "decides where the control can land" in python


def test_no_document_keeps_a_stale_branch_label_reference():
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs()
        if "branch label" in path.read_text(encoding="utf-8").lower()
    ]

    assert offenders == []


def test_the_python_adapter_errors_include_range_and_slider_checks():
    text = (ROOT / "docs" / "python.md").read_text(encoding="utf-8")

    assert "exclusive integer bounds that leave no integer after conversion" in text
    assert "sliders with no reachable valid position" in text
    assert "converted defaults the browser could not represent or validate" in text


def test_the_docs_state_that_plan_defaults_must_satisfy_constraints():
    plan = (ROOT / "docs" / "plan.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "javascript.md").read_text(encoding="utf-8")

    assert "constraint-valid" in plan
    assert "constraint-valid" in architecture
    assert "full constraints of its node" in javascript


def test_architecture_lists_setvalue_in_the_widget_contract():
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "setValue" in text


def test_no_document_keeps_the_old_file_atom_name():
    # `IsPathFile` became `FileHint` in pytypehint 1.0.0 and there is no
    # compatibility path back, so the old name in a document is always stale.
    # The CHANGELOG is not scanned: its dated entries are a record of what was
    # true then, and the Unreleased entry says so.
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs()
        if "IsPathFile" in path.read_text(encoding="utf-8")
        or "is_path_file" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


FILESYSTEM_CLAIMS = ("file does not exist", "not a file", "file too small",
                     "file too large")


def test_no_document_claims_the_core_inspects_the_filesystem():
    # The core reads an extension off the text and opens nothing, so none of
    # these refusals can be raised any more. They were the backbone of the old
    # file doctrine, which is why the phrases themselves are banned rather than
    # left to be re-derived.
    offenders = [
        f"{path.relative_to(ROOT)}: {claim}"
        for path in docs()
        for claim in FILESYSTEM_CLAIMS
        if claim in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_the_docs_place_stored_bytes_with_the_host():
    # The replacement doctrine, asserted rather than assumed: a reference is
    # opaque, the byte bounds are the browser's courtesy, and the host owns
    # storage through the resolver.
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")
    python = (ROOT / "docs" / "python.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "A reference is not a path" in limitations
    assert "carries no bytes" in python
    assert "everything about stored bytes" in architecture


def test_getting_started_uses_form_onchange():
    text = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")

    assert "form.onChange(refresh)" in text
    assert "field.widget.onChange(refresh)" not in text


# The portable representation has one reader, and it is the core's. decode()
# delegates to schema.decode() and adds only the file resolution the core has
# no opinion about, so a second reader growing back here would be two answers
# to "what does this value mean" — the divergence 1.1.0 removed. These name the
# machinery of that reader rather than leaving it to be re-derived.

def adapter_sources():
    for name in ("decode.py", "plan.py", "types.py", "__init__.py"):
        yield ROOT / "src" / "pytypehintweb" / name


PORTABLE_READING = ("fromisoformat", "timespec")


def test_the_adapter_does_not_read_the_portable_spelling_itself():
    # Restoring a date or a time from its text is the core's reading, pinned
    # there to a canonical spelling. A second one here would accept spellings
    # the core declines, and the value's text would start selecting an option.
    offenders = [
        f"{path.relative_to(ROOT)}: {token}"
        for path in adapter_sources()
        for token in PORTABLE_READING
        if token in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_decode_grows_no_reader_of_its_own():
    # The module, not the function `pytypehintweb.decode` re-exports: asking a
    # function for these attributes answers no whatever the module holds, and
    # the assertion would pass with the whole walker back in place.
    decode_module = importlib.import_module("pytypehintweb.decode")

    # The helpers the old walker was made of. Naming them is cheaper than
    # describing the shape of the thing that must not come back. _transport_type
    # is deliberately absent: it groups options by the type they arrive as,
    # which is transport routing and not a reading of a value.
    gone = ("_to_date", "_to_time", "_to_enum_member", "_decode_scalar",
            "_decode_string", "_decode_list", "_decode_options",
            "_decode_wrapped", "_decode_struct", "_decode_inline_struct")

    assert [name for name in gone if hasattr(decode_module, name)] == []


def test_decode_imports_no_shape_the_core_reads_for_it():
    text = (ROOT / "src" / "pytypehintweb" / "decode.py").read_text(
        encoding="utf-8")

    imported = {name.strip()
                for line in text.splitlines() if line.startswith("from pytypehint ")
                for name in line.split("import", 1)[1].split(",")}

    # Date, Time, Float, Int and EnumShape are exactly the shapes whose portable
    # spelling the core restores. Importing one here means something in this
    # module is deciding what such a value means. Matched against the import
    # list rather than the whole text, so an ordinary word cannot trip it.
    assert imported.isdisjoint({"Date", "Time", "Float", "Int", "EnumShape"})
