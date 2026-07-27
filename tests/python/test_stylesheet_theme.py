"""The theme contract of `widgets.css`.

Three things are checked here and nothing else: that the sheet stays inside its
own root, that the light and dark palettes are structurally complete, and that
the colours they resolve to clear the WCAG thresholds. The concrete hex values
are not a contract — every colour assertion is a relation between two tokens
against a threshold, so the palette can be retuned without touching a test.
"""

import re

from stylesheet import (
    AUTO_SELECTOR,
    CSS,
    DARK_MEDIA,
    DARK_ROOT,
    HEX,
    LIGHT_ROOT,
    ROOT_CLASS,
    asset,
    contrast,
    is_asset,
    palette,
    rules,
    theme_blocks,
)

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce)"

PALETTE_SELECTORS = [ROOT_CLASS, LIGHT_ROOT, DARK_ROOT]
THEME_SELECTORS = ([AUTO_SELECTOR], [LIGHT_ROOT], [DARK_ROOT])

TEXT_MINIMUM = 4.5
UI_MINIMUM = 3.0


def _properties(rule):
    """The property names a rule declares, custom ones included."""
    names = []

    for chunk in rule.body.split(";"):
        if ":" not in chunk:
            continue

        name = chunk.split(":", 1)[0].strip()

        if name:
            names.append(name)

    return names


def _is_theme_rule(rule):
    return rule.selectors in THEME_SELECTORS


def _is_palette_rule(rule):
    return rule.selectors == PALETTE_SELECTORS


def _paints(rule):
    """True for a rule that styles something, not one that only sets tokens."""
    return any(not name.startswith("--") for name in _properties(rule))


# ===== Namespace =====


def test_every_selector_stays_under_the_library_root():
    offenders = [
        selector
        for rule in rules()
        for selector in rule.selectors
        if not (selector == ROOT_CLASS
                or selector.startswith(f"{ROOT_CLASS} ")
                or selector.startswith(f"{ROOT_CLASS}:")
                or selector in (LIGHT_ROOT, DARK_ROOT))
    ]

    assert offenders == [], (
        "every rule must start at .pth-root or be one of the two namespaced "
        "theme roots; anything else could reach host elements")


def test_no_selector_starts_with_a_bare_element():
    bare = re.compile(r"^(html|body|input|button|label|select|textarea|form|"
                      r"div|span|\*|:root)\b")
    offenders = [selector for rule in rules() for selector in rule.selectors
                 if bare.match(selector)]

    assert offenders == [], "a bare element selector would restyle the host page"


def test_the_theme_root_class_exists():
    assert ROOT_CLASS in [selector for rule in rules()
                          for selector in rule.selectors]


def test_the_root_paints_the_surface_its_palette_is_calibrated_against():
    root = [rule for rule in rules() if rule.selectors == [ROOT_CLASS]]

    assert len(root) == 1
    assert "--pth-surface" in root[0].references, (
        "a forced theme has to stand on its own background, or a dark root on "
        "a light page would show its own text unreadably")


def test_the_sheet_carries_no_legacy_theme_contract():
    for legacy in ('[data-theme="light"]', '[data-theme="dark"]',
                   ".light-mode", ".dark-mode"):
        assert legacy not in CSS, f"{legacy} was dropped with the pre-1.0 rename"


def test_the_sheet_keeps_explicit_theme_blocks():
    assert "light-dark(" not in CSS, (
        "explicit blocks keep the theme resolvable per subtree without a global "
        "color-scheme")


# ===== Theme structure =====


def test_the_automatic_mode_is_pure_css():
    blocks = theme_blocks()

    assert "auto-light" in blocks
    assert "auto-dark" in blocks
    assert blocks["auto-dark"].in_dark_media
    assert DARK_MEDIA in CSS


def test_the_automatic_block_only_reaches_roots_without_an_override():
    inside = [rule for rule in rules() if rule.in_dark_media]

    assert inside != []
    assert all(rule.selectors == [AUTO_SELECTOR] for rule in inside), (
        "the automatic block must skip a root that carries data-pth-theme "
        "itself or inherits one from an ancestor")


def test_both_manual_overrides_exist():
    blocks = theme_blocks()

    assert "manual-light" in blocks
    assert "manual-dark" in blocks


