import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#+\s+(.*)$", re.MULTILINE)

SELF = "https://github.com/offerrall/pytypehintweb/blob/main/"


def documents():
    return sorted([ROOT / "README.md", *(ROOT / "docs").glob("*.md")])


def slug(heading: str) -> str:
    text = re.sub(r"`|\*|_", "", heading).strip().lower()
    return re.sub(r"[^a-z0-9 -]", "", text).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    return {slug(h) for h in HEADING.findall(path.read_text(encoding="utf-8"))}


def relative_links():
    for document in documents():
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            yield document, target


def self_links():
    for document in documents():
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(SELF):
                yield document, target


@pytest.mark.parametrize("document", documents(), ids=lambda p: p.name)
def test_the_document_exists_and_is_not_empty(document):
    assert document.read_text(encoding="utf-8").strip() != ""


def test_every_link_into_this_repository_points_at_a_real_file():
    broken = []

    for document, target in self_links():
        path, _, anchor = target[len(SELF):].partition("#")
        destination = ROOT / path

        if not destination.is_file():
            broken.append(f"{document.name}: {target}")
            continue

        if anchor and anchor not in anchors(destination):
            broken.append(f"{document.name}: {target} (missing anchor)")

    assert broken == []


def test_the_readme_links_to_every_documentation_page():
    readme = ROOT / "README.md"
    linked = set()

    for document, target in relative_links():
        if document.name != "README.md":
            continue

        path = target.partition("#")[0]

        if path:
            linked.add(path)

    for document, target in self_links():
        if document.name == "README.md":
            linked.add(target[len(SELF):].partition("#")[0])

    pages = {f"docs/{path.name}" for path in (ROOT / "docs").glob("*.md")}

    assert readme.is_file()
    assert pages <= linked


def test_every_relative_link_resolves():
    broken = []

    for document, target in relative_links():
        path, _, anchor = target.partition("#")
        destination = document.parent / path if path else document

        if not destination.is_file():
            broken.append(f"{document.name}: {target}")
            continue

        if anchor and anchor not in anchors(destination):
            broken.append(f"{document.name}: {target} (missing anchor)")

    assert broken == []


def test_relative_links_match_the_case_on_disk():
    wrong = []

    for document, target in relative_links():
        path = target.partition("#")[0]

        if not path:
            continue

        destination = document.parent / path

        if not destination.is_file():
            continue

        siblings = {entry.name for entry in destination.parent.iterdir()}

        if destination.name not in siblings:
            wrong.append(f"{document.name}: {target}")

    assert wrong == []


def test_no_document_links_to_a_deleted_decisions_log():
    offenders = [document.name for document in documents()
                 if "DECISIONES" in document.read_text(encoding="utf-8")]

    assert offenders == []


def test_no_document_embeds_a_local_filesystem_path():
    pattern = re.compile(r"(?:[A-Za-z]:\\|file:///|/home/|/Users/)")
    offenders = []

    for document in documents():
        for number, line in enumerate(
                document.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{document.name}:{number}")

    assert offenders == []


def test_the_readme_uses_only_absolute_image_sources():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", readme)
    relative = [source for source in images
                if not source.startswith(("http://", "https://"))]

    assert relative == []
