# Python API

The Python side of `pytypehintweb` is an adapter. It reads a compiled
`pytypehint` schema and produces a fully expanded plan. It renders nothing and
it validates no user input.

See the [plan contract](plan.md) for the shape of the produced document, the
[architecture](architecture.md) for where this layer sits, and
[getting started](getting-started.md) for a complete end-to-end example.

This module renders nothing, serves nothing and calls nothing. It reads a
schema and returns a dictionary; moving that dictionary to the browser, and
moving the resulting transport object back, is the host application's job.

The final validation and the construction of the resulting objects stay in
`pytypehint`: an application that receives `form.read()` passes it to
`Signature.build()` or `Struct.build()`.

## Public API

Everything the package exports from `pytypehintweb`:

| Name | Kind | Purpose |
| --- | --- | --- |
| `plan_of` | function | compiles a schema into a fully expanded plan |
| `decode` | function | prepares a JSON-parsed transport object for `schema.build()` |
| `WebConfig` | dataclass | the configurable texts of the web layer |
| `STATIC` | `Path` | the directory holding the browser runtime files |
| `PLAIN`, `INLINE`, `WRAPPED` | `str` | the three union transport modes |
| `__version__` | `str` | the installed version |

Anything not listed here is an implementation detail and may change without
notice.

## `plan_of()`

```python
plan_of(obj, *, config: WebConfig | None = None) -> dict
```

Returns a plain dictionary of plain data: dictionaries, lists, strings,
integers, booleans and `None`. It is not a JSON string, and nothing in it
references core classes.

`config` must be a `WebConfig` instance or `None`. The check is
`type(config) is WebConfig`: no subclasses, no coercion. `False`, `0`, `""`
and `{}` are errors, not shorthands for the factory configuration.

## Accepted inputs

`plan_of()` accepts:

- a plain named function accepted by `pytypehint.signature_of()`;
- a dataclass type accepted by `pytypehint.struct_of()`;
- an already compiled `Signature`;
- an already compiled `Struct`.

| Input | Result |
| --- | --- |
| plain named function | compiled with `signature_of()`; the form name is the function name and the docstring becomes the form description |
| dataclass type | compiled with `struct_of()`; the form name is the class name and the description is absent |
| compiled `Signature` | used directly |
| compiled `Struct` | used directly |

It does not accept arbitrary callables. Lambdas, bound methods,
`functools.partial` objects and objects implementing `__call__` are rejected.
Wrap such behaviour in a plain named function before compiling it.

Passing an already compiled schema avoids recompiling the original function or
dataclass, which is useful when the same schema is needed twice — once to
build the plan and once to build the submitted values:

```python
from pytypehint import signature_of, struct_of
from pytypehintweb import plan_of

schema = signature_of(create_user)

plan = plan_of(schema)
result = schema.build(transport)
```

Both forms produce the same document:

```python
plan_of(create_user) == plan_of(signature_of(create_user))
plan_of(User) == plan_of(struct_of(User))
```

### Rejected inputs

A dataclass *instance* is rejected, because the plan describes a type, not a
value:

```python
plan_of(User(name="ada"))
# TypeError: expected a dataclass type, got an instance of User
```

These are rejected too. The error usually comes from the core, which explains
the specific problem:

| Input | Why |
| --- | --- |
| `lambda value: value` | lambdas have no usable name |
| `functools.partial(fn, x=1)` | not a plain function |
| `instance.method` | bound methods are not plain functions |
| `Class.classmethod` | bound to the class, not a plain function |
| `Class.method` | the leading `self` parameter is not a form field |
| an object with `__call__` | not a plain function |
| an ordinary class | not a plain function |
| anything else | not a supported category |

A `@staticmethod` accessed through its class *is* a plain function, so it is
accepted.

Anything the adapter cannot classify raises:

```text
TypeError: expected a plain function, a dataclass type, a Signature or a
Struct, got ...
```

### Function restrictions

Function inputs inherit the restrictions of `pytypehint.signature_of()`. Each
parameter becomes a form field, so a parameter that cannot be described as one
is refused:

| Signature | Result |
| --- | --- |
| `def f(value: str)` | accepted |
| `def f(value: str = "x")` | accepted; the default initialises the field |
| `def f(*, value: str)` | accepted; keyword-only is fine |
| `def f(value)` | rejected: `missing type hint` |
| `def f(value: str, /)` | rejected: positional-only parameters are not supported |
| `def f(*args: str)` | rejected: variadic parameters are not supported |
| `def f(**kwargs: str)` | rejected: variadic parameters are not supported |
| `def f(self, value: str)` | rejected: looks like an unbound method |

