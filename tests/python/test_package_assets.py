import re
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytypehintweb
from pytypehintweb import STATIC

ROOT = Path(__file__).resolve().parents[2]

RUNTIME_FILES = [
    "contract.js",
    "defaults.js",
    "fields.js",
    "form.js",
    "inputs.js",
    "iso.js",
    "normalize.js",
    "slider.js",
    "widgets.css",
]

# Every icon the interface draws. They are files rather than data URIs so the
# page needs no `img-src data:`, and the stylesheet addresses them relative to
# itself so they follow it under any static prefix.
ICONS = STATIC / "icons"

ICON_FILES = [
    "select-arrow-dark.svg",
    "select-arrow-light.svg",
    "trash.svg",
]


def test_static_points_at_a_directory_inside_the_installed_package():
    package = Path(pytypehintweb.__file__).parent

    assert STATIC.is_dir()
    assert STATIC == package / "static"


def test_every_runtime_file_ships_with_the_package():
    missing = [name for name in RUNTIME_FILES if not (STATIC / name).is_file()]

    assert missing == []


def test_the_static_directory_holds_nothing_unexpected():
    found = sorted(path.name for path in STATIC.iterdir() if path.is_file())

    assert found == sorted(RUNTIME_FILES)


def test_the_static_directory_holds_exactly_one_subdirectory():
    found = sorted(path.name for path in STATIC.iterdir() if path.is_dir())

    assert found == ["icons"]


# --- icons ------------------------------------------------------------------


def test_every_icon_ships_with_the_package():
    missing = [name for name in ICON_FILES if not (ICONS / name).is_file()]

    assert missing == []


def test_the_icons_directory_holds_nothing_unexpected():
    found = sorted(path.name for path in ICONS.iterdir())

    assert found == sorted(ICON_FILES)


def test_the_icons_are_reachable_through_the_published_static_path():
    # STATIC is the only path the library publishes; a host serves that
    # directory. The icons have to be reachable through it, not through some
    # separate accessor, or a host serving STATIC would miss them.
    for name in ICON_FILES:
        assert (STATIC / "icons" / name).read_text(encoding="utf-8").strip() != ""


def test_package_data_declares_the_icons():
    # Nothing under src/ is packaged just for being there: a non-Python file
    # ships only if a package-data pattern names it.
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["pytypehintweb"]

    assert "static/icons/*.svg" in patterns

    package = ROOT / "src" / "pytypehintweb"
    covered = {path.name for pattern in patterns
               for path in package.glob(pattern)}

    assert set(ICON_FILES) <= covered


MAX_ICON_BYTES = 4096


def test_every_icon_is_a_small_well_formed_svg():
    for name in ICON_FILES:
        path = ICONS / name
        raw = path.read_bytes()

        assert len(raw) <= MAX_ICON_BYTES, f"{name} is unexpectedly large"

        text = raw.decode("utf-8")                       # valid UTF-8 or raises
        root = ElementTree.fromstring(text)              # exactly one root

        assert root.tag == "{http://www.w3.org/2000/svg}svg", name
        assert root.get("viewBox") is not None, f"{name} declares no viewBox"

        box = root.get("viewBox").split()
        assert len(box) == 4, f"{name} has a malformed viewBox"
        assert all(0 < float(value) <= 1000 for value in box[2:]), (
            f"{name} has absurd viewBox dimensions")


FORBIDDEN_IN_ICONS = [
    "<script",
    "<foreignObject",
    "<image",
    "data:",
    "base64",
    "http://",
    "https://",
    "<metadata",
    "sodipodi",
    "inkscape",
]


def test_no_icon_carries_a_script_a_remote_link_or_editor_metadata():
    offenders = []

    for name in ICON_FILES:
        text = (ICONS / name).read_text(encoding="utf-8")

        # The xmlns declaration is the one http:// an SVG must carry: it is a
        # namespace identifier, never fetched.
        text = text.replace('xmlns="http://www.w3.org/2000/svg"', "")

        for token in FORBIDDEN_IN_ICONS:
            if token.lower() in text.lower():
                offenders.append(f"{name}: {token}")

    assert offenders == []


# Production sources must never grow an embedded icon again. Documentation,
# `.svg` files themselves and the fake DOM are out of scope on purpose: the
# first explains the syntax, the second *is* the asset, and the third is test
# infrastructure that never ships.
EMBEDDED_SVG = ["data:image/svg", "<svg", "base64"]


def _production_sources():
    package = ROOT / "src" / "pytypehintweb"

    for path in package.rglob("*"):
        if path.suffix in {".css", ".js", ".py", ".html"}:
            yield path


