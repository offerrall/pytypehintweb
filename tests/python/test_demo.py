import json
from pathlib import Path

import pytest

from pytypehintweb.demo import app as demo

ROOT = Path(__file__).resolve().parents[2]


def test_duplicate_form_ids_raise_a_value_error():
    with pytest.raises(ValueError, match="duplicate demo form id"):
        demo._unique([("same", "a"), ("same", "b")])


def test_source_blocks_are_separated_by_a_blank_line():
    with_extra = next(form for section in demo.PLANS
                      for form in section["forms"]
                      if "\n\n" in form["source"])

    assert "\n\n" in with_extra["source"]
    assert not with_extra["source"].startswith("\n")


def test_the_demo_serves_javascript_with_a_modern_media_type():
    assert demo.MEDIA_TYPES[".js"] == "text/javascript"
    assert demo.MEDIA_TYPES[".css"] == "text/css"
    assert demo.MEDIA_TYPES[".svg"] == "image/svg+xml"


def test_the_demo_serves_the_stylesheet_icons():
    # widgets.css addresses its icons relative to itself, so the static route
    # has to reach into the subdirectory or every select loses its arrow.
    for name in ["widgets.css", "form.js", "icons/trash.svg",
                 "icons/select-arrow-light.svg", "icons/select-arrow-dark.svg"]:
        response = demo.static(name)

        assert response.status_code == 200, name
        assert response.body != b"", name


@pytest.mark.parametrize("name", [
    "../pyproject.toml",
    "../../pyproject.toml",
    "icons/../../pyproject.toml",
    "icons/nope.svg",
    "icons",
    "",
])
def test_the_static_route_serves_nothing_outside_the_package(name):
    # Accepting a slash in the path must not have opened a way out of STATIC.
    assert demo.static(name).status_code == 404


def test_the_demo_uses_a_lifespan_instead_of_deprecated_startup_events():
    assert demo.app.router.on_startup == []
    assert demo.app.router.lifespan_context is not None


def test_startup_hooks_run_through_the_lifespan():
    import asyncio

    fired = []

    def hook():
        fired.append("started")

    demo.ON_STARTUP.append(hook)

    async def run():
        async with demo.lifespan(demo.app):
            pass

    try:
        asyncio.run(run())
    finally:
        demo.ON_STARTUP.remove(hook)

    assert fired == ["started"]


def test_the_state_panel_shows_both_local_values_and_the_transport_object():
    assert "value:\\n" in demo.HTML
    assert "read:\\n" in demo.HTML
    assert "form.read()" in demo.HTML


def test_the_plan_panel_is_labelled_plan():
    assert 'summary.textContent = "Plan"' in demo.HTML
    assert "Compact plan" not in demo.HTML


def test_the_document_is_a_complete_html_page():
    text = demo.HTML.strip()

    assert text.startswith("<!doctype html>")
    assert text.endswith("</html>")
    assert 'lang="en"' in text
    assert "viewport" in text


def test_the_demo_chrome_follows_the_light_and_dark_themes():
    text = demo.HTML

    assert "@media (prefers-color-scheme: dark)" in text
    assert '[data-pth-theme="dark"]' in text
    assert "--demo-bg" in text
    assert "background: var(--demo-bg)" in text


def test_the_demo_has_a_theme_toggle_on_the_public_attribute():
    text = demo.HTML

    assert 'id="theme-toggle"' in text
    assert "el.dataset.pthTheme = current" in text
    assert "prefers-color-scheme: dark" in text

    # The toggle is the demo's own chrome. Nothing about the theme may travel
    # through the plan or the runtime, and the demo must not persist it either.
    assert "localStorage" not in text
    assert '[data-theme=' not in text


def test_the_demo_mounts_its_widgets_inside_a_theme_root():
    assert 'left.className = "pth-root"' in demo.HTML


# --- the file seam: reference in, stored path out ---------------------------

def test_the_demo_resolves_a_reference_to_where_it_stored_the_bytes():
    # The widget mints an opaque reference and nothing in the library or the core
    # knows what it stands for. decode()'s file_resolver is the only seam where a
    # host can say, and this demo says "a file in my uploads directory".
    assert demo.stored_path("abc-1234.pdf") == str(demo.UPLOADS / "abc-1234.pdf")

    # A reference is client-supplied, so the path segment is all that is trusted.
    assert demo.stored_path("albums/summer/beach.jpg") == str(
        demo.UPLOADS / "beach.jpg")


def _post_build(form_id, data):
    import asyncio

    response = asyncio.run(demo.build(form_id, data))

    return json.loads(response.body)


