# Current limitations

Everything a schema carries that the browser cannot represent faithfully
makes `plan_of()` raise `TypeError` — with one exception,
[a recursive shape](#recursive-shapes), which meets the interpreter's stack
limit before any check of ours can name it. Nothing is degraded silently, so the
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
`schema.build()`. **What it prepares is not this package's to decide.** The
portable representation — `int → float` where the shape is `Float`, ISO text →
`date`/`time` where the shape is `Date`/`Time`, a member name → enum member
where the shape is `EnumShape`, and the `$type`/`$value` wrapper that names an
option the value alone cannot — is restored by `schema.decode()` in the core,
and the web layer adds exactly one thing to it: the file references, resolved
through `file_resolver`. So the scope of the reading is the core's scope, and it
widens when the core's does rather than when this package decides it should. The
limit that does belong here is the file one: nothing resolves a reference unless
a host supplies the callable, because neither library knows what storage means.

The reading is made only where the shape at the path (or an explicit `$type` in
a union) fixes it, never by inspecting a value's content — a `str` that looks
like a date, or matches a member name, stays a `str`. Everything the schema
cannot name a reading for passes through unchanged for `build()` to judge, and
three consequences of that are worth stating as limits rather than left to be
discovered:

- **A date or a time is read in its canonical spelling only** — `YYYY-MM-DD`,
  and `HH:MM` with optional seconds, fraction and offset. `fromisoformat()`
  accepts far more, and the two grammars overlap (`"20200101"` reads as a date
  *and* as a time), so letting it decide would let the text of a value select an
  option. A producer that spells one of them some other way gets its string back
  and a `build()` error, not a silent reading.
- **An integer becomes a float only when a float equals it exactly.** `2**53 + 1`
  travels as it came, and so does an integer too large to convert at all:
  restoring the neighbouring float would hand `build()` a number the transport
  never carried, and `build()` would take it.
- **A wrapper whose payload did not read as the branch it names survives.** The
  transport said `date` and the value is not one, so nothing files it under the
  `str` beside it; the dict reaches `build()` whole and is reported there. This
  is also what keeps a file reference from reaching a `FileHint` field without
  passing through `file_resolver`.

One property of `decode()` is a guarantee rather than a limit, and it is worth
recording beside them: it **never raises on a value**, whatever that value's
type, size or spelling. Every refusal of a value is `build()`'s.

## Recursive shapes

A dataclass that refers to its own type — directly, or through another dataclass
that leads back to it — **compiles in the core** and is describable there: the
core's portable contract writes each dataclass once into a definition table and
lets a field point at it, so `to_dict()` represents the cycle as a reference and
terminates.

A plan is not that format. It is **fully expanded**: every node carries its own
options, messages and defaults written out in place, with nothing to point at
and no table to point into, because the browser reads a plan top to bottom and
resolves no references. A shape that contains itself has no expanded form — the
expansion does not terminate — so `plan_of()` cannot produce one:

```python
@dataclass
class Node:
    name: str
    child: "Node | None" = None


struct_of(Node)             # compiles
struct_of(Node).to_dict()   # the child field carries a reference back to Node
plan_of(Node)               # RecursionError
```

This is the one limit on this page that does not arrive as a `TypeError` naming
the offending path. The recursion is caught by the interpreter's stack limit
rather than by a check that knows what it is looking at, so what surfaces is a
bare `RecursionError` with no field coordinates in it. Finding the cycle before
descending into it is a check that has not been written; a recursive form has no
representation waiting behind it either way, so what is missing is the
diagnosis, not the feature.

A form over a recursive structure needs a shape with a bound: a fixed depth
spelled out as distinct dataclasses, or a flat `list` of nodes carrying a parent
key. Both are representable and both expand.

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
  unrepresentable: the `Str` atoms beside `FileHint`, and a union whose branches
  share a transport (see below). The byte-size bounds are not among them — they
  travel; what is limited is who can act on them.
- `File | str` — and so `list[File | str]` — is **inconstructible**, and the core
  says so: a file *is* a `Str`, so both branches carry the option id `"str"` and
  the schema fails to compile (`duplicate option types in shape` on a field,
  `both compile to str` on a list's items). Nothing can tell the two apart on the
  wire, so this is a real ambiguity rather than a missing feature. It does not
  extend to `File | None` or `File | int`, whose branches are distinguishable and
  both work.
- A file **default is an existing reference**, the same thing `setValue()` takes,
  and it is checked exactly as far as text can be checked: it must be a `str`
  whose extension is accepted. Nothing verifies that bytes stand behind it — not
  the browser, which never saw them, and not the core, which opens nothing. A
  reference that was never uploaded, that has expired or that belongs to somebody
  else renders like any other and travels back intact.
- `FileHint(min_size=...)` / `max_size=...` travel, but only a **local pick** can
  be weighed against them, because only a local `File` carries a `.size`. A
  reference carries no bytes, so a form can show one that breaks a bound and
  nothing downstream will object. A bound larger than a safe JavaScript integer
  is refused rather than rounded.

**A reference is not a path, and nothing between the browser and the core can
close that gap.** All the widget ever checks is the extension — a lenient
`endswith` filter — and the core checks the same extension on the same text.
Neither of them knows whether bytes were stored, and since `pytypehint 1.0.0`
neither claims to: existence, regular-file-ness and byte size left the core, so
an unstored reference builds into the plain string it always was. Deciding
whether a reference is real is the **host's**, at the only point where code that
knows the storage sees it — `decode(..., file_resolver=...)`, which propagates
whatever the host raises. A wrapper such as FuncToWeb that builds the upload
cycle owns that decision. The full cycle is in
[Values completed outside the browser](javascript.md#values-completed-outside-the-browser).

`FileHint(min_size=...)` and `max_size=...` **are** emitted, as `minSize` and
`maxSize`, and the widget weighs a chosen `File` against them so the bytes never
move when the answer is already no. That is also where they stop: a reference
names a file the browser never saw, so it is not weighed, and neither is a
default. There is no second opinion further down — a byte bound that has to hold
authoritatively belongs beside the storage that holds the bytes.

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
npm package. Hosting, deployment and CI belong to the host application, not to
the library.

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

The plan contract is public and tested. A breaking change to it increments `v`
and belongs to a major release; `v: 1` has one fixed meaning and keeps it. See
the [plan contract](plan.md#compatibility) for the version policy (a mandatory
`v`, currently `1`) and the single-representation guarantee.
