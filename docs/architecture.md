# Architecture

`pytypehintweb` is a rendering adapter, not an application server. The library
ends at plan generation, widget construction and transport reading: `plan_of()`
returns a dictionary, `compileForm()` returns widgets, `form.read()` returns a
value. HTTP routing, static-file delivery, authentication, submission handling
and function execution belong to the host application. The bundled
`pytypehintweb.demo` *is* such an application (FastAPI, mounted static dir,
`/plans` and `/build/{id}`); it is a showcase, not an API of the library.

## Layers

```text
pytypehint          compiles types, validates, builds objects
plan.py             Python adapter: schema -> expanded plan
decode.py           Python adapter: transport -> build input (int->float, ISO->date/time)
static/defaults.js  official runtime defaults and known property names
static/slider.js    shared, dependency-free slider position arithmetic
static/normalize.js structural validation and normalization
static/contract.js  semantic validation of the normalized plan
static/form.js      orchestration: widgets, initial values, transport
static/inputs.js    scalar widgets
static/fields.js    the widget contract and the containers
static/widgets.css  optional presentation
static/icons/*.svg  the icons that stylesheet references
```

Each layer depends only on the ones above it: the core knows nothing about the
web layer, and the widgets know nothing about the plan protocol. `slider.js` is
a dependency-free leaf whose position arithmetic (`firstSliderValue`,
`sliderReaches`) is shared by `contract.js` (validation) and `inputs.js`
(`IntWidget` initialization), so the congruence is implemented once.

```text
forward:  function/dataclass -> pytypehint schema -> plan_of() -> expanded plan
          -> normalize/check -> compileForm() -> widgets
reverse:  widgets -> form.read() -> transport object -> (host carries it)
          -> decode() -> schema.build() or another consumer
```

`decode()` is the reverse-pipeline counterpart of `plan_of()`: the forward path
turns a schema into a plan, and the reverse path turns the transport object back
into something `schema.build()` accepts by exact type. It is a preparation step,
not validation — it converts only what the wire could not carry faithfully
(today, an `int` where the shape is `Float`, and an ISO string where it is
`Date`/`Time`), guided by the shape and never by a value's content, and leaves
the core to reject anything wrong.

`value()` belongs to the components (the plain value they represent); `read()`
belongs to the orchestration (the transport shape a consumer expects, wrapping
union branches). A widget never decides whether its value travels `plain`,
`inline` or `wrapped`.

## Source of truth

`pytypehint` is the source of truth for types, constraints, defaults, unions,
construction and final validation. `plan.py` is the only adapter: it translates
a compiled schema into the flat, serializable [plan contract](plan.md), and when
a guarantee the core makes cannot be preserved in the browser it raises
`TypeError` — no rule is ever degraded silently. The browser may anticipate
errors to improve the experience, but it does not replace the core's validation
and is not a second source of truth.

That is why Python vocabulary stops at `plan.py`: `Shape`, `Struct`,
`option_id`, `MISSING` and the `$type` rules never surface in the widget API.
`form.js` consumes a hand-written plan and a plan from another backend
identically.

## Validation

```text
structural validation and normalization
    -> semantic validation of the normalized plan
    -> form construction
```

The structural pass runs on the plan as received (types of present properties,
required and unknown properties, valid `kind` and `mode`, the `hasDefault` /
`default` pair). The semantic pass runs on the normalized plan, where every
option holds a real value. Checking types before anything else, and never
filling absences, keeps every rule free of "if absent, assume this": an omitted
property is `<path>: is required`, not an implied default.

A plan default is producer configuration, not a live user value, so it is
checked against the **complete** normalized node — both structurally compatible
and **constraint-valid**. A default that breaks a constraint fails `checkPlan()`
and never mounts; a value the user later types may stay representable while
invalid, and the widget reports that through `hasError()` / `isReady()`.

A **file** node is a node like any other, and the compiler treats it that way.
There is no list of allowed file positions and no predicate asking whether a
shape "contains a file": a shape is representable when each of its nodes is, and
`_options_node` / `compileNode()` recurse over lists, optionals, choices and
structs without knowing what is at the bottom. The single file-specific decision
is a shortcut — a *bare* `list[File]` becomes one `multiple` file node instead of
a list of single-file widgets — and it is chosen by an exact shape match, so it
cannot capture anything wider.

A **file** default is the one case where the check stops short of the value on
purpose. `checkPlan()` owns the shape a browser can see — a `str` for a single
node, a `list[str]` for a `multiple` one, non-empty, extension-filtered, within
the file-count bounds — and stops there, because existence, regular-file and byte
size are not observable from a page. They are not observable from the core
either: `FileHint` reads the extension off the text and opens nothing, so those
questions have no answer anywhere in this stack. They belong to the **host**,
which is the only layer that knows where the bytes went, and it answers them in
`decode(..., file_resolver=...)`. The compiler applies the default by calling the
widget's public `setValue()`, so a default and a runtime assignment are one
implementation rather than two.