To build a form for something that is not a plain function, write one:

```python
service = Service()


def run(query: str) -> Result:
    return service.search(query)


plan = plan_of(run)
```

`plan_of()` reads the signature of `run`; it never calls it. Executing the
function is the host application's job.

## Strings

A `Str` shape maps to a `str` node. The metadata that reaches the plan:

| Annotation | Plan option |
| --- | --- |
| `Min` | `minLength` |
| `Max` | `maxLength` |
| `Pattern` | `pattern`, plus `patternMessage` when the annotation carries a message |
| `Placeholder` | `placeholder` |
| `IsPassword` | `password` |
| `Rows` | `rows` |
| `Choices` | `choices` |
| `Literal[str]` | `choices` |
| `Label` | the field `label` |
| `Description` | the field `description` |

`minLength` and `maxLength` count Unicode code points, matching Python's
`len(str)`. The browser measures the same way.

`Rows`, `IsPassword` and `Choices` ask for three different controls. Any two
of them together raise `TypeError` rather than letting the adapter pick one.
`Placeholder` is likewise rejected next to `Choices`: a closed select has no
empty prompt, so there is nothing for the placeholder to fill.

A `Choices` field always represents one of its values. It opens on the explicit
default when there is one, otherwise on the first choice, so it is ready from
the first render with no "choose one" step.

### Files

`IsPathFile` on a `str` turns the field into a **file node** (`kind: "file"`)
rather than a text box. Its value is a reference string the browser widget
**generates locally** the moment the user picks a file — a UUID plus the file's
lowercased extension. The library never interprets it beyond the **extension**:
a lenient `value.lower().endswith(ext)` filter over the declared list, in the
widget and in the core alike — a guard against honest mistakes, never a check
that the reference resolves to bytes. The core never sees bytes, and nothing
about the transport or `decode()` changes: a file field is a `str` on the wire.

| Annotation | Plan option |
| --- | --- |
| `IsPathFile(extensions=...)` | `extensions` — lowercase, dotted, possibly empty (any file), mapped to the input's `accept` |
| `list[Annotated[str, IsPathFile(...)]]` | one file node with `multiple: true`; the list's `Min`/`Max` become `minFiles`/`maxFiles` |

**`list[File]` is one `multiple` file node**, not a list of file widgets: a single
input that takes several files at once, minting one reference per file, with the
list's `Min`/`Max` as file-count bounds. A file anywhere else inside a list — an
optional item, a union, a nested list, a dataclass field — raises `TypeError`
("not supported yet"), deferred until a real case asks for it.

A file field carries **no plan default**: a plan is a static artefact (cacheable,
serialisable, hand-written) and a frozen reference in it is a promise nobody
renews, so `plan_of()` rejects a default over `IsPathFile` while compiling —
single or `list[File]` (even an empty list), and including the `None` a
switched-off optional would use, whose off state is an `OptionalToggle` instead.

**A struct with an internal path round-trips through an edit form.** Create and
edit are the same form: a host builds it from a `Struct` (`struct_of(User)`),
`setValue()`s each field from an existing record — including the file field, whose
string is an *existing* reference shown as the current file — the user edits what
they edit, and `schema.build(decode(schema, form.read()))` returns the whole
`User`. An untouched avatar comes back byte-identical to the reference it went in
as; a replaced one as the fresh reference the new local choice minted; no bytes
move for the files left alone. That is the counterpart to the rejected plan
default: the current file is runtime truth the host sets fresh at mount, not a
promise frozen into a static plan.

