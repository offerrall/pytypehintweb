# pytypehintweb

Python schemas in. Portable form plans and browser widgets out.

pytypehintweb turns a [pytypehint](https://offerrall.github.io/pytypehint/)
schema into a self-contained, JSON-serializable form plan, and renders that plan
in the browser with plain JavaScript widgets: no framework, no build step, no
npm. The browser side reads plans, not Python, so hand-written plans and plans
from another backend render the same way.

It is the rendering layer only. Routing, serving, submission and running the
function stay with the host application, or with
[func-to-web](https://offerrall.github.io/func-to-web/), which builds the whole
request cycle on top of it.

```python
from typing import Annotated

from pytypehint import Label, Min
from pytypehintweb import plan_of


def create_user(
    username: Annotated[str, Min(3), Label("Username")],
    age: Annotated[int, Min(0), Label("Age")],
) -> None:
    pass


plan = plan_of(create_user)  # a JSON-ready dict; compileForm(plan) renders it
```

The full documentation is at https://offerrall.github.io/pytypehintweb/.

## Documentation

- [Overview](docs/overview.md): what the library does, where it stops, its features and its stability promise.
- [Getting started](docs/getting-started.md): one complete form, from a Python function to the built result.
- [Plan contract](docs/plan.md): the plan format, every property, default and invariant.
- [Python API](docs/python.md): `plan_of()`, `decode()`, `WebConfig` and how each annotation maps to a node.
- [JavaScript API](docs/javascript.md): `compileForm()`, widgets, reading, accessibility, styling and themes.
- [Architecture](docs/architecture.md): the layers and which layer owns each rule.
- [Limitations](docs/limitations.md): what a plan cannot represent and why.

### Maintaining

- [Testing](docs/testing.md): how to run the suites, what they guarantee, and CI and release.