def test_the_build_endpoint_resolves_a_file_reference_end_to_end():
    # The whole seam, through the real endpoint: a prefilled record names a file
    # the host already holds and the resolver turns it into the path this host
    # keeps its bytes at. The demo no longer seeds those files, because nothing
    # downstream opens them — whether the bytes are really there is a question
    # only a host that cares has to answer, in its own resolver.
    body = _post_build("file-edit",
                       {"name": "Ada Lovelace",
                        "avatar": "avatars/ada-lovelace.jpg"})

    assert body["ok"] is True
    assert "Ada Lovelace" in body["built"]
    assert "ada-lovelace.jpg" in body["built"]
    # The reference did not travel raw: it came out mapped into the demo's own
    # storage, which is the resolver's whole job. (repr() escapes a Windows
    # separator, so the directory is matched by name rather than by full path.)
    assert demo.UPLOADS.name in body["built"]


def test_the_build_endpoint_reports_a_reference_of_the_wrong_kind():
    # What the core still refuses is the extension, read off the text, and the
    # demo turns that refusal into a readable envelope like any other.
    body = _post_build("file-edit",
                       {"name": "Ada", "avatar": "never-uploaded-1234.txt"})

    assert body["ok"] is False
    assert "not an accepted file type" in body["error"]


EXPECTED_MESSAGES = {
    "demo envelope": "TypeError: bad",
    "fastapi detail string": "Unknown form",
}


def test_the_frontend_explains_every_error_envelope(node, tmp_path):
    source = tmp_path / "app-source.txt"
    source.write_text(demo.HTML, encoding="utf-8")

    result = node("demo-errors.mjs", str(source),
                  str(tmp_path / "helpers.mjs"))

    assert result["found"], "the error helpers were not found in the demo HTML"

    messages = {row["name"]: row["message"] for row in result["results"]}

    for name, expected in EXPECTED_MESSAGES.items():
        assert messages[name] == expected

    assert "field required" in messages["fastapi detail list"]
    assert "boom" in messages["non json"]
    assert messages["non json"].startswith("HTTP 500")
    assert messages["empty body"] == "HTTP 502 Bad Gateway"

    assert all(message.strip() != "" for message in messages.values())


def test_every_demo_plan_is_valid_and_mounts(node, tmp_path):
    plans = {form["id"]: form["plan"]
             for section in demo.PLANS for form in section["forms"]}

    path = tmp_path / "plans.json"
    path.write_text(json.dumps(plans), encoding="utf-8")

    result = node("check-plans.mjs", str(path))

    assert result["failed"] == []
    assert result["mounted"] == len(plans)


@pytest.mark.parametrize("host, port, expected", [
    ("127.0.0.1", 8000, "http://127.0.0.1:8000"),
    ("localhost", 8000, "http://localhost:8000"),
    ("0.0.0.0", 8000, "http://127.0.0.1:8000"),
    ("::1", 8000, "http://[::1]:8000"),
    ("::", 8000, "http://[::1]:8000"),
    ("::0", 8000, "http://[::1]:8000"),
    ("2001:db8::1", 8000, "http://[2001:db8::1]:8000"),
    ("[::1]", 8000, "http://[::1]:8000"),
])
def test_the_demo_url_brackets_ipv6_literals(host, port, expected):
    from pytypehintweb.demo import __main__ as cli

    assert cli._url(host, port) == expected


EXPECTED_PREFILL = {
    "empty": [],
    "whitespace": [],
    "integer": ["12", 12],
    "negative integer": ["-5", -5],
    "padded integer": [" 7 ", 7],
    "malformed": ["abc"],
    "float-like": ["1.5"],
}


def test_the_demo_prefill_skips_empty_integer_values(node, tmp_path):
    source = tmp_path / "app-source.txt"
    source.write_text(demo.HTML, encoding="utf-8")

    result = node("demo-prefill.mjs", str(source), str(tmp_path / "prefill.mjs"))

    assert result["found"], "the prefill helper was not found in the demo HTML"

    candidates = {row["name"]: row["candidates"] for row in result["results"]}

    assert candidates == EXPECTED_PREFILL


def test_the_build_endpoint_wraps_any_build_exception():
    import asyncio

    from pytypehint import signature_of

    def empty() -> None:
        pass

    def boom(_data):
        raise RuntimeError("kaboom")

    # The endpoint runs decode() before build(), so the schema must be real; only
    # build is shadowed, leaving the endpoint's exception wrapping as what the
    # test exercises. decode() over a param-less signature returns {} untouched.
    schema = signature_of(empty)
    object.__setattr__(schema, "build", boom)
    demo.SCHEMAS["__boom__"] = schema

    try:
        response = asyncio.run(demo.build("__boom__", {}))
    finally:
        del demo.SCHEMAS["__boom__"]

    payload = json.loads(response.body)

    assert payload["ok"] is False
    assert "RuntimeError" in payload["error"]
    assert "kaboom" in payload["error"]
