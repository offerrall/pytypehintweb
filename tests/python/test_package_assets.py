import re
from pathlib import Path

import pytypehintweb
from pytypehintweb import STATIC

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


def _stylesheet_selectors():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

    selectors = []

    for block in css.split("{"):
        prelude = block.rsplit("}", 1)[-1].strip()

        if prelude:
            selectors.extend(part.strip() for part in prelude.split(",")
                             if part.strip())

    return selectors


# Theme roots set --pth-* variables; they never restyle host elements.
_THEME_ROOTS = {
    ":root", "[data-theme=\"light\"]", "[data-theme=\"dark\"]",
    ".light-mode", ".dark-mode",
}


def test_the_stylesheet_only_targets_the_pth_namespace():
    offenders = []

    for selector in _stylesheet_selectors():
        if selector.startswith("@"):
            continue
        if selector in _THEME_ROOTS:
            continue
        if selector.startswith(".pth-"):
            continue
        offenders.append(selector)

    assert offenders == [], (
        "every rule must target the pth-* namespace or a theme root; "
        "these would restyle host elements")


def test_the_stylesheet_carries_no_legacy_namespace():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    assert ".pti-" not in css
    assert "--pti-" not in css


def test_the_stylesheet_supports_automatic_and_manual_themes():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    assert "@media (prefers-color-scheme: dark)" in css
    assert '[data-theme="dark"]' in css
    assert '[data-theme="light"]' in css
    assert ".dark-mode" in css
    assert ".light-mode" in css


def test_the_stylesheet_respects_reduced_motion():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    assert "@media (prefers-reduced-motion: reduce)" in css


def test_the_stylesheet_styles_the_current_widget_classes():
    css = (STATIC / "widgets.css").read_text(encoding="utf-8")

    for selector in [".pth-field", ".pth-label", ".pth-description",
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
    block = css.split("\n.pth-list-remove {", 1)[1].split("}", 1)[0]

    assert "background: transparent" in block
    assert "var(--pth-error-color)" not in block


def test_the_package_exposes_a_single_version():
    assert isinstance(pytypehintweb.__version__, str)
    assert pytypehintweb.__version__.count(".") >= 1
