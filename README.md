# pytypehintweb 1.1.0

[![PyPI version](https://img.shields.io/pypi/v/pytypehintweb.svg)](https://pypi.org/project/pytypehintweb/)
[![Python](https://img.shields.io/pypi/pyversions/pytypehintweb.svg)](https://pypi.org/project/pytypehintweb/)
[![License](https://img.shields.io/pypi/l/pytypehintweb.svg)](LICENSE)

Python schemas in. Portable form plans and browser widgets out.

`pytypehintweb` is a framework-free browser form layer for
[`pytypehint`](https://github.com/offerrall/pytypehint). It converts compiled
Python type schemas into self-contained, JSON-serializable form plans and
renders them with plain JavaScript widgets. The browser runtime also consumes
hand-written plans or plans from another backend, so Python is not required at
render time. Everything around the form — routing, static-file delivery,
authentication, submission, function execution — belongs to the host
application. (For the whole request/response cycle instead of the rendering
layer, see [FuncToWeb](https://github.com/offerrall/FuncToWeb).)

The public API — `plan_of()`, `decode()`, `WebConfig`, `STATIC` and the plan's
own `v: 1` contract — is settled, and a breaking change to any of them belongs
to a major release. Internals carry no such promise: 1.1.0 replaced most of
`decode()` with a call into the core, and that kind of change is expected.

## Features

- Self-contained, JSON-serializable plans from plain functions, dataclass types
  or compiled `Signature`/`Struct` schemas — and hand-written plans need no
  Python.
- Framework-free browser runtime (plain HTML, CSS and JS modules), with widgets
  usable directly or from a plan; browser files ship inside the Python package
  under `pytypehintweb.STATIC`.
- Optional stylesheet scoped to a `.pth-root` container, with a light/dark theme
  that follows the system or is forced with `data-pth-theme` — pure CSS, no
  theme JavaScript and no flash. Its icons are plain `.svg` files served beside
  it, so no `img-src data:` is needed.
- `str`, `int`, `float`, `date`, `time`, `bool` and `enum` composing through lists,
  optional fields, unions and nested dataclasses, with constraints, static choices,
  integer sliders, and configurable validation messages and labels.
- `file` fields (single, optional or `list[File]`, and inside dataclasses) that
  mint an upload reference the host redeems through its own channel, and that
  accept an existing reference as a plan default or through `setValue()`.
- Centralized plan normalization and validation before any widget is built, and
  `plain` / `inline` / `wrapped` union transport.
- Plan text is always rendered as text, never parsed as markup.

## Installation

```bash
pip install pytypehintweb            # library
pip install "pytypehintweb[demo]"    # + the local demo (pytypehintweb-demo)
```

```bash
# Demo with all widgets, served by a local HTTP server on port 8000:
pytypehintweb-demo
```

There is no npm package: the browser modules live under `pytypehintweb.STATIC`
and can be served by any static-file mount.

## Quick start

```python
from typing import Annotated

from pytypehint import Label, Min
from pytypehintweb import plan_of


def create_user(
    username: Annotated[str, Min(3), Label("Username")],
    age: Annotated[int, Min(0), Label("Age")],
) -> None:
    pass


plan = plan_of(create_user)
```

`plan_of()` returns ordinary Python dictionaries and lists — a single, fully
expanded, self-contained document where every non-conditional property is present
with an explicit value (`default` appears exactly when `hasDefault` is true),
carrying a top-level `"v": 1`:

```json
{
  "v": 1,
  "kind": "form",
  "name": "create_user",
  "description": null,
  "fields": [
    {
      "name": "username",
      "label": "Username",
      "description": null,
      "optional": false,
      "enabled": true,
      "hasDefault": false,
      "node": {
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
    },
    {
      "name": "age",
      "label": "Age",
      "description": null,
      "optional": false,
      "enabled": true,
      "hasDefault": false,
      "node": {
        "kind": "int",
        "options": {
          "min": 0,
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

Transporting that document to the browser and compiling it with `compileForm()`
is walked through end to end in [Getting started](docs/getting-started.md).

## Documentation

- [Getting started](docs/getting-started.md) — the end-to-end tutorial.
- [Plan contract](docs/plan.md) — the plan format, every property and invariant.
- [Python API](docs/python.md) — `plan_of()`, `WebConfig`, annotation mappings.
- [JavaScript API](docs/javascript.md) — `compileForm()`, widgets, reading,
  accessibility, styling and themes.
- [Architecture](docs/architecture.md) — layers and which layer owns each rule.
- [Testing](docs/testing.md) — how to run the suites and what they guarantee.
- [Current limitations](docs/limitations.md).
