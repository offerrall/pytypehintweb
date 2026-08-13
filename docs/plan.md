# Plan contract

## Overview

A plan is plain, JSON-serializable data: dictionaries, arrays, strings,
numbers, booleans and `null`. It describes a form — its fields, nodes,
constraints, defaults and transport — without referencing any Python class.

There is a single representation of the contract: the **fully expanded plan**.
Every known property is present and holds an explicit value — `null` or `false`
where there is nothing to constrain — so no widget ever has to interpret an
absence. There is no compact form and no default filling: an omitted property
is a validation error. `plan_of()` always emits this expanded form, and a
hand-written plan must too.

`compileForm()` receives an already parsed JavaScript object. Getting that
object into the browser — JSON, `fetch`, a template, a constant, another
backend — is outside the library.

A plan captures the visible texts (messages and labels) in force when it is
generated; a serialized plan should be regenerated after changing `WebConfig`.

## Version

Every form plan carries a top-level integer `v`, always present, because it
identifies the contract itself.

```text
{ "v": 1, "kind": "form", "name": "example", "description": null, "fields": [] }
```

Only version `1` is currently supported. A plan whose `v` is missing, is not an
integer, or names an unsupported version is rejected before any widget is
constructed:

```text
plan.v: is required
plan.v: must be an integer
plan.v: unsupported plan version: 2
```

There are no migrations or compatibility layers: a producer targets exactly
version `1`.

The version policy is simple: **every incompatible change to the serialized plan
increments `v`, including before 1.0.** A given `v` therefore has one fixed
meaning, so a consumer can pin the `v` it understands and trust that a plan
carrying it has not changed shape underneath.

## Producing and checking plans

`plan_of()` is the supported Python producer; it always emits a valid `v: 1`
plan. Hand-written browser plans are checked by `checkPlan()` (which
`compileForm()` calls for you). A standalone Python plan validator is not
currently provided — Python users generate plans through `plan_of()`.

## A single, expanded representation

A node carries every property of its kind, explicitly. A `str` node is always:

```json
{
  "kind": "str",
  "options": {
    "minLength": 3,
    "maxLength": null,
    "pattern": null,
    "patternMessage": "Invalid format",
    "minMessage": "Must contain at least {value} characters",
    "maxMessage": "Must contain at most {value} characters",
    "placeholder": null,
    "password": false,
    "rows": null,
    "choices": null
  }
}
```