`checkPlan()` validates everything a hand-written expanded plan needs to be
buildable — structure, the network boundary, and the semantics of the normalized
document including its defaults — but it does not restate schema-compiler
invariants that cannot affect runtime integrity (e.g. ordinary-range
`multipleOf` reachability). New semantic rules are still written once, in Python.

### Who owns which rule

| Layer | Owns |
| --- | --- |
| `pytypehint` | core schema validity: positive `Rows` and `Step`, non-empty and non-repeating `Choices`, non-empty ranges, ordinary and slider ranges that admit a valid multiple of `MultipleOf`, choices consistent with their constraints, unions without repeated option types or homonym discriminators (dataclasses or enums that would share a `$type` name) |
| `plan_of()` | web representability and the exact converted browser contract it emits: every value a JavaScript safe integer, portable patterns, control combinations that ask for different widgets, unique branch option ids (defense in depth — the core compiler rejects that collision on every path it compiles, a field's union and a list's items alike, so this one only ever fires on a shape assembled by hand), nested objects with at least one field, exclusive integer bounds that still leave a value after integer conversion, sliders with both converted limits, sliders with a reachable valid position, converted defaults valid against their node including the slider `Step` grid |
| `normalizePlan()` | structural validity: every non-conditional property present (a missing one is `<path>: is required`), no unknown keys, types of values, the `hasDefault` / `default` pair, canonical scalar forms (a date value is a real calendar date, not merely the `YYYY-MM-DD` shape), and the structural shape invariants — non-empty field names, `optional` nodes only in list-item position, and `optional` / `enabled` field coherence |
| `checkPlan()` | everything a hand-written expanded plan needs to be buildable — structure, network boundary, and the semantics of the normalized document: coherent ranges, choices against their constraints, reachable slider positions, unique and non-empty field names within each scope, `inline` transport only on object branches, `optional` nodes only as list items, unique branch values, and every plan default validated against the full constraints of its node. It does **not** restate schema-compiler invariants that cannot affect runtime integrity (e.g. ordinary-range `multipleOf` reachability) |
| `schema.build()` | the values actually submitted |
| the host application | everything about stored bytes: where an upload went, whether a reference still stands for something, whether it has expired, whether it is this caller's to redeem, and any byte-size guarantee that has to hold authoritatively. `decode(..., file_resolver=...)` is the seam, and an exception raised there propagates unchanged |

The adapter does not restate the core's schema semantics for their own sake; it
re-checks only the parts that become concrete once the plan is converted for the
browser (exclusive bounds collapse *after* integer conversion, a slider's
reachability depends on the converted limits, safe-integer representability is a
browser property the core need not know). These are defense in depth checked in
Python before the plan leaves the process — the core validates its schema
semantics, and the adapter additionally verifies the exact converted browser
contract it is about to emit. The normalized semantic layer is broader still,
because a hand-written plan never passed through `pytypehint`; for a generated
plan those invariants were guaranteed upstream and the browser only confirms
them.

## Widget contract

`Widget` requires `isEmpty()` and `value()`; the base provides `onChange()`,
`error()` (default `null`), `hasError()` and `isReady()`. Scalar widgets add
`_check()`/`_apply()` and inherit `setValue()` (validate-and-apply); containers
are built from a plan, not reassigned, so they have no `setValue()`. Containers
use only that contract on their children — they never inspect a child's concrete
class. The full public API is in the [JavaScript API](javascript.md).

| Container      | Role                                                     |
| -------------- | -------------------------------------------------------- |
| `Field`        | label, description, optional toggle                       |
| `GroupWidget`  | several named widgets travelling as one object            |
| `ListWidget`   | rows created by a factory, with `minItems` / `maxItems`   |
| `ChoiceWidget` | one branch active at a time, selected by an opaque `value` (`Shape.option_id()` when the plan comes from Python) |

## Styling

`widgets.css` gives a polished appearance and is not part of the contract. Its
`pth-*` classes are a technical namespace with no global selectors, driven by
`--pth-*` design tokens; semantic behaviour and keyboard accessibility do not
depend on it.

Presentation stops at the stylesheet — including its icons, which are `.svg`
files under `static/icons/` that the sheet addresses relative to itself. Nothing
is embedded as a data URI, so a host needs no `img-src data:`, and the runtime
builds no SVG of its own; it only has to serve the whole static directory.

Every rule starts at the `.pth-root`
container the host mounts the widgets in, colours resolve through
`--pth-<name>-light` / `--pth-<name>-dark` palette pairs into the active
`--pth-<name>` tokens the widgets read, and the theme is chosen by
`prefers-color-scheme` or by a `data-pth-theme="light|dark"` override on the
root or any ancestor. That is the whole theme API: it is not in the plan, not
in `compileForm()`, not in the transport and not in validation, and the runtime
carries no theme JavaScript at all — which is also why the automatic mode
cannot flash. See the [JavaScript API](javascript.md#styling) for the tokens
and the theme contract.
