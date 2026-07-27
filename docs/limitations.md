# Current limitations

Everything a schema carries that the browser cannot represent faithfully
makes `plan_of()` raise `TypeError`. Nothing is degraded silently, so the
limitations below are visible at plan-generation time rather than at render
time.

## Scalar types

The current scalar slice is `str`, `int`, `float`, `date`, `time`, `bool` and
`enum` (any non-`Flag`, non-empty `Enum`).

Those compose through lists, nested lists, optional values, unions,
dataclasses and function signatures, which is enough to exercise the whole
pipeline: absence, values, constraints, parsing, transport and construction.

Any other scalar shape raises:

```text
... is not supported yet
```

### Float slider

`Slider` on a `Float` is rejected:

```text
Float.slider is not supported yet
```

A slider is a grid of `min + k*step` positions plus `max`, and float arithmetic
cannot walk that grid exactly: `min + k*step` accumulates rounding, so a legitimate default
could fall just off a position and be refused, or the control would have to
silently snap a value to the nearest step. The doctrine forbids both — no
rejecting a valid value, no silent correction — so a float slider is not offered
rather than offered wrongly. The `float` node carries no `slider` property at
all, so a hand-written plan that adds one is rejected as an unknown property,
with no special rule needed.

### `decode()` scope

The transport cannot express every type the core validates by exact type, so
[`decode()`](python.md#decode) prepares a JSON-parsed object before
`schema.build()`. **Today it prepares three things: `int → float` where the
shape is `Float`, an ISO string → `date`/`time` where the shape is `Date`/`Time`
(via `fromisoformat`), and a member name → enum member where the shape is
`EnumShape` (via `cls[name]`).** It converts only where the shape at the path (or
an explicit `$type` in a union) fixes the reading, never by inspecting a
value's content — a `str` that looks like a date, or matches a member name,
stays a `str`. It is the
reverse-pipeline counterpart of `plan_of()` and will grow as new types arrive;
everything it does not recognise passes through unchanged for `build()` to
judge.

## Regular expressions

Pattern support is a conservative portable subset: the core validates with
Python's `re` and the browser runs `RegExp`, and only constructs that behave
identically in both engines are accepted (a pattern that merely compiles in
JavaScript is not enough). The full list of rejected constructs and accepted
escapes lives in the [plan contract](plan.md#pattern-portability).

Most rejected shortcuts have a portable equivalent that spells out the intended
characters, which also documents the pattern:

| Common shortcut | Portable form                                   |
| --------------- | ----------------------------------------------- |
| `\d`            | `[0-9]`                                          |
| `\D`            | `[^0-9]`                                         |
| `\w`            | an explicit class for the domain, e.g. `[A-Za-z0-9_]` |
| `\s`            | an explicit class of the spaces you accept, e.g. `[ \t]` |
| `.`             | an explicit class of the allowed characters     |

Spelling the class out is not only portable, it is usually the more honest
pattern: `\d` matches digits in many scripts, while a form field almost always
means `[0-9]`. The library ships two convenience patterns — `COLOR_PATTERN` and
`EMAIL_PATTERN`, behind the `Color` and `Email` aliases (see
[python.md](python.md#types)) — and no more. They are format filters, not
validators: `EMAIL_PATTERN` in particular rejects plenty of RFC-valid addresses
and accepts plenty of nonsense, and a generic "email" regular expression is
neither simple nor universally correct. The subset may become stricter if another
divergence is found; it is not guaranteed to grow.

## Safe integers

Every integer that reaches a plan must fit JavaScript's safe integer range,
from `-9007199254740991` to `9007199254740991`. Bounds, `multipleOf`, `step`,
choices, list lengths and defaults at any depth go through the same check.

This does not restrict `pytypehint`, which keeps accepting arbitrary
integers. It only prevents sending a value the browser would round.

Exclusive bounds are converted to inclusive ones before that check, so an
exclusive limit can fail because the inclusive value it needs falls outside
the range. This conversion applies to integer bounds. String and list *length*
bounds are inclusive in the browser contract and the core does not allow
exclusive length bounds; the adapter rejects one defensively rather than
dropping the `exclusive` flag and weakening the bound.

An ordinary integer range with a `multipleOf` must contain at least one value
that satisfies it: `Min(1), Max(4), MultipleOf(7)` has none and is rejected —
by the **core**, when it compiles the schema, so the adapter and the browser
validator do not re-check it. This is range membership, distinct from a slider,
whose default must land on a `min + k * step` position. A `Slider` with a
`Placeholder` is also rejected — a range input has no placeholder — alongside
the other control combinations below.

The browser validator (`checkPlan`) validates everything a hand-written expanded
plan needs to be buildable — structure, the network boundary, and the semantics
of the normalized document — but it does not restate schema-compiler invariants
that cannot affect runtime integrity. So a **valid** manual plan is not the same
as a form that can reach ready: a hand-written plan can carry a constraint that
is merely unsatisfiable (never valid) — an unreachable ordinary `multipleOf`
range, say — and `checkPlan` accepts it, because it corrupts nothing it
transports; the widget simply never becomes ready.

## Message templates are not a translation engine

Validation messages are simple templates with a single fixed placeholder —
`{value}` for the value-bearing ones, `{current}` and `{total}` for the mode
position. They do not pluralize, decline or reorder for grammar, so a default
such as `Add at least {value} items` reads awkwardly at `{value}` of one and in
languages where the noun agrees with the number.

The intended answer is wording that stays correct across counts rather than a
built-in i18n layer. A neutral phrasing sidesteps the problem — for example
`Minimum number of items: {value}` — and an application that needs full
pluralization can supply its own messages through `WebConfig` or render its own
below the widgets.

## Unsupported metadata

- `Extra` is not interpreted, including on an enum. The `enum` node reserves a
  `labels` slot (always `null` today) for the visible member labels a future
  `Extra` vocabulary would supply; that vocabulary will be designed when a real
  consumer (FuncToWeb) needs it, not before. Until then an enum shows the raw
  member names.
- Metadata combinations that ask for different controls are rejected rather
  than resolved by the adapter: `Rows`, `IsPassword` and `Choices` on a
  string, and `Choices` with `Slider`, `Choices` with `Placeholder`, or
  `Slider` with `Placeholder` on an integer.
- Branches that share a transport type *and* an option id are rejected,
  because nothing downstream could tell them apart.

## File fields

How a file field works — its two reference origins, the reference minting, the
Replace/Restore cycle and the host's upload loop — is the
[JavaScript API](javascript.md#values-completed-outside-the-browser)'s to
describe. What is *limited* here:

- A file **composes like any other node**, at any depth: inside a list, a
  dataclass, an optional or a union branch, and inside combinations of those.
  A bare `list[File]` is the one shape with a dedicated representation — a single
  `multiple` widget rather than a list of single-file widgets — and that is a
  shortcut, not a restriction on the others.
  The only file combinations still refused are the ones listed here as genuinely
  unrepresentable: the `Str` atoms beside `IsPathFile`, the byte-size bounds, and
  a union whose branches share a transport (see below).
- `File | str` — and so `list[File | str]` — is **inconstructible**, and the core
  says so: a file *is* a `Str`, so both branches carry the option id `"str"` and
  the schema fails to compile with `duplicate option types in shape`. Nothing can
  tell the two apart on the wire, so this is a real ambiguity rather than a
  missing feature. It does not extend to `File | None` or `File | int`, whose
  branches are distinguishable and both work.
- A file **default is an existing reference**, the same thing `setValue()` takes.
  The browser never checks that bytes stand behind it; where the guarantee comes
  from depends on which road the reference took. A default written into a
  **Python schema** — a prefill included, since a prefill is a temporary default
  — is certified by `IsPathFile` before a plan can exist, so it has to be a real
  local file and a missing one fails with `file does not exist` instead of
  rendering. A reference applied at runtime with **`setValue()`** is frontend
  state only; it is certified later, when the host resolves it with
  `decode(..., file_resolver=...)` and the core checks the resulting path. A
  reference that expires in between shows fine and fails at `build()`.
- `IsPathFile(min_size=...)` / `max_size=...` travel now, but only a **local
  pick** can be weighed against them. A reference carries no bytes, so a form
  can show one that breaks a bound and only fail at `build()`. A bound larger
  than a safe JavaScript integer is refused rather than rounded.

**A reference is not a path, and the browser cannot close that gap.** All the
widget ever checks is the extension — a lenient `endswith` filter — and it has no
way to know whether bytes were stored. The core does check, since
`pytypehint 0.0.7`: `IsPathFile` certifies extension, existence, regular file and
byte size, so an unstored reference fails at `build()`. Mapping the reference to
where the bytes actually live is the host's, through
`decode(..., file_resolver=...)`; a wrapper such as FuncToWeb that builds the
upload cycle owns it. The full cycle is in
[Values completed outside the browser](javascript.md#values-completed-outside-the-browser).

`IsPathFile(min_size=...)` and `max_size=...` **are** emitted, as `minSize` and
`maxSize`, and the widget weighs a chosen `File` against them so the bytes never
move when the answer is already no. That is where its knowledge ends: a
reference names a file the browser never saw, so it is not weighed, and neither
is a default. The size that decides is the one `build()` measures on disk.

## Static data only

`Choices` (on any scalar, dates and times included), `Literal[str]` and
`Literal[int]` describe a closed set of values that is known when the plan is
generated. A plan carries no URL, no query and no callback, so a select cannot
load its options from a remote source or depend on the value of another field.

Filling a select from live data means generating a new plan with the values
already in it, or building the widget directly with `StrChoiceWidget`,
`IntChoiceWidget` or `FloatChoiceWidget` (a date/time select is a
`StrChoiceWidget` over ISO strings, and an enum select is a `StrChoiceWidget`
over member names). An enum's set of members is fixed in the type, so it is
static by nature.

## Not a web framework

`pytypehintweb` provides no web server, no routing, no static-file handler, no
authentication, no session handling and no way to invoke a Python function
from the browser. It generates plans and provides the widgets that consume
them; everything around that is the host application's.

The bundled demo is a small FastAPI application written on top of the library
to show the pipeline end to end. Its routes and its file handler are part of
the demo, not of the public API.

For the complete request/response cycle — routing, file serving and calling
the function itself — see [FuncToWeb](https://github.com/offerrall/FuncToWeb),
a separate project by the same author. From its 2.0.0 release it will use this
package as its rendering core; the dependency runs in that direction only, and
nothing here depends on FuncToWeb.

## Accessibility

The widgets expose names, descriptions, invalid state and grouping through
standard attributes on native controls. What is guaranteed, and what is **not**
covered (no WCAG statement, no real-browser test suite, focus-after-removal left
to the browser, page-level concerns owned by the host), is in the
[JavaScript API](javascript.md#accessibility).

## Text rendering, not sanitizing

Plan strings are always inserted as text and never parsed as markup, so a
label containing HTML shows the characters instead of rendering them. That is
a rendering guarantee, not a content filter: nothing is stripped, escaped or
rewritten, and `form.read()` returns exactly what the user typed.

Deciding whether a plan comes from a trustworthy producer, and validating the
transport object once it leaves the browser, remain the application's job.

## Distribution

`pytypehintweb` is published on PyPI (`pip install pytypehintweb`); there is no
npm package. It is early (alpha) and not meant for production deployment yet.
Hosting, deployment and CI belong to the host application, not to the library.

The browser modules live inside the Python package, under
`pytypehintweb.STATIC`, and are meant to be served or copied as plain static
files.

They are ES modules with no build step, no bundler configuration and no type
declarations.

## Browser support

The **JavaScript runtime** uses standard ES modules, classes, nullish
coalescing, `WeakMap`, `BigInt` and the `u` regular expression flag. It targets
current versions of the major browsers.

The optional **`widgets.css` stylesheet** additionally uses custom properties,
the CSS `:has()` selector, `:not()` with a complex argument and `mask-image`
(with the `-webkit-` fallback), so it requires a
current browser. This is a stylesheet requirement only: the widgets remain
semantically correct and keyboard-operable without the stylesheet, so a browser
lacking them still runs the library — it only loses some of the polished
styling. There are no CSS fallbacks or polyfills, and no `light-dark()`: the
themes are explicit blocks, so a subtree can be themed without depending on a
global `color-scheme`.

The stylesheet also expects the widgets to be mounted inside a `.pth-root`
container; outside one they are unstyled rather than half-styled. Its theme
contract is exactly `.pth-root`, `.pth-root[data-pth-theme="light"]` and
`.pth-root[data-pth-theme="dark"]` — the pre-1.0 `[data-theme]` attribute and
the `.light-mode` / `.dark-mode` classes were removed, not aliased.

**The stylesheet needs its `icons/` subdirectory.** Its icons are `.svg` files
addressed relative to the sheet, so they follow it under any static prefix, but
a host that serves only the flat files leaves the selects without a chevron and
the remove buttons without a glyph. Nothing is embedded as a data URI, so the
page needs no `img-src data:` — a plain `img-src 'self'` is enough — and the
library sets no CSP headers of its own. An icon that fails to load costs the
glyph and nothing else: size, accessible name and behaviour are unaffected.

The automated tests run on Node with a lightweight fake DOM, so they cover
widget logic, state and transport, not layout or real browser event
behaviour. No specific browser version is claimed beyond what those tests
demonstrate; the bundled demo is the practical way to check a target browser.

## Plan contract stability

The plan contract is public and tested but pre-1.0: breaking changes may occur
before 1.0. See the [plan contract](plan.md#compatibility) for the version
policy (a mandatory `v`, currently `1`) and the single-representation guarantee.