def _code(path):
    """A source file with its comments removed.

    A comment that spells out the rule — "no data: URI here" — is not a
    violation of it, so the scan looks at code only. Without this the rule
    could not be written down anywhere it applies.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    return "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("#"))


def test_no_production_source_embeds_an_svg():
    offenders = []

    for path in _production_sources():
        code = _code(path)

        for token in EMBEDDED_SVG:
            if token in code:
                offenders.append(f"{path.relative_to(ROOT)}: {token}")

    assert offenders == [], (
        "an icon must be a file under static/icons/, referenced from the "
        "stylesheet; embedding one brings back the need for img-src data:")


def test_the_stylesheet_needs_no_data_uri_at_all():
    css = _code(STATIC / "widgets.css")

    assert "data:" not in css
    assert "base64" not in css


def test_the_embedded_svg_scan_would_actually_catch_one():
    # The scan strips comments, so it has to be shown to still see code.
    fake = EMBEDDED_SVG[0]

    assert any(token in f"--pth-x: url('{fake},%3Csvg%3E');"
               for token in EMBEDDED_SVG)


def test_every_stylesheet_asset_reference_resolves_to_a_shipped_file():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")
    references = re.findall(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", css)

    assert references != []

    missing = []
    for reference in references:
        assert not reference.startswith(("/", "http:", "https:", "data:")), (
            f"{reference} must be relative to the stylesheet")

        if not (STATIC / reference).is_file():
            missing.append(reference)

    assert missing == []


def test_every_shipped_icon_is_actually_referenced():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")
    unused = [name for name in ICON_FILES if name not in css]

    assert unused == [], "an icon nobody references is dead weight"


# --- line endings -----------------------------------------------------------

# Everything under static/ is served byte for byte, so its bytes are part of
# what a user downloads. `.gitattributes` pins them to LF, and the extensions
# it pins have to keep up with the extensions that ship.
SHIPPED_SUFFIXES = {".js", ".css", ".svg"}


def test_gitattributes_pins_every_shipped_extension_to_lf():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    found = set(re.findall(r"^\*(\.\w+) text eol=lf$", attributes, re.MULTILINE))

    shipping = {path.suffix for path in STATIC.rglob("*") if path.is_file()}

    assert shipping <= SHIPPED_SUFFIXES, (
        f"a new kind of asset ships: {sorted(shipping - SHIPPED_SUFFIXES)}")
    assert shipping <= found, (
        "an extension that ships without an eol=lf rule gains a byte per line "
        f"on a Windows checkout: {sorted(shipping - found)}")


def test_no_shipped_asset_carries_crlf():
    offenders = [str(path.relative_to(STATIC))
                 for path in STATIC.rglob("*")
                 if path.is_file() and b"\r\n" in path.read_bytes()]

    assert offenders == []


def test_every_browser_module_import_resolves_inside_the_package():
    pattern = re.compile(r"""from\s+["'](\./[^"']+)["']""")
    missing = []

    for name in RUNTIME_FILES:
        if not name.endswith(".js"):
            continue

        source = (STATIC / name).read_text(encoding="utf-8")

        for target in pattern.findall(source):
            if not (STATIC / target[2:]).is_file():
                missing.append(f"{name} -> {target}")

    assert missing == []


UNSAFE_SINKS = [
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "createContextualFragment",
    "eval(",
    "new Function(",
    "srcdoc",
]


def test_no_browser_module_uses_an_html_parsing_sink():
    found = []

    for name in RUNTIME_FILES:
        if not name.endswith(".js"):
            continue

        source = (STATIC / name).read_text(encoding="utf-8")

        for number, line in enumerate(source.splitlines(), start=1):
            for sink in UNSAFE_SINKS:
                if sink in line:
                    found.append(f"{name}:{number}: {sink}")

    assert found == [], (
        "plan text must be inserted with textContent, setAttribute or value; "
        "these sinks parse HTML")


def test_the_demo_page_uses_no_html_parsing_sink():
    from pytypehintweb.demo import app

    found = [sink for sink in UNSAFE_SINKS if sink in app.HTML]

    assert found == []


def test_the_stylesheet_keeps_a_visible_focus_indicator():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    assert ":focus-visible" in css
    assert "outline: var(--pth-focus-width" in css


def test_the_stylesheet_never_removes_focus_outlines():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")
    offenders = [line for line in css.splitlines()
                 if "outline" in line and "none" in line]

    assert offenders == []


def test_the_stylesheet_carries_no_legacy_namespace():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    assert ".pti-" not in css
    assert "--pti-" not in css


# The theme contract itself — namespace, palette structure and contrast — lives
# in test_stylesheet_theme.py.
def test_the_stylesheet_styles_the_current_widget_classes():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    for selector in [".pth-root", ".pth-field", ".pth-label", ".pth-description",
                     ".pth-str", ".pth-int", ".pth-choice",
                     ".pth-choice-input", ".pth-mode-navigation",
                     ".pth-mode-previous", ".pth-mode-next", ".pth-mode-position",
                     ".pth-mode-content",
                     ".pth-group", ".pth-list", ".pth-list-item",
                     ".pth-list-add", ".pth-list-remove", ".pth-toggle",
                     ".pth-int-value"]:
        assert selector in css, f"missing styling for {selector}"


def test_the_list_remove_button_is_visually_light_by_default():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")
    block = css.split("\n.pth-root .pth-list-remove {", 1)[1].split("}", 1)[0]

    assert "background: transparent" in block
    assert "var(--pth-error-color)" not in block


def test_the_package_exposes_a_single_version():
    assert isinstance(pytypehintweb.__version__, str)
    assert pytypehintweb.__version__.count(".") >= 1
