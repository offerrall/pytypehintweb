# Testing

Two suites, one per side of the contract:

- `tests/python/` — plan generation (`plan_of`) and the round trip back to
  `schema.build()`.
- `tests/js/` — normalization, validation and form construction in the browser
  layer.

Neither touches the network, sleeps, writes into the repository or depends on
execution order. The test files document themselves; this page lists only how
to run them and the cross-cutting guarantees they exist to protect.

## Running

```bash
pytest tests/python                       # Python
node --test "tests/js/*.test.mjs"         # JavaScript (Node 20+, installs nothing)
pytest tests/python && node --test "tests/js/*.test.mjs"   # both
```

The Python suite needs the test extra (`pip install -e ".[test]"`). The Python
tests that shell out to Node — the round trip and the producer-validator
invariant — skip themselves when `node` is not on the path.

### Real-browser smoke

The two suites above run against a lightweight fake DOM, which cannot reproduce a
few behaviours only a real browser has — most importantly that a native control
loses focus when it is disabled. `tests/browser/smoke.html` covers those against
the actual shipped modules, with no dependency and no build step. Run it headless
and read the verdict from the DOM:

```bash
chrome --headless=new --disable-gpu --allow-file-access-from-files \
  --virtual-time-budget=8000 --dump-dom "$SMOKE_URL" | grep '<div id="result"'
```

where `$SMOKE_URL` is an absolute `file://` URL to `tests/browser/smoke.html`.
Expect `SMOKE: PASS (N checks)`. It is a manual pre-release check, not part of the
Node suite; drag-and-drop and byte uploads are out of its scope (they need a live
host channel and are exercised by the bundled demo).

## Guarantees

The suites are written around the failures that would otherwise be silent:

- every plan `plan_of()` emits passes `checkPlan()` and `compileForm()`, and the
  full round trip `plan_of` → JSON → `compileForm` → `read()` → `schema.build()`
  holds;
- a missing property fails with `<path>: is required`, never a default; a
  mistyped or unknown property fails instead of being ignored;
- normalization never mutates or aliases its input, and returns fresh objects;
- every documented JSON example validates as written, with no default filling,
  and the `plan.md` default tables match `static/defaults.js`;
- a string from a plan reaches the page as text, never as markup — hostile
  payloads are mounted everywhere and none runs, and the fake DOM
  (`tests/js/dom.mjs`) throws on every HTML-parsing sink so the check cannot go
  decorative;
- a plan `default` is constraint-valid against its node, not merely
  shape-compatible, while a live user value may stay representable yet invalid;
- `enabled: false` on a non-optional field is rejected before any widget exists,
  at the root and inside nested objects;
- a slider never represents emptiness — `setValue(null)` throws — and, by the
  general rule that an integer default must be a safe integer, a `null` default
  on a non-optional slider field is rejected;
- a checkbox always represents a value — never empty, never in error;
  `setValue(null)` and a non-boolean throw, and a non-boolean `default` is
  rejected;
- an `int` typed into a float field becomes a built `float`: the star round trip
  `"3"` → `read()` → JSON → `decode()` → `build()` yields `3.0` with type `float`;
- a non-finite float — a magnitude that overflows to `Infinity` — reads as
  `null` and is never transported, the float analogue of the unsafe integer;
- `decode()` prepares without validating: it coerces `int → float` only where a
  `Float` shape is the single reading, never mutates its input, and leaves an
  invalid value untouched for the core to reject;
- a `float` slider is refused at plan generation, because `min + k*step` has no
  exact float arithmetic;
- an ISO string picked in the browser becomes a built `date`/`time`: the star
  round trip `read()` → JSON → `decode()` → `build()` yields the exact Python
  object, and a date exclusive bound is emitted converted by ±1 day while a time
  bound keeps its flag;
- `decode()` never interprets a string by its content: it converts to `date`/
  `time` only where the shape (or an explicit `$type`) says so, so a `str` field
  or branch carrying `"2026-07-22"` stays a string;
- an enum member name picked in the browser becomes the exact built member: the
  star round trip `read()` → JSON → `decode()` → `build()` yields the member via
  `cls[name]` with type the enum class; an alias name resolves to its canonical
  member, an unknown name is left for the core, and two enums sharing a class
  name in a union are rejected by the core at compile time (the class name is the
  wrapper discriminator);
- only a local choice makes a new file reference (a UUID plus the file's
  extension) — one per file, `list[File]` minting an array through one `multiple`
  widget; a reference is filtered only by extension in the widget and the core,
  never checked for existence;
- `setValue(string)` plants an existing reference, shown on screen declared as the
  current file (not editable) and transported verbatim, so a `Struct` with an
  internal path round-trips through an edit form byte-identical when its file is
  untouched; a file node carries no plan default (`plan_of`/`checkPlan` reject one,
  path included), and a `str | file` union is inconstructible because both branches
  carry the option id `"str"`;
- date and time bounds compare lexicographically over the canonical ISO form,
  and the core's rejection of the string-group wrapper is pinned, so `decode()`
  is proven to be the only thing that can unwrap it;
- `read()` stays callable and honest while the form is incomplete;
- string lengths count code points, so `"😀"` is one character; a pattern the
  validator accepts constructs as a JavaScript Unicode `RegExp`, and one the two
  engines would read differently is rejected in Python;
- a placeholder is allowed on an ordinary `str`/`int` input and rejected on a
  closed choice, which opens on its first option;
- the `Color`/`Email` aliases are pure `Annotated[str, Pattern(...)]`: a `Color`
  plan is asserted byte-equal to the hand-written str node, so the contract does
  not distinguish it; the colour picker is presentation only — mounted by string
  equality with the published `COLOR_PATTERN`, whose JS mirror is pinned equal to
  the Python constant — while the text field stays the source of truth;
- every control keeps an accessible name, and generated ids stay unique across
  nested, repeated and separately compiled forms;
- every browser file the runtime imports ships inside the package.

The bundled demo is a showcase and a debugging tool; it asserts nothing.

## Continuous integration and release

`.github/workflows/ci.yml` runs on every push to `main` and on pull requests, in
three jobs: **Python** (a `3.11`/`3.12`/`3.13` matrix running `mypy` and the
`pytest` suite, packaging/assets test included), **JavaScript** (the `node --test`
suite — widgets, size budget and plan-doc examples — plus the headless-Chrome
browser smoke), and **Packaging** (`uv build` then `uvx twine check`). Installing
the project resolves its one runtime dependency, `pytypehint >= 0.0.6`, from PyPI.

Releases are published from `.github/workflows/publish.yml`, which triggers only
when a GitHub Release is *published*. It re-runs every check, builds the wheel and
sdist, and uploads them to PyPI through **Trusted Publishing** (OIDC) — no API
token or password. The workflow targets the `pypi` GitHub environment, which must
be registered as the Trusted Publisher on PyPI.
