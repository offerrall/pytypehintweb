# Overview

`pytypehintweb` sits between a [pytypehint](https://offerrall.github.io/pytypehint/)
schema and a browser. On the Python side, `plan_of()` compiles a function, a
dataclass type or an already compiled `Signature`/`Struct` into a plan: one
self-contained, JSON-serializable document that describes every field, node,
constraint, default, message and transport rule. In the browser, `compileForm()`
turns that plan into widgets, and `form.read()` returns the value to send back.
On the way back, `decode()` prepares the posted value and the core's
`schema.build()` validates it and builds the result.

```text
function/dataclass -> pytypehint schema -> plan_of() -> plan (JSON)
    -> compileForm() -> widgets -> form.read() -> transport object
    -> decode() -> schema.build()
```

The browser runtime reads plans, not Python: a hand-written plan or one produced
by another backend renders the same way. [Getting started](getting-started.md)
walks the whole cycle with a concrete FastAPI host.

## Where the library stops

`pytypehintweb` is a rendering layer, not a web framework. `plan_of()` returns a
dictionary, `compileForm()` returns widgets and `form.read()` returns a value.
There is no web server, no routing, no static-file handler, no authentication, no
session handling and no way to invoke a Python function from the browser: moving
the plan to the page, mounting the widgets, posting the value and running the
function all belong to the host application. The bundled demo is such a host,
written on top of the library to show the pipeline end to end; its routes and
file handler are not part of the public API.

For the complete request/response cycle (routing, file serving and calling the
function itself) there is [func-to-web](https://offerrall.github.io/func-to-web/),
which uses this package as its rendering core. The dependency runs in that
direction only.

## Features

- **Self-contained plans.** A plan is fully expanded: every property is present
  with an explicit value, so no widget interprets an absence. See the
  [plan contract](plan.md).
- **Framework-free browser runtime.** Plain ES modules and an optional
  stylesheet, with no dependencies and no build step, shipped inside the Python
  package under `pytypehintweb.STATIC`. The widgets can be built from a plan or
  used directly. See the [JavaScript API](javascript.md).
- **Types.** `str`, `int`, `float`, `date`, `time`, `bool` and `enum`, composing
  through lists, optional fields, unions and nested dataclasses, with
  constraints, static choices, integer sliders, and configurable validation
  messages and labels. See the [Python API](python.md).
- **File fields.** Single, optional, `list[File]` and nested inside dataclasses.
  The widget mints an upload reference that the host redeems through its own
  channel, and an existing reference can be planted as a default or through
  `setValue()`. See
  [Values completed outside the browser](javascript.md#values-completed-outside-the-browser).
- **Checked before rendering.** Plan normalization and validation run before any
  widget is built, and unions travel `plain`, `inline` or `wrapped` as the
  contract decides.
- **Themes without JavaScript.** The stylesheet is scoped to a `.pth-root`
  container, follows the system's light or dark preference or is forced with
  `data-pth-theme`, and loads its icons as plain `.svg` files, so the page needs
  no `img-src data:`. See [Styling](javascript.md#styling).
- **Text is never markup.** Plan strings are always inserted as text.

## Stability

The public API is `plan_of()`, `decode()`, `WebConfig` and `STATIC` (the full
list is in [Public API](python.md#public-api)), together with the plan contract
`v: 1`. A breaking change to any of them belongs to a major release; `v: 1` has
one fixed meaning and keeps it (see [Compatibility](plan.md#compatibility)).
Internals carry no such promise and change between releases.