def test_the_manual_blocks_come_after_the_automatic_one():
    blocks = theme_blocks()

    automatic = max(blocks["auto-light"].order, blocks["auto-dark"].order)
    manual = min(blocks["manual-light"].order, blocks["manual-dark"].order)

    assert automatic < manual, (
        "a manual override wins by source order, not by !important")


def test_no_theme_block_uses_important():
    offenders = [rule.prelude for rule in rules()
                 if _is_theme_rule(rule) and "!important" in rule.body]

    assert offenders == []


def test_the_four_theme_blocks_assign_the_same_active_tokens():
    assigned = {name: frozenset(rule.declarations)
                for name, rule in theme_blocks().items()}

    assert len(assigned) == 4
    assert len(set(assigned.values())) == 1, (
        f"the theme blocks disagree on their token set: {assigned}")


def test_every_active_token_reads_the_pair_of_its_own_theme():
    offenders = []

    for name, rule in theme_blocks().items():
        theme = name.split("-")[1]

        for token, value in rule.declarations.items():
            if value.strip() != f"var({token}-{theme})":
                offenders.append(f"{name}: {token}: {value}")

    assert offenders == [], (
        "a theme block must point every active token at its own palette pair")


# ===== Palette =====


def test_every_palette_value_comes_as_a_light_dark_pair():
    incomplete = {stem: sorted(pair) for stem, pair in palette().items()
                  if set(pair) != {"light", "dark"}}

    assert incomplete == {}


def test_the_light_and_dark_palettes_differ_everywhere():
    identical = [stem for stem, pair in palette().items()
                 if pair["light"] == pair["dark"]]

    assert identical == []


def test_every_active_token_has_a_palette_pair():
    stems = set(palette())
    missing = [token for token in theme_blocks()["auto-light"].declarations
               if token not in stems]

    assert missing == []


def test_widgets_read_active_tokens_only():
    offenders = []

    for rule in rules():
        if _is_theme_rule(rule) or _is_palette_rule(rule):
            continue

        for token in rule.references:
            if token.endswith(("-light", "-dark")):
                offenders.append(f"{rule.prelude}: {token}")

    assert offenders == [], (
        "outside the theme blocks a rule must read the active token, never one "
        "half of a palette pair")


def test_every_token_a_widget_reads_is_defined():
    themed = set(theme_blocks()["auto-light"].declarations)
    static = {token
              for rule in rules() if rule.selectors == [ROOT_CLASS]
              for token in rule.declarations}

    missing = sorted({token
                      for rule in rules() if not _is_theme_rule(rule)
                      for token in rule.references
                      if token not in themed and token not in static})

    assert missing == []


def test_the_sheet_defines_no_token_it_never_reads():
    # A token nothing consumes is download weight and a false promise: a host
    # that overrides it sees nothing change. The palette pairs are exempt because
    # the theme blocks read them, which the reference scan already counts.
    defined = {token for rule in rules() for token in rule.declarations}
    used = {token for rule in rules() for token in rule.references}

    assert sorted(defined - used) == []


def test_hex_colours_live_only_in_the_palette():
    offenders = [rule.prelude for rule in rules()
                 if not _is_palette_rule(rule) and HEX.search(rule.body)]

    assert offenders == [], (
        "a colour written into a rule cannot follow the theme; give it a "
        "light/dark pair instead")


def test_button_text_is_a_token_of_its_own():
    assert "--pth-submit-text" in palette()

    readers = [rule.prelude for rule in rules()
               if "--pth-submit-text" in rule.references]

    for widget in (".pth-list-add", ".pth-file-add", ".pth-number-btn:active",
                   "::file-selector-button:hover",
                   ".pth-file-current-replace:hover"):
        assert any(widget in prelude for prelude in readers), (
            f"{widget} paints text over a themed background and must read "
            "--pth-submit-text")


def test_error_text_is_a_token_of_its_own():
    assert "--pth-error-color" in palette()

    readers = [rule.prelude for rule in rules()
               if "--pth-error-color" in rule.references]

    assert any("-message" in prelude for prelude in readers)


# ===== Native controls =====


def test_color_scheme_reaches_the_libraries_own_controls_only():
    carriers = [rule for rule in rules() if "color-scheme" in _properties(rule)]

    assert carriers != []

    for rule in carriers:
        for selector in rule.selectors:
            assert selector.startswith(f"{ROOT_CLASS} ."), (
                f"{selector} would hand a color-scheme to something that is "
                "not a library control")

        assert "var(--pth-color-scheme)" in rule.body


