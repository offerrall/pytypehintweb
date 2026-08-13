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
loses focus when it is disabled, that a range input whose stride misses the
maximum really does reach it, and that a `File` has a real `.size` a size bound
can be weighed against (a `DataTransfer` is the only way to build one, and the
only way to hand it to a read-only `FileList`).
`tests/browser/smoke.html` covers those against
the actual shipped modules, with no dependency and no build step. Run it headless
and read the verdict from the DOM:

```bash
chrome --headless=new --disable-gpu --allow-file-access-from-files \
  --virtual-time-budget=8000 --dump-dom "$SMOKE_URL" | grep '<div id="result"'
```

where `$SMOKE_URL` is an absolute `file://` URL to `tests/browser/smoke.html`.
Expect `SMOKE: PASS (N checks)`. It runs in CI alongside the Node suite;
drag-and-drop and byte uploads are out of its scope (they need a live host
channel and are exercised by the bundled demo).

**Read the verdict from `#result`, never from a bare text match.** Both browser
pages spell their own PASS string in a comment, so `grep 'SMOKE: PASS'` matches
whatever the page did — including not running at all. Anchor on
`id="result">SMOKE: PASS`, which is what CI does.

Both pages import their modules **statically**. A top-level `await import(...)`
settles after the load event, so `--dump-dom` raced it and captured `PENDING`
about half the time; the fix is the import form, not a larger time budget, which
does not help because the race is not about how much time is granted.

### Theme cascade

`tests/browser/theme.html` covers the other thing only a browser has: the CSS
cascade. The Python suite reads `widgets.css` as text and can prove the theme
blocks exist, agree on their tokens and clear their contrast thresholds, but not
that specificity, inheritance and proximity land where the contract says. The
page is static — no modules, no library JavaScript — and reads computed styles:
automatic mode, an override applied on the root and on an ancestor, the nearest
override winning, two roots disagreeing on one page, and the host document left
untouched. Run it once per system preference, since automatic mode has two
answers:

```bash
chrome --headless=new --disable-gpu --allow-file-access-from-files \
  --virtual-time-budget=8000 --blink-settings=preferredColorScheme=0 \
  --dump-dom "$THEME_URL" | grep 'id="result"'
```

`preferredColorScheme=0` is dark and `=1` is light. Expect
`THEME: PASS (N checks)` from both. CI runs it after the smoke page, failing the
job and dumping the page when either preference does not reach PASS.

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
- `decode()` prepares without validating: an `int` is restored to a `float` only
  where a `Float` shape is the single reading and only where a float equals it
  exactly (`2**53 + 1` travels as it came), the input is never mutated and the
  result shares no container with it, and an invalid value is left untouched for
  the core to reject. That `decode()` never raises on a value of its own accord
  is pinned on its own — an integer of four hundred digits in a float field comes
  back whole — and so is the delegation behind all of it: the helpers the old
  walker was made of are asserted absent from the module, and `decode.py` is
  asserted to name neither `fromisoformat` nor any shape whose portable spelling
  the core restores;
- a `float` slider is refused at plan generation, because `min + k*step` has no
  exact float arithmetic;
- an ISO string picked in the browser becomes a built `date`/`time`: the star
  round trip `read()` → JSON → `decode()` → `build()` yields the exact Python
  object, and a date exclusive bound is emitted converted by ±1 day while a time
  bound keeps its flag;
- `decode()` never interprets a string by its content: it reads a `date`/`time`
  only where the shape (or an explicit `$type`) says so, and only from the
  canonical spelling, so a `str` field or branch carrying `"2026-07-22"` stays a
  string while `"20260722"` and `"2026-W30-3"` stay strings in a `date` field and
  `"2020"` stays one in a `time` field;
- an enum member name picked in the browser becomes the exact built member: the
  star round trip `read()` → JSON → `decode()` → `build()` yields the member with
  type the enum class; an alias name resolves to its canonical member (the lookup
  reads through `__members__`), an unknown name is left for the core, and two
  enums sharing a class name in a union are rejected by the core at compile time
  (the class name is the wrapper discriminator);
- only a local choice makes a new file reference (the file's name slugged to bare
  ASCII, a UUID and the file's extension, the UUID carrying the uniqueness on its
  own) — one per file, `list[File]` minting an array through one `multiple`
  widget; a reference is filtered only by extension in the widget and the core,
  never checked for existence;
- `setValue(string)` plants an existing reference, shown on screen declared as the
  current file (not editable) and transported verbatim, so a `Struct` with an
  internal path round-trips through an edit form byte-identical when its file is
  untouched; and a `str | file` union is inconstructible because both branches
  carry the option id `"str"`;
