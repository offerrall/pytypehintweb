# Getting started

This guide builds one complete form, from a Python function to the object the
core returns:

```text
Python function
    -> plan_of()
    -> JSON response
    -> fetch()
    -> compileForm()
    -> mount widgets
    -> form.read()
    -> POST
    -> decode()
    -> schema.build()
```

Only two of those steps belong to `pytypehintweb`: `plan_of()` on the Python
side and `compileForm()` / `form.read()` in the browser. The JSON response,
the route, the static files, the `fetch` and the `POST` are written by you.

FastAPI is used as the concrete example. Nothing in the library requires it:
any framework that can return JSON and read a JSON body works the same way.
`pytypehintweb` provides no server, no routes and no static-file handler of
its own.

## Installation

```bash
pip install pytypehintweb
```

To run the example below as written:

```bash
pip install "pytypehintweb[demo]"
```

That extra installs FastAPI and Uvicorn, which the bundled demo also uses.

## Generate a plan from Python

```python
from typing import Annotated

from pytypehint import Label, Min, signature_of
from pytypehintweb import plan_of


def create_user(
    username: Annotated[str, Min(3), Label("Username")],
    age: Annotated[int, Min(0), Label("Age")],
) -> None:
    """Create a user account."""


schema = signature_of(create_user)
plan = plan_of(schema)
```

`plan_of()` accepts the function directly as well; compiling the schema once
is useful when the same schema is also needed to build the result later.

It accepts a plain named function, a dataclass type, or an already compiled
`Signature` or `Struct` — not arbitrary callables. See
[accepted inputs](python.md#accepted-inputs) for what is rejected and why.

The plan is a plain dictionary, fully expanded — every non-conditional property
is present with an explicit value (`default` appears exactly when `hasDefault` is
true):

```json
{
  "v": 1,
  "kind": "form",
  "name": "create_user",
  "description": "Create a user account.",
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

There is a single representation now, and the browser never reconstructs an
absence. See the [plan contract](plan.md) for every property and its meaning.

## Serve the browser files

The browser modules ship inside the Python package. `pytypehintweb.STATIC` is
the directory holding `form.js`, its sibling modules and `widgets.css`. The
library exposes the path; serving it is up to the application:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pytypehintweb import STATIC, decode

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/form-plan")
def form_plan():
    return plan


@app.post("/users")
def create(data: dict):
    return repr(schema.build(decode(schema, data)))
```

`decode()` prepares the JSON-parsed body for `schema.build()`: it is the
reverse-pipeline counterpart of `plan_of()`, coercing the values the transport
cannot express by exact type (today, an `int` where the schema wants a `float`)
and leaving everything else untouched. This form has none, so `decode()` returns
the body unchanged; adding it now keeps the backend correct as the schema grows.

Copying the files next to your own assets works just as well; they are plain
ES modules with no build step.

## Fetch and compile the plan

```html
<link rel="stylesheet" href="/static/widgets.css">

<div id="form"></div>
<button id="submit" type="button">Create</button>
<pre id="answer"></pre>

<script type="module">
  import { compileForm } from "/static/form.js";

  const response = await fetch("/form-plan");
  const plan = await response.json();

  const form = compileForm(plan);
</script>
```

`compileForm()` receives an already parsed object. It never fetches and never
parses JSON: obtaining the plan belongs to the application.

## Mount the fields

```javascript
  const host = document.getElementById("form");

  for (const field of form.fields) {
      host.append(field.widget.el);
  }
```

Mounting is explicit. The library builds the elements and hands them over.

## Read and submit values

```javascript
  const submit = document.getElementById("submit");
  const answer = document.getElementById("answer");

  const refresh = () => {
      submit.disabled = !form.isReady();
  };

  const unsubscribe = form.onChange(refresh);

  refresh();

  submit.addEventListener("click", async () => {
      const result = await fetch("/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form.read()),
      });

      answer.textContent = await result.text();
  });
```

`form.read()` returns the transport object described by the plan. The core
validates it and builds the result:

```python
schema.build({"username": "ada", "age": 36})
# {'username': 'ada', 'age': 36}
```

The browser anticipates errors so the form is pleasant to use, but the
authoritative validation stays in `pytypehint`.

## Use a manual plan

Python is optional at render time: `compileForm()` consumes any fully expanded
plan, whether it came from `plan_of()`, a hand-written constant, or another
backend — the compile-and-mount steps above are identical. Authoring one by
hand is covered in the [JavaScript API](javascript.md#manual-plans); `plan_of()`
remains the reliable way to produce the full document.

## Run the demo

```bash
pytypehintweb-demo
```

The demo shows the same pipeline for a catalogue of examples: the model
source, the plan, the mounted form, its live state, the transport
object and the core's answer.

## Next steps

- [Python API](python.md) — everything `plan_of()` reads and rejects.
- [JavaScript API](javascript.md) — `compileForm()`, widgets and styling.
- [Plan contract](plan.md) — the document format and its defaults.
- [Current limitations](limitations.md) — what is not supported yet.