def test_the_sheet_never_writes_a_global_color_scheme():
    for owner in (":root", "html", "body"):
        assert f"{owner} {{" not in CSS
        assert f"{owner}{{" not in CSS


# ===== Motion =====


def test_reduced_motion_is_kept_and_stays_out_of_the_theme():
    slowed = [rule for rule in rules() if REDUCED_MOTION in rule.at_rules]

    assert slowed != []

    for rule in slowed:
        assert DARK_MEDIA not in rule.at_rules
        assert set(_properties(rule)) <= {"transition", "transform"}


def test_no_transition_animates_everything():
    assert not re.search(r"transition:\s*all\b", CSS)


# ===== Contrast =====

RELATIONS = [
    ("--pth-input-text", "--pth-input-background", TEXT_MINIMUM),
    ("--pth-label-color", "--pth-surface", TEXT_MINIMUM),
    ("--pth-label-color", "--pth-input-background", TEXT_MINIMUM),
    ("--pth-label-color", "--pth-neutral-hover", TEXT_MINIMUM),
    ("--pth-label-color", "--pth-nested-background", TEXT_MINIMUM),
    ("--pth-description-color", "--pth-surface", TEXT_MINIMUM),
    ("--pth-description-color", "--pth-input-background", TEXT_MINIMUM),
    ("--pth-description-color", "--pth-nested-background", TEXT_MINIMUM),
    ("--pth-error-color", "--pth-surface", TEXT_MINIMUM),
    ("--pth-error-color", "--pth-input-background", TEXT_MINIMUM),
    ("--pth-submit-text", "--pth-submit-background", TEXT_MINIMUM),
    ("--pth-submit-text", "--pth-submit-hover", TEXT_MINIMUM),
    ("--pth-submit-text", "--pth-input-focus", TEXT_MINIMUM),
    ("--pth-input-focus", "--pth-neutral-hover", TEXT_MINIMUM),
    ("--pth-input-border", "--pth-surface", UI_MINIMUM),
    ("--pth-input-border", "--pth-input-background", UI_MINIMUM),
    ("--pth-input-border", "--pth-nested-background", UI_MINIMUM),
    ("--pth-input-border", "--pth-neutral-hover", UI_MINIMUM),
    ("--pth-input-focus", "--pth-surface", UI_MINIMUM),
    ("--pth-input-focus", "--pth-input-background", UI_MINIMUM),
    ("--pth-input-focus", "--pth-nested-background", UI_MINIMUM),
    ("--pth-submit-background", "--pth-surface", UI_MINIMUM),
    ("--pth-submit-background", "--pth-nested-background", UI_MINIMUM),
    ("--pth-toggle-knob", "--pth-input-border", UI_MINIMUM),
    ("--pth-toggle-knob", "--pth-input-focus", UI_MINIMUM),
    ("--pth-error-color", "--pth-neutral-hover", UI_MINIMUM),
    ("--pth-select-arrow", "--pth-input-background", UI_MINIMUM),
]


def _colour(stem, theme):
    """The hex a palette entry resolves to.

    An icon token names a file rather than a colour, so the colour is read out
    of the asset itself. That is the point: the contrast thresholds then cover
    what the browser actually paints, not a copy of it kept in the stylesheet.
    """
    value = palette()[stem][theme]
    found = HEX.search(asset(value) if is_asset(value) else value)

    assert found is not None, f"{stem}-{theme} carries no colour"

    return found.group(0)


def test_the_contrast_helper_matches_the_wcag_extremes():
    assert round(contrast("#000000", "#ffffff"), 2) == 21.0
    assert round(contrast("#ffffff", "#ffffff"), 2) == 1.0
    assert round(contrast("#767676", "#ffffff"), 1) == 4.5


def test_both_palettes_clear_every_contrast_threshold():
    failures = []

    for theme in ("light", "dark"):
        for foreground, background, minimum in RELATIONS:
            ratio = contrast(_colour(foreground, theme),
                             _colour(background, theme))

            if ratio < minimum:
                failures.append(
                    f"{theme}: {foreground} on {background} "
                    f"is {ratio:.2f}:1, below {minimum}:1")

    assert failures == []