- a file **default** is that same reference declared in the plan, and it reaches
  the widget *through* `setValue()`, so the two cannot drift: compiling with a
  default is asserted to produce the same observable state as compiling without
  one and calling `setValue()` afterwards — at the widget level and again across
  the real Python → plan → browser boundary. A default is never a local
  selection: `file()`/`files()` stay empty and `uploads()` reports nothing, while
  a user's pick does appear in both. `checkPlan()` polices the shape — `str` for
  a single node, `list[str]` for a multiple one, non-empty, extension-filtered,
  within `minFiles`/`maxFiles` — and the widget owns the semantics. Existence is
  neither checked nor claimed anywhere: what a Python schema default (a prefill
  included) still faces is the extension, checked by `FileHint` on the text, so a
  wrong extension or one bad element of a `list[File]` fails at the core with no
  plan produced, while a reference naming no local file compiles and renders like
  any other. Both sides of that line are pinned — the refusal to the core's own
  message, the acceptance to a plan that reaches the widget — so a regression
  that moved a filesystem check into either half would show. What the byte bounds
  do reach is the widget, and a star test drives a plan_of() plan through the
  real modules to see a local pick refused for its size and a planted reference
  accepted for having none;
- which file compositions compile is a test, not a sentence: `File`,
  `File | None`, `list[File]`, `list[File | None]`, `list[File | int]`,
  `list[list[File]]`, a dataclass holding a file, a dataclass holding a
  `list[File]` and a list of such dataclasses all produce a node, and a guard
  asserts the blanket "does this contain a file" predicate stays deleted. The
  browser side drives each nested shape through the public API — rows added and
  removed, branches switched, a real pick two levels down — and `decode()` is
  pinned to call the resolver once per reference, in order, at any depth;
- date and time bounds compare lexicographically over the canonical ISO form,
  and the core's rejection of the string-group wrapper is pinned, so `decode()`
  is proven to be the only thing that can unwrap it;
- a wrapper is unwrapped only when its payload read as the branch it names: a
  `{"$type": "date"}` over a string that is not a date, or over a spelling that
  is canonical but not a real calendar day, survives to `build()` instead of
  settling as the `str` beside it — which is also what keeps a reference from
  reaching a file field behind the resolver's back — while a malformed wrapper
  (an extra key, a missing `$value`, a `$type` naming no branch, a wrapper on a
  path that is not a union) travels whole in every position;
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
- the stylesheet stays inside its own root and its themes stay complete: every
  selector starts at `.pth-root` or is one of the two `data-pth-theme` roots,
  the automatic block skips any overridden root and the manual blocks follow it
  without `!important`, the four theme blocks assign the same token set, every
  palette value has a light/dark pair no rule reads directly, and no colour is
  written outside the palette. The palettes are then measured: both clear 4.5:1
  for text and 3:1 for interface components across every relation that appears
  on screen (`tests/python/test_stylesheet_theme.py`, with the parser and the
  WCAG helper in `tests/python/stylesheet.py`). Thresholds are the contract, not
  the hex values, so the palette can be retuned without editing a test;
- every icon is a file, never an embedding: the production sources carry no
  `data:image/svg`, no inline `<svg>` and no base64 (comments excepted, so the
  rule can be written down where it applies), every `url()` in the stylesheet is
  relative and resolves to a shipped file, every shipped icon is referenced, and
  each one is valid UTF-8 with a single `<svg>` root, a `viewBox`, sane
  dimensions and no script, no `<foreignObject>`, no remote link and no editor
  metadata. `static/icons/*.svg` is asserted to be declared as package data,
  because nothing under `src/` ships just for being there;
- the documentation's anchors follow GitHub's rule, pinned by a table of cases
  rather than by the documents that happen to exist
  (`tests/python/test_markdown_anchors.py`, with the helper in
  `tests/python/markdown_anchors.py`): punctuation is dropped without leaving a
  separator, `_` and non-ASCII letters survive, repeats take `-1`/`-2`, and the
  heading parser skips fenced code blocks so a shell comment never becomes an
  anchor. Every internal `#fragment` in the documentation is then resolved
  against those anchors;
- every browser file the runtime imports ships inside the package.

The bundled demo is a showcase and a debugging tool; it asserts nothing.

## Continuous integration and release

`.github/workflows/ci.yml` runs on every push to `main` and on pull requests, in
three jobs: **Python** (a `3.11`/`3.12`/`3.13` matrix running `mypy` and the
`pytest` suite, packaging/assets test included), **JavaScript** (the `node --test`
suite — widgets, size budget and plan-doc examples — plus the headless-Chrome
browser smoke and the theme-cascade page, the latter once per system
preference), and **Packaging** (`uv build` then `uvx twine check`). Installing
the project resolves its one runtime dependency, `pytypehint >= 1.0.0`, from PyPI.

Releases are published from `.github/workflows/publish.yml`, which triggers only
when a GitHub Release is *published*. It re-runs every check, builds the wheel and
sdist, and uploads them to PyPI through **Trusted Publishing** (OIDC) — no API
token or password. The workflow targets the `pypi` GitHub environment, which must
be registered as the Trusted Publisher on PyPI.
