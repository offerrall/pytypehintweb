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


def test_getting_started_uses_form_onchange():
    text = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")

    assert "form.onChange(refresh)" in text
    assert "field.widget.onChange(refresh)" not in text