The reference is a local promise, not proof of storage. That a file's bytes are
actually stored is the host's, with no net from the library: if it mints a
reference and never uploads the bytes, `build()` accepts a string that points at
nothing. FuncToWeb (or any wrapper) must ensure it internally if it cares; see
[Values completed outside the browser](javascript.md#values-completed-outside-the-browser).

Only a bare `IsPathFile` is emitted today. The other `Str` atoms — `Min`, `Max`,
`Pattern`, `Choices`, `IsPassword`, `Rows`, `Placeholder` — describe a text box
and have no meaning on a file control, so any of them alongside `IsPathFile`
raises `TypeError` ("not supported yet"), deferred until a real case asks for it,
exactly as `Float.slider` is. `Label` and `Description` are the field's, not the
`Str`'s, so a labelled file field is fine.

### Patterns

Pattern support is intentionally conservative. The core validates with
Python's `re` and the browser runs `RegExp`; the two are different engines,
so only the subset that behaves identically in both is accepted. A pattern
that merely *compiles* in JavaScript is not enough.

The browser wraps the pattern as `` new RegExp(`^(?:${pattern})$`, "u") ``,
which reproduces `re.fullmatch()`. Plans never carry flags.

Patterns outside the supported subset are rejected during plan generation,
not at render time. The rejected categories are listed in
[the plan contract](plan.md#pattern-portability).

### Types

`pytypehintweb` exports two convenience aliases, importable from the top level:

```python
from pytypehintweb import Color, Email, COLOR_PATTERN, EMAIL_PATTERN
```

They are **not new types**. Each is an `Annotated[str, Pattern(...)]`, so the plan
they produce is an ordinary `str` node — the same node the equivalent hand-written
annotation produces — and nothing in the contract, transport or `decode()` knows
they exist. Each alias does set the pattern's `message`, so the node's
`patternMessage` carries that wording rather than the generic default; it is not
identical to a bare `Pattern(...)` with no message. They exist only to save every
caller from repeating the pattern.

- `Color` is `Annotated[str, Pattern(COLOR_PATTERN, message="Hex color like
  #ff5733")]`, where `COLOR_PATTERN` is `#[0-9a-fA-F]{6}` — a hex colour like
  `#ff5733`. This exact string is also the
  opt-in for the browser's [colour assistant](javascript.md#direct-widget-usage):
  a `StrWidget` whose pattern equals it mounts a picker beside the text field.
- `Email` is `Annotated[str, Pattern(EMAIL_PATTERN, message=...)]`, where
  `EMAIL_PATTERN` is
  `[^@ ]+@[^@ ]+\.[a-z]{2,}` — a run of non-space, non-`@` characters, an `@`,
  another such run, a dot and a suffix of two or more lowercase letters. It is a
  **format filter, not an email validator**: it rejects plenty of RFC-valid
  addresses and accepts plenty of nonsense, exactly the humility
  [limitations](limitations.md#regular-expressions) records for the pattern
  subset. `Email` carries no `Placeholder`, so it composes cleanly with a
  caller's own metadata.

Both compose the usual way — typing flattens the nested `Annotated`, so
`Annotated[Color, Label("Fondo")]` reaches the core as the pattern on the node and
the label on the field.

## Integers

Every integer that reaches a plan is a JavaScript safe integer: bounds,
`multipleOf`, `step`, choices, list lengths and defaults at any depth go
through the same check. If the core accepts a larger one, `plan_of()` fails
and says where. This does not restrict `pytypehint` itself; it only prevents
sending a silently rounded value to the browser.

| Annotation | Plan option |
| --- | --- |
| `Min` | `min` |
| `Max` | `max` |
| `MultipleOf` | `multipleOf` |
| `Step` | `step` |
| `Slider` | `slider`, plus `showValue` |
| `Choices` | `choices` |
| `Literal[int]` | `choices` |

Exclusive bounds are converted to inclusive browser limits: an exclusive
minimum becomes `value + 1` and an exclusive maximum becomes `value - 1`.
When that conversion leaves the safe range, the error reports the original
exclusive bound and the inclusive value it would have needed.

`Step` controls presentation, `MultipleOf` controls validity. They can
coexist: `Step(25)` moves the arrows in steps of 25 but still lets someone
type 37, and `MultipleOf(25)` is what makes that 37 invalid. On an ordinary
number input the `▲`/`▼` arrows step by `step`, else by `multipleOf`, else by
`1`; that is a widget-local increment only — `MultipleOf` is never copied into
the plan's `step`.

`Slider` is another presentation of the same integer and needs both bounds.
`Choices` and `Slider` together are rejected.

For a slider, `Step` decides where the control can land and `MultipleOf`
decides whether the represented integer is valid; `MultipleOf` is not copied
into the slider stride. Usually

```python
Annotated[int, Slider(), Step(5), MultipleOf(5)]
```

is what you want: the slider only stops on multiples of 5. Without the matching
`Step`,

```python
Annotated[int, Slider(), MultipleOf(5)]
```

leaves the default stride of 1, so the slider can visit intermediate positions
that are not multiples of 5 and therefore invalid. The adapter still requires
at least one reachable valid position, but it will not silently align the two
for you.

## Floats

A `Float` shape maps to a `float` node. The metadata that reaches the plan:

| Annotation | Plan option |
| --- | --- |
| `Min` | `min`, plus `minExclusive` |
| `Max` | `max`, plus `maxExclusive` |
| `Step` | `step` |
| `Choices` | `choices` |
| `Placeholder` | `placeholder` |
| `Label` | the field `label` |
| `Description` | the field `description` |

Unlike an integer, a float bound is **not** converted. The core compares a
float directly against its bound and an exclusivity flag (`value <= min` when
exclusive, `value < min` when not), so the adapter emits the bound value
verbatim and carries `minExclusive` / `maxExclusive` beside it. There is no ±1
neighbour, because a float has no next representable step. An empty range —
`min > max`, or `min == max` with either side exclusive — is rejected by the
core when it compiles the schema, so `plan_of()` never re-checks it.

Every finite double is representable in the browser, so there is no "safe float"
check the way there is for integers: `min`, `max`, `choices` and defaults travel
as they are. `Step` is presentation only — the stride of the `▲`/`▼` arrows —
never a validation grid.

`Slider` on a `Float` is **rejected** with `TypeError: Float.slider is not
supported yet`: the `min + k*step` grid a slider needs has no exact float
arithmetic, so a legitimate default could be refused or the control would have
to silently correct a value, and the doctrine forbids both (see
[limitations](limitations.md#float-slider)). `Choices` and `Placeholder`
together are rejected, as for the other scalars: a closed select has no empty
prompt.

The float stepper reuses the integer stepper's accessible labels
(`int_increase_label` / `int_decrease_label`): the arrows do the same job, so
their names do not vary by type. The float-specific texts —
`float_invalid_message`, `float_finite_message`, `float_min_message`,
`float_max_message` — are on [`WebConfig`](#webconfig).

## Dates and times

A `Date` maps to a `date` node and a `Time` to a `time` node, each a native
picker. Both travel as ISO text — a date as `YYYY-MM-DD`, a time as `HH:MM:SS`
(the native control shows seconds) — so the metadata that reaches the plan is
the same for both:

| Annotation | Plan option |
| --- | --- |
| `Min` | `min` (date: plus the ±1-day conversion; time: plus `minExclusive`) |
| `Max` | `max` (date: plus the ±1-day conversion; time: plus `maxExclusive`) |
| `Choices` | `choices` |
| `Placeholder` | `placeholder` |
| `Label` | the field `label` |
| `Description` | the field `description` |

Bounds, choices and defaults are emitted in the **canonical** ISO form
`isoformat()` produces, which is fixed-width, so the browser compares them
lexicographically. A time is always `HH:MM:SS`: the core pins it to whole seconds
and rejects any microsecond, so no sub-second fraction is ever emitted. A date is
always a real calendar date as `YYYY-MM-DD` — it starts as a `datetime.date`, so
an impossible date cannot exist here; the browser enforces the same rule for
hand-written plans and direct widget use.

The one asymmetry is deliberate, and each type copies its own core: **a date
bound is converted like an integer — an exclusive bound becomes the neighbouring
inclusive one by ±1 day, so the node carries no flag — while a time bound is
kept like a float — the core compares it directly, so the node carries
`minExclusive`/`maxExclusive` and no conversion happens.** Neither has a slider,
step or `multiple_of`; `Choices` with `Placeholder` is rejected, as for the
other scalars. The date/time texts — `date_invalid_message`, `date_min_message`,
`date_max_message`, `time_invalid_message`, `time_min_message`,
`time_max_message` — are on [`WebConfig`](#webconfig).

## Booleans

A `bool` maps to a `bool` node, rendered as a native checkbox. It has no
metadata of its own — no bounds, choices, placeholder or slider — so the node's
`options` is an empty object. `Label` and `Description` still apply, as on any
field.

A checkbox always represents a value: unchecked is `false`, checked is `true`.
A `bool` default of `True` or `False` travels certified by the core; `bool |
None` makes the field optional (the toggle expresses `None`, the checkbox never
does). In a union, a `bool` branch carries `option_id()` `"bool"` and travels
`plain` (`true`/`false`), since it never collides with another `bool`.

## Enums

An `EnumShape` maps to an `enum` node, rendered as a select over its members'
names. An enum carries no constraint metadata — the closed set of members *is*
the constraint — so the node's `options` is just `choices` (the member names, in
declaration order), with `placeholder` and `labels` always `null`. `Label` and
`Description` still apply, as on any field. `Flag` enums and empty enums are
rejected by the core, so an `enum` node always has at least one choice.

A member travels as its **name** (`.name`), never its value: a value can be
anything, repeat across aliases, or not serialize, while a name is a stable JSON
string. An enum default travels as the member name, certified by the core, and
`decode()` rebuilds the exact member with `cls[name]`.

**Aliases.** When two members share a value (`A = 1; B = 1`), `B` is an alias of
`A`: `list(cls)` yields only canonical members, so an alias name never appears in
`choices`. If an external producer sends an alias name, `decode()` resolves it
with `cls[name]` — which reads through `__members__` — to the canonical member,
and `build()` accepts it (its type is the enum class).

`Extra` on the core's enum is stored but **not interpreted** by the adapter; the
`labels` slot on the node is where a future `Extra` vocabulary for visible member
labels would land (see [limitations](limitations.md#unsupported-metadata)).

In a union, a member is a JSON string, so an enum shares the string transport
with `str`, `date`, `time` and other enums: every such branch travels `wrapped`,
with the enum's class name (`option_id()`) as its `$type`.

## Lists

List constraints and item constraints are independent: `Min` on the list is
`minItems`, `Min` on the item is the item's own constraint.

- A list with no default starts empty, even when it has a minimum.
- `minItems` does not create rows. The interface never invents values to
  satisfy a constraint; it only reports that the list is not ready and
  refuses to remove below the limit.
- `maxItems` prevents adding above the limit.
- A default materializes exactly its elements and no others.
- Nested lists are supported.
- Union items are supported: `list[A | B]` produces one choice per row.

`list[A] | list[B]` is a different question: the choice covers the whole
list, so rows cannot mix types.

## Optional values

A union containing `None` makes the field optional. Disabling the toggle
means `None`.

The initial toggle state is resolved in Python and travels in the plan:

1. `OptionalToggle` wins when present;
2. otherwise a missing default leaves the field enabled;
3. otherwise the field is enabled when the default is not `None`.

Turning a field off hides its widget without destroying it. Whatever was
typed is still there when it is turned back on.

Inside a list, an optional item becomes an explicit `optional` node wrapping
the item node. An optional field carries its own `optional` flag instead.

## Unions

A union with two or more non-`None` branches becomes a `choice` node. A
single branch is emitted as its own node, with no choice around it.

Each branch carries `Shape.option_id()` from the core as its `value`, and the
adapter assigns each a transport `mode` — `plain`, `inline` or `wrapped` — by
the rules in the [plan contract](plan.md#union-transport). The core compiler
rejects the homonym enums or dataclasses a union's normal path could produce;
`plan_of()` still fails if two branches reach it sharing an option id — defense in
depth, because nothing downstream could tell them apart.

The three mode names are also exported as constants, so that code inspecting
a generated plan does not have to repeat string literals:

```python
from pytypehintweb import PLAIN, plan_of

plan = plan_of(order)
branch = plan["fields"][0]["node"]["branches"][0]

if branch["mode"] == PLAIN:
    ...
```

They are plain strings — `"plain"`, `"inline"` and `"wrapped"` — identical to
the values that appear in the plan, so comparing with `==` is correct and a
plan that has crossed JSON compares the same way.

## Defaults

Defaults come from the compiled schema, not from re-reading the original
dataclass, and they initialize the entire tree: scalars, optionals, lists,
choices and nested objects.

Five states that are easy to confuse:

| Value | Meaning |
| --- | --- |
| `MISSING` | no initial value; the plan emits `hasDefault: false` and omits `default` |
| `None` | an explicit value; the optional starts disabled |
| `""` | an explicit string; the field is not empty |
| `0` | an explicit integer; the field is not empty |
| `[]` | an explicit empty list; no rows are created |

For a union, the plan records which branch the default selected:
`{"branch": index, "value": ...}`. When the value fits more than one branch,
the first declared branch that accepts it wins — the same ordered selection
the core performs. `list[str] | list[int] = []` opens on `list[str]`; with
the branches swapped it opens on `list[int]`. It only fails when no branch
accepts the value at all.

## `decode()`

```python
decode(schema, data) -> dict
```

`decode()` is the reverse counterpart of `plan_of()`: where `plan_of()` turns a
schema into a plan, `decode()` prepares a JSON-parsed transport object for the
schema to build. It takes the compiled schema (a `Signature` or a `Struct`) and
the raw dictionary that came out of the JSON parser, and returns a **new**
dictionary — the input is never mutated. The new root, and any container it
descends into to prepare a value, is freshly built; but a value it passes through
untouched is returned by reference, not deep-copied, so an unconverted nested
object or list may be shared with the input. The guarantee is no mutation and a
fresh root, not a deep clone:

```python
from pytypehintweb import decode

resolved = schema.build(decode(schema, data))
```

It exists because the transport cannot express, by type, everything the core
demands. JSON has no way to tell `3` from `3.0`, so a float typed in the browser
arrives as an `int`; and a date or a time travels as an ISO string where the
core wants a `date`/`time` object. `build()` validates by exact type and would
reject both. Rather than patch this per type at the call site, `decode()` walks
the schema shapes and, guided by the shape at each path, prepares the values the
transport could not carry faithfully.

**What it prepares today:**

| Shape at the path | Transport value | Prepared into |
| --- | --- | --- |
| `Float` | an `int` (`3`) | a `float` (`3.0`) |
| `Date`  | an ISO string (`"2026-07-22"`) | `date.fromisoformat(...)` |
| `Time`  | an ISO string (`"14:30:00"`)   | `time.fromisoformat(...)` |
| `EnumShape` | a member name (`"ACTIVO"`) | the member `cls["ACTIVO"]` |

It converts only where that shape is the single possible reading of the path.
Root fields, nested objects, lists (and nested lists), optionals (a `None`
passes through), and union branches are all covered. Everything else passes
through untouched. A date/time whose string `fromisoformat` cannot parse, or an
enum name that is not a member (`cls[name]` raising `KeyError`), is left intact
for `build()` to reject.

**`decode()` never guesses from a value's content.** It converts a string to a
`date` because the *shape* (or an explicit `$type`) says so, never because the
string "looks like" a date. A `str` field carrying `"2026-07-22"` stays a
string. This is the rule that keeps the conversion honest, and it is inviolable.

`decode()` **prepares, it does not validate.** A value the core will reject —
`"abc"` in a float field, `"not-a-date"` in a date field — passes through
unchanged, and `build()` reports it with its own error. `decode()` never raises
on a value; the error is the core's territory. (It does raise on a schema that
is neither a `Signature` nor a `Struct`: that is a programming error, not a
value.)

### Unions and the wrapper

In a union, the shape alone cannot fix the reading of a bare number or string,
so the transport `$type` does. Two kinds of union collide on the wire: `int |
float` (both a JSON number) and any mix of `str`, `date`, `time` and enums (all a
JSON string). Their branches travel `wrapped`
([plan contract](plan.md#union-transport)): `{"$type": "float", "$value": 3}`,
`{"$type": "date", "$value": "2026-07-22"}`, `{"$type": "str", "$value":
"2026-07-22"}`, `{"$type": "Estado", "$value": "ACTIVO"}`. `decode()` reads
`$type` and consumes the wrapper: the `float` branch coerces `$value`, a
`date`/`time` branch runs `fromisoformat`, an enum branch turns the name into its
member, a `str` branch keeps its string, and each unwraps to the bare value the
core routes by exact Python type. The `$type` is not discarded — it is *answered*: the
ambiguity it named exists only on the wire.

A wrapper the core genuinely needs — `list[str] | list[int]`, where both
branches are the same runtime type — is kept as it is; `decode()` only prepares
what is inside `$value`. The general rule: `decode()` converts where the shape
is the only possible reading of the path, and in a union the `$type` fixes that
reading — the string's content is never consulted.

`decode()` walks the schema through the core's public surface only
(`Struct.fields`, `Field.shape`, `List.item`, `type(shape) is Float`/`Date`/
`Time`/`EnumShape`, `EnumShape.cls`, `option_id()`): it never touches the core
internals.

## `WebConfig`

```python
@dataclass(frozen=True, kw_only=True)
class WebConfig:
    list_add_label: str = "Add"
    list_remove_label: str = "Remove"
    list_item_label: str = "Item"
    str_min_message: str = "Must contain at least {value} characters"
    str_max_message: str = "Must contain at most {value} characters"
    str_pattern_message: str = "Invalid format"
    int_safe_message: str = "Must be a safe integer"
    int_invalid_message: str = "Enter a valid integer"
    int_min_message: str = "Must be at least {value}"
    int_max_message: str = "Must be at most {value}"
    int_multiple_of_message: str = "Must be a multiple of {value}"
    int_increase_label: str = "Increase"
    int_decrease_label: str = "Decrease"
    float_invalid_message: str = "Enter a valid number"
    float_finite_message: str = "Must be a finite number"
    float_min_message: str = "Must be at least {value}"
    float_max_message: str = "Must be at most {value}"
    date_invalid_message: str = "Enter a valid date"
    date_min_message: str = "Must be on or after {value}"
    date_max_message: str = "Must be on or before {value}"
    time_invalid_message: str = "Enter a valid time"
    time_min_message: str = "Must be at or after {value}"
    time_max_message: str = "Must be at or before {value}"
    list_min_message: str = "Add at least {value} items"
    list_max_message: str = "Keep at most {value} items"
    mode_previous_label: str = "Previous mode"
    mode_next_label: str = "Next mode"
    mode_position_label: str = "Mode {current} of {total}"
    file_invalid_message: str = "Not an accepted file type"
    file_min_message: str = "Add at least {value} files"
    file_max_message: str = "Keep at most {value} files"
    file_current_label: str = "Current file: {value}"
    file_current_remove_label: str = "Remove current file"
    file_current_replace_label: str = "Replace file"
    file_current_restore_label: str = "Restore current file"
```

Every visible text the web layer generates is configurable. `WebConfig`
applies to a whole plan, never to individual fields through type hints, and
each `plan_of()` call may use a different one: there is no global state.

Message templates are deliberately minimal. The messages that insert a value
take exactly one `{value}` placeholder and nothing else; the ones that do
not insert a value accept no placeholders at all; literal braces are not
supported. A template that breaks these rules raises `TypeError` when the
`WebConfig` is constructed.

A `Pattern(..., message=...)` beats `str_pattern_message`. The priority is
resolved during plan generation, so a single decided text reaches the
browser.

Structural elements — kinds, transport modes, `$type`, `$value`, property
names — are not configurable, and neither are technical errors: those are
contract violations seen by programmers, not interface text.

Every configured text travels in every plan `plan_of()` emits: the plan is
fully expanded, so a `WebConfig` message or label is written on each node it
applies to, whether or not it differs from the standard text. Each side then
decides whether a given control renders — a slider and a closed choice show no
stepper, so they simply ignore the stepper labels they still carry.

## Errors

`plan_of()` raises `TypeError` at plan-generation time whenever browser
semantics cannot preserve a guarantee the core makes. Nothing is degraded
silently.

It does not independently recreate the core's validation. The layers divide
the work:

```text
pytypehint      core schema semantics
plan_of()       the exact converted browser contract it emits
JavaScript      manual and generated plan input
schema.build()  the values actually submitted
```

A schema that reaches `plan_of()` has already passed the core model, so the
adapter does not restate the core's schema semantics for their own sake. It
verifies the parts of the contract that only become concrete once the plan is
converted for the browser, and rejects:

- JavaScript-unsafe integers, anywhere they appear;
- non-portable regular-expression patterns;
- incompatible control metadata (control combinations asking for different
  widgets);
- duplicate branch identifiers;
- empty nested objects;
- exclusive integer bounds that leave no integer after conversion;
- sliders without both converted bounds;
- sliders with no reachable valid position;
- converted defaults the browser could not represent or validate — including a
  slider default that lands off the `Step` grid.

The full split is in the
[architecture](architecture.md#who-owns-which-rule).

Every message is prefixed with the path of the field that caused it, because
in a composed form knowing *what* failed is useless without knowing *where*:

```text
fields.lines.item
fields.address.postal_code
fields.value[int]
```

The paths follow the plan structure: `.name` for a field, `.item` for a list
item, `[index]` for a default element and `[option_id]` for a union branch.

Exact error strings are not part of any compatibility guarantee.

`plan_of()` rejects unsupported types, incompatible control metadata, unsafe
integers, unportable patterns, ambiguous transport identifiers, empty nested
objects, unreachable or unbounded sliders, converted defaults the browser could
not accept, and an invalid `WebConfig`. See
[current limitations](limitations.md) for the full list.