There is no shorter form: omitting `maxLength` or `options` is an error, not an
implied `null`. The tables under [Official defaults](#official-defaults) list
the value each property holds when the producer has nothing more specific to
say — but the property is still written.

An earlier draft of the contract carried a second, compact representation that omitted every property equal to its default. It was removed before the first release: with gzip on the wire the byte savings are negligible, while the dual representation doubled the surface — mirrored default tables in Python and JavaScript, a parity test between them, and six-case presence semantics. One representation, one meaning per key, is the contract.

## General rules

- Unknown keys are rejected, with their path.
- Every known property is required; a missing property is rejected with
  `<path>: is required`.
- Normalization never mutates the object it receives.
- Normalized nodes never share a mutable options object.
- Every value must be JSON-serializable. Functions, class instances and DOM
  nodes are rejected.
- Every string is text, never markup. See
  [Text is never markup](#text-is-never-markup).

### Explicit values

`null` and `false` are explicit values, not absences. The contract keeps these
apart:

```text
null                a real value where the property accepts it (e.g. no bound)
""                  a value
0                   a value
[]                  a value
false               a value
```

`default` is the one property whose *presence* carries meaning, paired with
`hasDefault`:

```text
hasDefault false
    -> default must be absent

hasDefault true
    -> default must be present, including when it is null
```

### Placeholder

`placeholder` is always present in a `str`/`int` node's `options`; it is a
string only on an ordinary input, and `null` otherwise:

```text
ordinary str/int input
    placeholder is a string or null

closed choices
    placeholder must be null (a closed select has no empty prompt)

closed choices without an explicit default
    the first choice is selected
```

A closed-choice node's `placeholder` is `null`: it always represents one of its
values — the explicit default, or the first choice when there is none — so it
needs no empty leading option. Both Python and JavaScript reject a non-`null`
placeholder declared alongside `choices`. `null` on a plain input is an empty
prompt; `null` on a closed choice is simply the only value it may hold.

## Official defaults

The runtime defaults live in `static/defaults.js` as frozen objects.

### Form

| Property      | Default |
| ------------- | ------- |
| `description` | `null`  |

### Field

| Property      | Default          |
| ------------- | ---------------- |
| `label`       | the field `name` |
| `description` | `null`           |
| `optional`    | `false`          |
| `enabled`     | `true`           |
| `hasDefault`  | `false`          |

### String options

| Option           | Default                                      |
| ---------------- | -------------------------------------------- |
| `minLength`      | `null`                                       |
| `maxLength`      | `null`                                       |
| `pattern`        | `null`                                       |
| `patternMessage` | `"Invalid format"`                           |
| `minMessage`     | `"Must contain at least {value} characters"` |
| `maxMessage`     | `"Must contain at most {value} characters"`  |
| `placeholder`    | `null`                                       |
| `password`       | `false`                                      |
| `rows`           | `null`                                       |
| `choices`        | `null`                                       |

### Integer options

| Option              | Default                                  |
| ------------------- | ---------------------------------------- |
| `min`               | `null`                                   |
| `max`               | `null`                                   |
| `multipleOf`        | `null`                                   |
| `step`              | `null`                                   |
| `slider`            | `false`                                  |
| `showValue`         | `false`                                  |
| `placeholder`       | `null`                                   |
| `choices`           | `null`                                   |
| `safeMessage`       | `"Must be a safe integer"`               |
| `invalidMessage`    | `"Enter a valid integer"`                |
| `minMessage`        | `"Must be at least {value}"`             |
| `maxMessage`        | `"Must be at most {value}"`              |
| `multipleOfMessage` | `"Must be a multiple of {value}"`        |
| `increaseLabel`     | `"Increase"`                             |
| `decreaseLabel`     | `"Decrease"`                             |

### Float options

| Option           | Default                      |
| ---------------- | ---------------------------- |
| `min`            | `null`                       |
| `max`            | `null`                       |
| `minExclusive`   | `false`                      |
| `maxExclusive`   | `false`                      |
| `step`           | `null`                       |
| `choices`        | `null`                       |
| `placeholder`    | `null`                       |
| `invalidMessage` | `"Enter a valid number"`     |
| `finiteMessage`  | `"Must be a finite number"`  |
| `minMessage`     | `"Must be at least {value}"` |
| `maxMessage`     | `"Must be at most {value}"`  |
| `increaseLabel`  | `"Increase"`                 |
| `decreaseLabel`  | `"Decrease"`                 |

### Date options

| Option           | Default                     |
| ---------------- | --------------------------- |
| `min`            | `null`                      |
| `max`            | `null`                      |
| `placeholder`    | `null`                      |
| `choices`        | `null`                      |
| `invalidMessage` | `"Enter a valid date"`      |
| `minMessage`     | `"Must be on or after {value}"`  |
| `maxMessage`     | `"Must be on or before {value}"` |

### Time options

| Option           | Default                     |
| ---------------- | --------------------------- |
| `min`            | `null`                      |
| `max`            | `null`                      |
| `minExclusive`   | `false`                     |
| `maxExclusive`   | `false`                     |
| `placeholder`    | `null`                      |
| `choices`        | `null`                      |
| `invalidMessage` | `"Enter a valid time"`      |
| `minMessage`     | `"Must be at or after {value}"`  |
| `maxMessage`     | `"Must be at or before {value}"` |

### Enum options

| Option        | Default |
| ------------- | ------- |
| `choices`     | `null`  |
| `placeholder` | `null`  |
| `labels`      | `null`  |

### File options

| Option               | Default                       |
| -------------------- | ----------------------------- |
| `extensions`         | `[]`                          |
| `invalidMessage`     | `"Not an accepted file type"` |
| `multiple`           | `false`                       |
| `minFiles`           | `null`                        |
| `maxFiles`           | `null`                        |
| `minSize`            | `null`                        |
| `maxSize`            | `null`                        |
| `minMessage`         | `"Add at least {value} files"` |
| `maxMessage`         | `"Keep at most {value} files"` |
| `minSizeMessage`     | `"File is too small; minimum {value}"` |
| `maxSizeMessage`     | `"File is too large; maximum {value}"` |
| `currentLabel`       | `"Current file: {value}"`     |
| `currentRemoveLabel` | `"Remove current file"`       |
| `currentReplaceLabel`| `"Replace file"`              |
| `currentRestoreLabel`| `"Restore current file"`      |

### List options

| Property      | Default                        |
| ------------- | ------------------------------ |
| `addLabel`    | `"Add"`                        |
| `removeLabel` | `"Remove"`                     |
| `minItems`    | `null`                         |
| `maxItems`    | `null`                         |
| `minMessage`  | `"Add at least {value} items"` |
| `maxMessage`  | `"Keep at most {value} items"` |

### Optional item nodes

| Property  | Default  |
| --------- | -------- |
| `label`   | `"Item"` |
| `enabled` | `true`   |

These tables list the value `plan_of()` writes for a property when nothing more
specific applies. Every property is still present in the plan; the table is a
reference for what a producer emits, and the scalar/list/choice/optional tables
mirror `static/defaults.js`, which the widget constructors use for hand-built
widgets.

## Form

Required: `v`, `kind`, `name`, `description`, `fields`.

```json
{
  "v": 1,
  "kind": "form",
  "name": "create_user",
  "description": null,
  "fields": []
}
```

With a description:

```json
{
  "v": 1,
  "kind": "form",
  "name": "schedule_report",
  "description": "Schedule a recurring report.",
  "fields": []
}
```

`v` is the contract version; see [Version](#version). `kind` must be
`"form"`. `name` is the dataclass name or the function name. `description` is
the function docstring; it is plain text, never HTML.

## Fields

Required: `name`, `label`, `description`, `optional`, `enabled`, `hasDefault`,
`node` (and `default` when `hasDefault` is `true`).

```json
{
  "name": "username",
  "label": "username",
  "description": null,
  "optional": false,
  "enabled": true,
  "hasDefault": false,
  "node": {
    "kind": "str",
    "options": {
      "minLength": null,
      "maxLength": null,
      "pattern": null,
      "patternMessage": "Invalid format",
      "minMessage": "Must contain at least {value} characters",
      "maxMessage": "Must contain at most {value} characters",
      "placeholder": null,
      "password": false,
      "rows": null,
      "choices": null
    }
  }
}
```

An optional field that starts disabled with an explicit `None` default:

```json
{
  "name": "nickname",
  "label": "nickname",
  "description": null,
  "optional": true,
  "enabled": false,
  "hasDefault": true,
  "default": null,
  "node": {
    "kind": "str",
    "options": {
      "minLength": null,
      "maxLength": null,
      "pattern": null,
      "patternMessage": "Invalid format",
      "minMessage": "Must contain at least {value} characters",
      "maxMessage": "Must contain at most {value} characters",
      "placeholder": null,
      "password": false,
      "rows": null,
      "choices": null
    }
  }
}
```

`optional` means the union contains `None`. `enabled` is the resolved initial
state of the toggle. `label` defaults to `name` only in the producer that emits
the plan; in the plan itself it is always present.

Field invariants:

- `name` must be a non-empty string, unique within its immediate field
  collection. Uniqueness is per scope: the form root and each nested object
  are checked independently, so the same name may appear in unrelated nested
  objects. The two strings `$type` and `$value` are reserved by the
  discriminated transport (a `wrapped`/`inline` branch uses them for the
  discriminator and payload) and are rejected as field names; every other
  non-empty string, `"__proto__"` included, is a valid name and travels intact.
- `enabled` is only meaningful for an optional field. It is always present, and
  on a non-optional field it must be `true`; a `false` `enabled` there is a
  contradiction and is rejected. When `optional` is `true`, `enabled` may be
  `true` or `false`.

```text
plan.fields[1].name: duplicated field name
plan.fields[0].name: must be a non-empty string
plan.fields[0].name: "$type" is reserved by the transport and cannot be a field name
plan.fields[0].enabled: must be true when the field is not optional
```

## String nodes

Required: `kind`, `options`. `options` carries every string property (see the
[String options](#string-options) table).

```json
{
  "kind": "str",
  "options": {
    "minLength": 3,
    "maxLength": null,
    "pattern": null,
    "patternMessage": "Invalid format",
    "minMessage": "Enter at least {value} characters",
    "maxMessage": "Must contain at most {value} characters",
    "placeholder": null,
    "password": false,
    "rows": null,
    "choices": null
  }
}
```

Invariants:

- `minLength` and `maxLength` are non-negative safe integers, or `null`.
- `minLength` must not exceed `maxLength`.
- `rows`, `password` and `choices` ask for different controls and never
  appear together.
- `choices` must be a non-empty array of unique strings that satisfy
  `minLength`, `maxLength` and `pattern`.
- `rows` must be a positive safe integer.

`minLength` and `maxLength` count Unicode code points, matching Python's
`len(str)` rather than UTF-16 units.

## Integer nodes

Required: `kind`, `options`. `options` carries every integer property (see the
[Integer options](#integer-options) table).

```json
{
  "kind": "int",
  "options": {
    "min": 0,
    "max": null,
    "multipleOf": 5,
    "step": null,
    "slider": false,
    "showValue": false,
    "placeholder": null,
    "choices": null,
    "safeMessage": "Must be a safe integer",
    "invalidMessage": "Enter a valid integer",
    "minMessage": "Must be at least {value}",
    "maxMessage": "Must be at most {value}",
    "multipleOfMessage": "Must be a multiple of {value}",
    "increaseLabel": "Increase",
    "decreaseLabel": "Decrease"
  }
}
```

Invariants:

- Every integer in a plan is a JavaScript safe integer.
- `min` must not exceed `max`.
- `choices` must be a non-empty array of unique safe integers satisfying
  `min`, `max` and `multipleOf`.
- `choices` and `slider` never appear together.
- A `slider` needs both `min` and `max`; with a `multipleOf`, at least one
  reachable slider position must satisfy it.
- `step` must be a positive safe integer.
- `multipleOf` is a positive safe integer, or `null`. A zero or negative
  `multipleOf` is rejected before any widget, slider check or `BigInt` division
  runs, so a malformed plan never leaks a native `RangeError`.

Exclusive bounds are already converted to inclusive ones by the Python adapter.

`Step` and `MultipleOf` are distinct properties; `multipleOf` is **never**
written into the plan's `step`. The two stepping strides differ and are each
pinned:

```text
ordinary numeric stepper stride   step, else multipleOf, else 1
slider grid stride                step, else 1
```

`step` (default `1`) is the slider grid, `minimum + k * step`, **plus `maximum`
itself**. `multipleOf` decides which represented integers are *valid*, and is never
used as the slider stride. So `Annotated[int, Slider(), Step(5), MultipleOf(5)]` lands only on
multiples of 5, whereas `Slider(), MultipleOf(5)` alone keeps the default stride
of 1 and can stop on intermediate invalid positions. On an ordinary input the
`▲`/`▼` arrows step by `multipleOf` when no explicit `step` is given — a
widget-local increment, not a copy of `multipleOf` into `step`.

### The maximum is always a position

When the stride does not divide the range evenly, the last full step falls short
of `maximum`. `min 1, max 100, step 5` steps `1, 6, … 96`: `100` is a value the
plan declares valid, and a slider that could not reach it would be refusing a
valid value — which the doctrine forbids. So `maximum` is a grid position of its
own, reached by a final short step:

```text
1 ─ 6 ─ … ─ 91 ─ 96 ─ 100
                  └─ 4, not 5
```

The positions *between* the last full step and the maximum are not on the grid:
`97`, `98` and `99` are refused exactly as `2` or `3` are. Only `maximum` is
added, never a value inside a stride.

A native `<input type="range">` cannot express this — it only offers
`min + k*step` and snaps anything else — so a widget whose stride misses the
maximum drives its range input by grid *index* (`min 0`, `max` the last index,
`step 1`) and maps index to value. The value contract is unchanged: `value()`
returns the integer, `setValue()` takes the integer. An indexed slider carries
`aria-valuetext` so a screen reader announces the value rather than the index.
When the stride does divide the range, the range input still carries the real
`min`, `max` and `step`, and no mapping happens.

`multipleOf` reachability follows the same grid: a slider whose only valid
multiple *is* the maximum is reachable and starts there.

A malformed integer that cannot be parsed at all (`abc`, `1.5`, `1-2`) shows
`invalidMessage`; a syntactically valid integer outside JavaScript's safe range
shows `safeMessage`.

## Float nodes

Required: `kind`, `options`. `options` carries every float property (see the
[Float options](#float-options) table).

```json
{
  "kind": "float",
  "options": {
    "min": 0.5,
    "max": 10.0,
    "minExclusive": true,
    "maxExclusive": false,
    "step": 0.1,
    "choices": null,
    "placeholder": null,
    "invalidMessage": "Enter a valid number",
    "finiteMessage": "Must be a finite number",
    "minMessage": "Must be at least {value}",
    "maxMessage": "Must be at most {value}",
    "increaseLabel": "Increase",
    "decreaseLabel": "Decrease"
  }
}
```

Invariants:

- `min` and `max` are finite numbers, or `null`. `minExclusive` and
  `maxExclusive` are booleans, **always present**, `false` when there is no
  bound or the bound is inclusive.
- The bound is compared directly against the value, exactly as the core does:
  an exclusive bound rejects the boundary value itself. There is **no** ±1
  conversion — a float has no next representable step the way an integer does,
  so `min` and `max` travel verbatim with the flag beside them.
- `min` and `max` leave no representable value when `min > max`, or when
  `min == max` and either side is exclusive; such a range is rejected. (The
  core rejects it at schema-compile time too, so `plan_of()` never emits one;
  `checkPlan` enforces it for hand-written plans.)
- `choices` must be a non-empty array of unique finite numbers, each satisfying
  `min` and `max` with their exclusivity.
- `choices` and `placeholder` never appear together (a closed select has no
  empty prompt).
- `step` is a positive finite number, or `null`. It is **presentation only** —
  the stride of the `▲`/`▼` arrows — never a validation grid: `value ± step`
  is accepted exactly as the double arithmetic lands it, so `0.1 + 0.2` gives
  the honest `0.30000000000000004`.
- There is no `slider` property; a float has no slider (see
  [limitations](limitations.md)). A plan carrying one is rejected as an unknown
  property.

The parsing grammar is exactly `-?\d+(\.\d+)?` over the trimmed text: no
scientific notation, no bare `.5` or `5.`. A comma is folded to a point before
the grammar runs, so it is accepted as the decimal separator under exactly the
same restrictions — one separator at most, never a thousands mark. Text outside
it shows `invalidMessage`. A grammar-valid magnitude that overflows to `Infinity`
shows `finiteMessage` and reads as `null`; it is never transported, the float
analogue of the integer's safe-range guard.

### A float bound, choice or default is bit-identical in the browser

Python's `repr` and JavaScript's serialization both use the shortest round-trip
form for a double, so a finite double written into a plan — a bound, a choice,
a default — is the *same* double in the browser, bit for bit. This is the float
analogue of the integer's safe-range guarantee: an integer is representable when
it is within the safe range, and every finite double is representable, always.
There is no "safe float" check. Choice equality is therefore exact double
equality: the select value comes from the plan, never from typed text, so it is
the same double the plan carried.

## Date nodes

Required: `kind`, `options`. `options` carries every date property (see the
[Date options](#date-options) table).

```json
{
  "kind": "date",
  "options": {
    "min": "2026-01-01",
    "max": "2026-12-31",
    "placeholder": null,
    "choices": null,
    "invalidMessage": "Enter a valid date",
    "minMessage": "Must be on or after {value}",
    "maxMessage": "Must be on or before {value}"
  }
}
```

A date travels as an ISO string, `YYYY-MM-DD`, produced by a native date picker.
A canonical date is **a real calendar date represented exactly as `YYYY-MM-DD`**
— the shape alone is not enough, so `2026-02-31` and `2026-13-01` are not dates.
Its bounds are **inclusive**: `plan_of()` converts an exclusive bound by ±1 day
before emitting, exactly as it does for an integer, so the node carries no
exclusivity flag.

Invariants:

- `min` and `max` are canonical ISO date strings (`YYYY-MM-DD`), or `null`.
- The range is empty, and rejected, when `min` is strictly after `max`. (The
  core rejects an empty range at compile time, so `plan_of()` never emits one;
  `checkPlan` enforces it for hand-written plans.)
- `choices` is a non-empty array of unique ISO date strings, each within `min`
  and `max`.
- `choices` and `placeholder` never appear together (a closed select has no
  empty prompt).

## Time nodes

Required: `kind`, `options`. `options` carries every time property (see the
[Time options](#time-options) table).

```json
{
  "kind": "time",
  "options": {
    "min": "09:00:00",
    "max": "17:30:00",
    "minExclusive": true,
    "maxExclusive": false,
    "placeholder": null,
    "choices": null,
    "invalidMessage": "Enter a valid time",
    "minMessage": "Must be at or after {value}",
    "maxMessage": "Must be at or before {value}"
  }
}
```

A time travels as an ISO string, `HH:MM:SS`, produced by a native time picker
with its seconds field open. Its precision is whole seconds: the core pins a time
to second precision and rejects any microsecond, so a sub-second fraction never
enters the domain and never appears in a plan. Unlike a date, a
time bound keeps its exclusivity: **the core compares a time directly with no ±1
conversion (as it does a float), so the node carries `minExclusive` /
`maxExclusive`**, always present, and the widget compares with the flag.

Invariants:

- `min` and `max` are canonical ISO time strings (`HH:MM:SS`, whole seconds),
  or `null`. `minExclusive`/`maxExclusive` are booleans, always present, `false`
  when there is no bound or the bound is inclusive.
- The range is empty, and rejected, when `min` is after `max`, or when
  `min == max` and either side is exclusive.
- `choices` is a non-empty array of unique ISO time strings, each satisfying
  `min` and `max` with their exclusivity.
- `choices` and `placeholder` never appear together.

### The canonical ISO form and lexicographic comparison

Both nodes carry bounds, choices and defaults in the **canonical** ISO form
Python's `isoformat()` produces: a date is always a real calendar date written as
`YYYY-MM-DD`; a time is always `HH:MM:SS` — whole seconds, the only precision the
core admits, so there is never a sub-second fraction. These forms are fixed-width
and zero-padded, so **a plain lexicographic string comparison orders them
correctly** — this is the invariant the widget's bound checks rely on.
`"09:05:00" < "14:30:00"` as strings because the padding makes the string order
match the clock order. A native time picker asked for `step=1` matches this
domain exactly, keeping every value at second precision — except where the
platform ignores the request: iOS offers a wheel picker with hours and minutes
only and reports `HH:MM`. Whole minutes are inside the domain, so `TimeWidget`
completes such a value to `HH:MM:00` when reading it, rather than calling a
perfectly chosen time invalid. Only a well-formed, in-range `HH:MM` is completed;
anything else stays exactly as the control reported it and remains invalid. The
control's own text is never rewritten, and `setValue()` is unaffected — it still
demands the canonical `HH:MM:SS`.

Both halves of the definition are enforced, on both sides. In a generated plan
the values start as real `datetime.date` / `datetime.time` objects, so
`pytypehint` guarantees them by construction. For a hand-written plan, a plan
from another backend, or direct widget use, the browser applies the same
guarantee: a date is checked against the calendar (`2026-02-31` and `2026-13-01`
are refused, `2024-02-29` is accepted) before it is stored as a bound, a choice
or a default, and before `DateWidget` writes it into its control. Because every
comparison happens only after both strings are certified canonical, the
lexicographic ordering above stays sound.

## Boolean nodes

Required: `kind`, `options`. A `bool` has no configurable properties, so
`options` is an empty object — present and validated as an object with no keys,
but carrying nothing:

```json
{
  "kind": "bool",
  "options": {}
}
```

A `bool` renders as a native checkbox and always represents a value: unchecked
is `false`, checked is `true`. It is never empty and never in error, so it has
no validation message.

Invariants:

- `options` is an object with no keys; any key is rejected as unknown.
- A `default`, when present, is `true` or `false`. A non-optional `bool` field
  cannot carry a `null` default (a checkbox has no empty state); `null` is only
  valid on an optional field, where it means the toggle is off.
- `true` / `false` travel as plain JSON booleans, including in a union branch
  (`value` is `"bool"`, `mode` is `plain`).

## Enum nodes

Required: `kind`, `options`. An `enum` renders as a select over its members'
names, like a `bool` with more than two options — a closed set that always holds
a value.

```json
{
  "kind": "enum",
  "options": {
    "choices": ["ACTIVE", "INACTIVE", "IN_PROGRESS"],
    "placeholder": null,
    "labels": null
  }
}
```

A member travels as its **name** (`.name`), a JSON string, never its value: a
value can be anything, repeat across aliases, or not serialize. The name is the
core's own portable spelling of a member: `schema.decode()` rebuilds it with
`cls[name]`, and the core then validates the exact member by type.

Invariants:

- `choices` is a non-empty array of unique strings — the member names, in
  declaration order. It is never `null`: the closed set of names is the enum
  itself. An alias never appears (`list(cls)` yields only canonical members).
- `placeholder` is always `null`. A closed select always represents a value (the
  default, or the first member), so it is never empty, never in error, and needs
  no prompt or validation message. The key exists only for structural symmetry
  with the other scalar nodes.
- `labels` is always `null`. It is the reserved slot for visible member labels a
  future `Extra` vocabulary would supply; until that exists it must be `null`.
  `Extra` on the core's enum is not interpreted by the adapter.
- A `default`, when present, is one of `choices`.
- On the wire a member is a JSON string, so it shares the string transport with
  `str`, `date`, `time` and other enums. When a union actually puts two or more
  of those together, the collision forces them `wrapped`, and the enum's class
  name is its `$type` discriminator. On its own in a union — `int | Estado`, where
  nothing else is a string — the enum branch travels `plain`; wrapping follows
  the collision, not the type.

## File nodes

Required: `kind`, `options`. `FileHint` on a `str` produces a `file` node. Its
value is a reference string the browser widget **generates locally** when the
user picks a file — the file's name compressed to bare ASCII (15 characters at
most), a UUID, and the file's lowercased extension. It is a reference, not a
path, and it carries no bytes: turning it into something the function behind the
schema can use is the host's, through `decode(..., file_resolver=...)`.
`FileHint(min_size=...)` and `max_size=...` travel as `minSize` / `maxSize`, in
bytes, and they are **per file**, never a combined total. They belong to the
node, so they arrive wherever a file node arrives — inside a list, a union branch
or a nested struct alike.

The browser is the only place they are ever applied: a local `File` carries a
`.size`, so the widget refuses one that already breaks a bound before any upload
happens. A reference the host plants carries no bytes at all, so nothing weighs
it — not the widget, and not the core, which never opens a value. A bound that
has to hold no matter what reaches the endpoint is the host's to enforce beside
its storage; a hand-written HTTP call skips everything in this document.

```json
{
  "kind": "file",
  "options": {
    "extensions": [".pdf", ".docx"],
    "invalidMessage": "Not an accepted file type",
    "multiple": false,
    "minFiles": null,
    "maxFiles": null,
    "minSize": null,
    "maxSize": null,
    "minMessage": "Add at least {value} files",
    "maxMessage": "Keep at most {value} files",
    "minSizeMessage": "File is too small; minimum {value}",
    "maxSizeMessage": "File is too large; maximum {value}",
    "currentLabel": "Current file: {value}",
    "currentRemoveLabel": "Remove current file",
    "currentReplaceLabel": "Replace file",
    "currentRestoreLabel": "Restore current file"
  }
}
```

The widget mints the reference on choice and `read()` carries it at once. A file
node **may carry a default**, and it means an *existing* reference the host
declares — the same thing `setValue(string)` plants at runtime, and by the same
route: the compiler applies the default through `setValue()`. It is shown as a
"current file", transported verbatim, and it starts no upload; it is not a local
selection, so `file()` and `files()` stay empty. A single node takes a `str`, a
`multiple` one a `list[str]`, and an optional file takes `null` for its off
state. Nothing in the browser checks that bytes stand behind the reference — an
expired one shows fine and fails when the host resolves it, which is correct
because the form and the storage are different layers. On the wire a file is a
`str` (a `list[str]` when `multiple`), so nothing about the transport or
`decode()` changes. See
[Values completed outside the browser](javascript.md#values-completed-outside-the-browser).

Invariants:

- `extensions` is an array of lowercase, dot-prefixed extensions (`".pdf"`) with
  no repeats, possibly empty. Empty means any file; the list maps to the input's
  `accept` attribute. The only check ever applied — in the widget and in the core
  — is `value.lower().endswith(ext)`: a filter for honest mistakes, never a check
  that the reference resolves to bytes. The widget mints the reference with the
  matched extension, so it passes that same filter downstream.
- A `file` node composes like any other: it is legal wherever a node is, so a
  `list` whose item is a `file`, an `optional` over one, a `choice` branch and an
  `object` field all work, at any depth. `multiple` (from a bare `list[File]`) is
  a dedicated representation for the one shape users expect it for, not a rule
  about the others.
- `multiple` (from `list[File]`) makes `value()` an array — one reference per
  file, minted from a single selection. `minFiles`/`maxFiles` are file-count
  bounds (`minMessage`/`maxMessage` their `{value}` templates); both must be
  `null` on a single file node (`minFiles ≤ maxFiles` when present).
- `invalidMessage` is plain status text with no placeholder, shown only when the
  browser lets through a file whose extension is not accepted, so no reference is
  minted. `currentLabel` (one `{value}`, the existing reference, compacted to its
  file name or to 32 trailing characters for display only) and
  `currentReplaceLabel` drive the current-file display `setValue()` opens;
  `currentRestoreLabel` labels the ↺ that undoes a replace, and
  `currentRemoveLabel` the ✕ on each chosen-file card.
A field declaring an existing file, single and multiple:

```json
{
  "name": "document",
  "label": "Document",
  "description": null,
  "optional": false,
  "enabled": true,
  "hasDefault": true,
  "default": "stored/document.pdf",
  "node": {
    "kind": "file",
    "options": {
      "extensions": [".pdf"],
      "invalidMessage": "Not an accepted file type",
      "multiple": false,
      "minFiles": null,
      "maxFiles": null,
      "minSize": null,
      "maxSize": null,
      "minMessage": "Add at least {value} files",
      "maxMessage": "Keep at most {value} files",
      "minSizeMessage": "File is too small; minimum {value}",
      "maxSizeMessage": "File is too large; maximum {value}",
      "currentLabel": "Current file: {value}",
      "currentRemoveLabel": "Remove current file",
      "currentReplaceLabel": "Replace file",
      "currentRestoreLabel": "Restore current file"
    }
  }
}
```

```json
{
  "name": "documents",
  "label": "Documents",
  "description": null,
  "optional": false,
  "enabled": true,
  "hasDefault": true,
  "default": ["stored/one.pdf", "stored/two.pdf"],
  "node": {
    "kind": "file",
    "options": {
      "extensions": [".pdf"],
      "invalidMessage": "Not an accepted file type",
      "multiple": true,
      "minFiles": null,
      "maxFiles": null,
      "minSize": null,
      "maxSize": null,
      "minMessage": "Add at least {value} files",
      "maxMessage": "Keep at most {value} files",
      "minSizeMessage": "File is too small; minimum {value}",
      "maxSizeMessage": "File is too large; maximum {value}",
      "currentLabel": "Current file: {value}",
      "currentRemoveLabel": "Remove current file",
      "currentReplaceLabel": "Replace file",
      "currentRestoreLabel": "Restore current file"
    }
  }
}
```

Invariants (continued):

- A file **default** is checked for shape at `<path>.default`: a `str` for a
  single node and an array of `str` for a `multiple` one — the wrong arity is
  rejected either way — each reference non-empty and passing the same
  `endswith` extension filter, and a multiple default within `minFiles` and
  `maxFiles`. An optional file may default to `null`, which is its off state.
  The plan checks the shape; `FileWidget.setValue()` owns the semantics and is
  what actually applies the value.
- On the wire a file is a JSON string with option id `"str"` (it is a `Str`), so
  it shares the string transport with `str`, `date`, `time` and `enum`. A union
  of a plain `str` and a file is **inconstructible**: both branches have option
  id `"str"`, which the core rejects at compile time as duplicate option types.

## List nodes

Required: `kind`, `addLabel`, `removeLabel`, `minItems`, `maxItems`,
`minMessage`, `maxMessage`, `item`.

```json
{
  "kind": "list",
  "addLabel": "Add",
  "removeLabel": "Remove",
  "minItems": 1,
  "maxItems": 3,
  "minMessage": "Add at least {value} items",
  "maxMessage": "Keep at most {value} items",
  "item": {
    "kind": "str",
    "options": {
      "minLength": null,
      "maxLength": null,
      "pattern": null,
      "patternMessage": "Invalid format",
      "minMessage": "Must contain at least {value} characters",
      "maxMessage": "Must contain at most {value} characters",
      "placeholder": null,
      "password": false,
      "rows": null,
      "choices": null
    }
  }
}
```

Invariants:

- `minItems` must not exceed `maxItems`.
- Both limits are non-negative safe integers, or `null`.

`minItems` and `maxItems` constrain the value; they never create rows.

## Object nodes

Required: `kind`, `fields`. Each field carries the full field shape.

```json
{
  "kind": "object",
  "fields": [
    {
      "name": "street",
      "label": "street",
      "description": null,
      "optional": false,
      "enabled": true,
      "hasDefault": false,
      "node": {
        "kind": "str",
        "options": {
          "minLength": null,
          "maxLength": null,
          "pattern": null,
          "patternMessage": "Invalid format",
          "minMessage": "Must contain at least {value} characters",
          "maxMessage": "Must contain at most {value} characters",
          "placeholder": null,
          "password": false,
          "rows": null,
          "choices": null
        }
      }
    },
    {
      "name": "city",
      "label": "city",
      "description": null,
      "optional": false,
      "enabled": true,
      "hasDefault": false,
      "node": {
        "kind": "str",
        "options": {
          "minLength": null,
          "maxLength": null,
          "pattern": null,
          "patternMessage": "Invalid format",
          "minMessage": "Must contain at least {value} characters",
          "maxMessage": "Must contain at most {value} characters",
          "placeholder": null,
          "password": false,
          "rows": null,
          "choices": null
        }
      }
    }
  ]
}
```

`fields` must not be empty.

## Choice nodes

Required: `kind`, `previousLabel`, `nextLabel`, `positionLabel`, `branches`.

```json
{
  "kind": "choice",
  "previousLabel": "Previous mode",
  "nextLabel": "Next mode",
  "positionLabel": "Mode {current} of {total}",
  "branches": [
    {
      "value": "str",
      "mode": "plain",
      "node": {
        "kind": "str",
        "options": {
          "minLength": null,
          "maxLength": null,
          "pattern": null,
          "patternMessage": "Invalid format",
          "minMessage": "Must contain at least {value} characters",
          "maxMessage": "Must contain at most {value} characters",
          "placeholder": null,
          "password": false,
          "rows": null,
          "choices": null
        }
      }
    },
    {
      "value": "int",
      "mode": "plain",
      "node": {
        "kind": "int",
        "options": {
          "min": null,
          "max": null,
          "multipleOf": null,
          "step": null,
          "slider": false,
          "showValue": false,
          "placeholder": null,
          "choices": null,
          "safeMessage": "Must be a safe integer",
          "invalidMessage": "Enter a valid integer",
          "minMessage": "Must be at least {value}",
          "maxMessage": "Must be at most {value}",
          "multipleOfMessage": "Must be a multiple of {value}",
          "increaseLabel": "Increase",
          "decreaseLabel": "Decrease"
        }
      }
    }
  ]
}
```

Every branch carries exactly `value`, `mode` and `node`; none is omitted, and
no other property is allowed. A branch has no `label`: the mode navigator
identifies branches by position (`Mode {current} of {total}`), never by a
configurable label.

`value` is a non-empty transport identifier string. It is unique within the
choice node, never shown to the user, and used for transport and branch
restoration. Branch identifiers are always strings compared by direct string
equality — object identifiers and canonical object serialization are not
supported — and uniqueness within a node is enforced with a `Set`.

The choice node also carries the mode-navigator strings, always present like
every other configurable text:

| Property        | Default                     |
| --------------- | --------------------------- |
| `previousLabel` | `"Previous mode"`           |
| `nextLabel`     | `"Next mode"`               |
| `positionLabel` | `"Mode {current} of {total}"` |

Invariants:

- A `choice` node contains at least two branches.
- Two branches must not share the same `value`.
- `mode` must be `plain`, `inline` or `wrapped`.
- `inline` transport is only valid on an object branch: it spreads the branch
  value into an object next to `$type`, so `node.kind` must be `"object"`. An
  object branch may still legitimately use `plain` when its transport identity
  is unambiguous.
- `positionLabel` contains exactly one `{current}` and one `{total}`;
  `previousLabel` and `nextLabel` are non-empty and contain no placeholders.

There is one rule for how many branches a `choice` may hold:

```text
one branch      -> use the branch node directly
two or more     -> use kind: "choice"
```

A single-branch `choice` is rejected rather than unwrapped, so a plan means
exactly one thing.

### The branch id is transport identity, not visible text

`value` is `Shape.option_id()` from the core when the plan comes from Python;
the browser never rebuilds it. It is the branch's identity — the discriminator
`form.read()` uses, the routing key `pytypehint` expects, the key for restoring
defaults — never shown to the user, who sees only numbered modes. Uniqueness is
global to the node: two branches may share a `mode`, never a `value`.

## Optional nodes

Required: `kind`, `label`, `enabled`, `node`.

```json
{
  "kind": "optional",
  "label": "Item",
  "enabled": true,
  "node": {
    "kind": "str",
    "options": {
      "minLength": null,
      "maxLength": null,
      "pattern": null,
      "patternMessage": "Invalid format",
      "minMessage": "Must contain at least {value} characters",
      "maxMessage": "Must contain at most {value} characters",
      "placeholder": null,
      "password": false,
      "rows": null,
      "choices": null
    }
  }
}
```

Only list items use this node, and this is enforced: an `optional` node in any
other position — a top-level field node, a direct object field node, a choice
branch, or wrapping another `optional` — is rejected during normalization with

```text
plan.fields[0].node: optional nodes are only valid as list items
```

An optional field carries its own `optional` flag instead.

## Defaults and initial values

A default initializes the whole widget tree: scalars, optionals, lists,
choices and nested objects.

A plan default is producer configuration, not temporary user input, so it is
validated against the **complete** normalized node — both structurally
compatible and constraint-valid, not merely shape-compatible:

| Node       | Default value                                             |
| ---------- | --------------------------------------------------------- |
| `str`      | a string satisfying `minLength`, `maxLength`, `pattern`, and one of `choices` when declared |
| `int`      | a safe integer satisfying `min`, `max`, `multipleOf`, one of `choices` when declared, and the slider `Step` grid — `max` included — on a slider node |
| `float`    | a finite number satisfying `min`, `max` with their exclusivity, and one of `choices` when declared |
| `date`     | a canonical ISO date string (`YYYY-MM-DD`) satisfying `min`, `max`, and one of `choices` when declared |
| `time`     | a canonical ISO time string (`HH:MM:SS`) satisfying `min`, `max` with their exclusivity, and one of `choices` when declared |
| `list`     | an array respecting `minItems` and `maxItems`, each item valid against the item node |
| `object`   | an object whose keys are declared field names, each value valid against its field |
| `choice`   | `{"branch": index, "value": ...}`, the value valid against the branch node |
| `optional` | `null`, or a value for the wrapped node                    |

For a `choice`, the first declared branch accepted by the core is selected.

This is stricter than `form.read()`, which reports live user values that may be
representable while still invalid. A default that breaks a constraint fails
`checkPlan()` before any widget is built:

```text
plan.fields[0].default: is below min 10
plan.fields[0].default: is not a multiple of 5
plan.fields[0].default: is shorter than minLength 3
plan.fields[0].default: is not on the slider grid stepping by 5 from 0
```

## Union transport

`mode` decides how a branch value travels back, per branch:

- `plain`: the branch is the only one with its input type, so the value
  travels as it is.
- `inline`: several object branches share the input type, so `$type` goes
  inside the dictionary next to the fields.
- `wrapped`: several non-object branches share the input type, so the value
  moves to `$value` next to `$type`.

```javascript
// plain
"hello"

// inline
{"$type": "Shirt", "size": "M"}

// wrapped
{"$type": "str", "$value": "hello"}
```

A lone object branch never carries `$type`.

Branches are grouped by the **JSON type** a value arrives as, not by Python
type. Two groups share a wire type today: a `3` and a `3.0` are the same JSON
number, so `int` and `float` collide; and `str`, `date` and `time` all travel as
a JSON string (date and time as ISO text), so any union mixing two of them
collides. Every branch in a colliding group travels `wrapped`, naming itself
with `$type` (`"int"`/`"float"`, or `"str"`/`"date"`/`"time"` — the core's
`option_id()`), so the browser can round-trip the distinction JSON would lose:

```javascript
// int | float, the float branch
{"$type": "float", "$value": 3}

// str | date, the date branch
{"$type": "date", "$value": "2026-07-22"}

// str | date, the str branch
{"$type": "str", "$value": "2026-07-22"}
```

`str | int` is unaffected: a string and a number are distinct JSON types, so
those branches stay `plain`. The wrapper a colliding group produces is **not** a
web dialect: it is the core's own portable value format, the same one
`Signature.to_dict()` / `Struct.to_dict()` write and `schema.decode()` reads,
down to the `option_id()` names it puts in `$type`. `plan_of()` computes the mode
per branch because the core does not publish that rule as public API, not because
the two sides disagree about what the wrapper means.

[`decode()`](python.md#decode) therefore consumes nothing itself: it hands the
transport object to `schema.decode()`, which turns `$type` into the real type
distinction — restoring the `date`/`time` branch's ISO string as an object,
keeping the `str` branch a string — before `schema.build()`. The reading goes by
the shape at the path or by an explicit `$type`, **never by inspecting the
string**: a `str` branch carrying `"2026-07-22"` stays a string.

The transport object is produced by `form.read()`, which is always callable:
it does not throw because the form is incomplete, and while `isReady()` is
false it may contain incomplete values. That output is meant for inspection;
callers should require `isReady()` before submitting to a strict consumer. The
exact value each incomplete widget reports is tabulated in the
[JavaScript API](javascript.md#reading-an-incomplete-form).

## Validation

```text
structural validation and normalization
    -> semantic validation of the normalized plan
    -> form construction
```

The structural pass runs on the plan as received: the types of the properties
that are present, required properties, unknown properties, a valid `kind`, a
valid `mode`, non-empty field names, `optional` nodes only in list-item
position, `optional` / `enabled` field coherence, and the `hasDefault` /
`default` pair. A property that is allowed to be missing is never an error.

The semantic pass runs on the normalized plan, where every option holds a
real value. It enforces:

- `minLength` does not exceed `maxLength`;
- `min` does not exceed `max`;
- a float `min`/`max` leave a representable value (empty when `min > max`, or
  `min == max` with either side exclusive);
- a date `min`/`max` leave a representable value (empty when `min > max`), and a
  time `min`/`max` likewise, empty also when equal with an exclusive side —
  compared lexicographically over the canonical ISO form;
- `minItems` does not exceed `maxItems`;
- field names are unique and non-empty within each scope (form root and each
  nested object);
- object nodes contain at least one field;
- choice nodes contain at least two branches, with unique branch values, and
  `inline` transport only on object branches;
- `optional` nodes appear only as list items;
- choices are non-empty, unique and satisfy their node constraints;
- sliders declare both bounds and can reach a valid multiple (an *ordinary*
  integer range with an unreachable `multipleOf` is rejected by the core when
  it compiles the schema, so `checkPlan` does not re-check it);
- plan defaults are valid against their node — structurally compatible and
  constraint-valid, including scalar ranges, `pattern`, `multipleOf`, `choices`
  and the slider `Step` grid;
- message templates carry exactly the placeholders they are allowed.

`checkPlan(plan)` is the public entry point. It normalizes, validates and
returns the normalized plan. `compileForm()` calls it once and builds from
its result.

Some of these invariants are unreachable from a plan produced by `plan_of()`,
because `pytypehint` makes the invalid state unconstructable in the first
place. They are enforced anyway, for hand-written plans and plans generated by
another backend. The division of responsibility is documented in the
[architecture](architecture.md#who-owns-which-rule).

Errors are `TypeError` and carry a path:

```text
plan.fields[2].node.kind: unknown node kind "tuple"
plan.fields[0].node.options.minLenght: unknown property
plan.fields[0].node.options.choices[1]: is not a multiple of 5
```

Exact error strings are not part of any compatibility guarantee.

## Text is never markup

Every string in a plan — `name`, `label`, `description`, `placeholder`, the
message templates, `addLabel`, `removeLabel`, the mode navigation strings,
closed `choices` and string defaults — is rendered as plain text. The browser
inserts it with `textContent`, `setAttribute` or the control's `value`, never
by parsing markup, so `<b>Name</b>` appears literally and an `<img
onerror=...>` payload executes nothing.

Nothing is stripped or escaped on the way: a plan carries the exact string and
`form.read()` returns the exact string. The guarantee is about how text
reaches the page, not about where the text came from.

## Pattern portability

The core validates with Python's `re`; the browser runs `RegExp`. Only the
subset that behaves identically in both is accepted, and a pattern that
merely compiles in JavaScript is not enough.

Stable guarantees:

- The pattern is compiled with the Unicode `u` flag.
- It is wrapped as `` new RegExp(`^(?:${pattern})$`, "u") ``, reproducing
  `re.fullmatch()`.
- Lengths are measured in Unicode code points.
- Plans never carry flags.
- Patterns outside the supported subset are rejected by `plan_of()`, not at
  render time.

The goal is identical construction and identical matching behaviour, not
maximum feature coverage. The accepted subset is deliberately conservative and
rejects patterns the two engines could in principle both support.

Rejected because Unicode mode would fail to construct the expression:

- an unclosed character class, as in `[abc` or `a[b`;
- a lone `{` that does not open a supported quantifier, as in `a{b}` or `{x}`;
- an unsupported brace quantifier such as `a{,5}`;
- a lone `}` outside a character class, as in `a}`;
- an unescaped `]` outside a character class, as in `a]`;
- a literal `]` as the first member of a class, as in `[]]` or `[^]]`, which
  Python reads as a class containing `]` and Unicode mode reads as an empty
  class followed by a stray bracket.

Rejected because the two engines would match different text:

- escapes whose class depends on Unicode or on the engine: `\d`, `\D`, `\w`,
  `\W`, `\s`, `\S`, `\b`, `\B`, `\A`, `\Z`, `\z`, `\G`;
- Python-only escapes such as `\N{...}` and `\U0001F600`;
- surrogate escapes in the `\uD800`–`\uDFFF` range, because Unicode mode joins
  a surrogate pair into one code point while Python keeps two separate
  characters;
- the unescaped dot, whose line-terminator semantics differ between engines;
- identity escapes that Unicode mode rejects, such as `\a`, `\_`, or `\-`
  outside a character class.

Rejected because JavaScript has no equivalent construct:

- Python named groups and named backreferences, and numeric backreferences;
- atomic groups and possessive quantifiers;
- inline flags, inline comments and conditionals;
- lookbehind.

Escapes are accepted by allow-list: escaped metacharacters, `\n`, `\r`, `\t`,
`\f`, `\v`, and `\xHH` and `\uHHHH` with their full digits and outside the
surrogate range. `\.`, `[.]`, `\]`, `\{` and `\}` remain valid, and `\-` is
valid inside a character class. Supported brace quantifiers are `{n}`, `{n,}`
and `{n,m}`.

This is not a guarantee that the two engines agree on everything else. The
subset may become stricter.

## Compatibility

A plan is a single, fully expanded document by design: a producer emits every
non-conditional property and the validator rejects any omission (`default` is
present exactly when `hasDefault` is true). There is one representation and one
meaning per key, so no widget ever has to interpret an absence. The contract
version is `v: 1`.

The plan contract is public and tested. A breaking plan change increments `v`
(see [Version](#version)), is documented in the release notes, and belongs to a
major release; `v: 1` has one fixed meaning and keeps it.

Every form plan carries a mandatory integer `v` (see [Version](#version));
version `1` is the only one currently supported. A producer targeting this
contract should pin a `pytypehintweb` version range until 1.0.
