# JavaScript API

The browser runtime is a set of ES modules with no dependencies and no build
step. It renders forms from a plan and reports what the user represents; it
never talks to a server on its own.

These modules perform no request, mount nothing into the page and submit
nothing. Fetching the plan, appending the widgets and posting the transport
object are all the application's decisions.

See the [plan contract](plan.md) for the document these modules consume.

## Browser modules

The modules ship inside the Python package, in the directory exposed as
`pytypehintweb.STATIC`:

| Module         | Purpose                                                    |
| -------------- | ---------------------------------------------------------- |
| `form.js`      | compiles a plan into widgets and reads the transport object |
| `contract.js`  | `checkPlan()`: normalization plus semantic validation       |
| `normalize.js` | structural validation and normalization of a plan           |
| `defaults.js`  | the official runtime defaults and the known property names  |
| `slider.js`    | shared slider position arithmetic (`firstSliderValue`, `sliderReaches`) |
| `iso.js`       | shared canonical-date validation (`isValidIsoDate`)         |
| `fields.js`    | `Widget`, `Field`, `GroupWidget`, `ListWidget`, `ChoiceWidget` |
| `inputs.js`    | `StrWidget`, `IntWidget`, `FloatWidget`, `DateWidget`, `TimeWidget`, `BoolWidget`, `FileWidget`, `StrChoiceWidget`, `IntChoiceWidget`, `FloatChoiceWidget` |
| `widgets.css`  | the optional stylesheet                                     |

Most applications only import `form.js`. Applications that build controls by
hand import `fields.js` and `inputs.js`.

`checkPlan()` and `normalizePlan()` are exported so that a producer of plans
can validate one without building a form:

```javascript
import { checkPlan } from "./contract.js";

const normalized = checkPlan(plan);   // throws TypeError on an invalid plan
```

`compileForm()` already calls `checkPlan()` internally, so an application that
only renders forms never needs it. Everything else these two modules export —
the default tables, the known property names, the internal helpers — is an
implementation detail.

## Loading and size

The runtime is plain ES modules with no build step: a page loads exactly the
files reachable from the entry point it imports, and nothing else.

- `import { compileForm } from "./form.js"` pulls the whole runtime, because
  compilation is synchronous and one plan can reach every node kind: `form.js`
  imports `contract.js`, `normalize.js`, `fields.js`, `inputs.js`, `slider.js`,
  `iso.js` and `defaults.js`.
- `import { StrWidget } from "./inputs.js"` — building controls by hand — pulls
  `inputs.js`, `fields.js`, `defaults.js`, `slider.js`, `iso.js` and, through
  `fields.js`, `normalize.js` (for its `putKey` helper). Two of those are tiny
  dependency-free leaves shared with the plan validator — slider positions
  (`slider.js`) and canonical-date validation (`iso.js`) — so the two sides
  cannot drift. The plan compiler and the semantic validator (`form.js`,
  `contract.js`) never load, so a direct-widget page still ships noticeably less
  code than one that compiles plans.

Nothing here is asynchronous: there is no code splitting and `compileForm()`
stays synchronous. The split is simply what the import graph already gives.

The shipped files are readable, unminified ES modules and are served as they
are. They carry no comments: with no build step there is nothing to strip them,
so every explanatory line would be downloaded by every page. The reasoning
behind the runtime lives in this documentation instead — which is also where a
reader looks for it. A production host is free to serve them with gzip or
Brotli, run them through its own minifier, or bundle them with the rest of its
application. The library itself adds no npm package, bundler or build
dependency, and the exact byte sizes are an implementation detail, not part of
the contract.

## `compileForm()`

```javascript
compileForm(plan, { prefix = "pth" } = {})
```

It:

1. receives a fully expanded plan object;
2. normalizes it once, through `checkPlan()`;
3. validates the normalized plan;
4. builds the fields and widgets;
5. returns the orchestration object.

It does **not**:

- fetch anything;
- parse JSON;
- look for a plan inside the DOM;
- mount the widgets;
- submit data.

`prefix` seeds the generated element ids used to link labels to their
controls.

The returned object:

```javascript
{
    name,          // the plan name
    description,   // the description, or null
    fields,        // [{ name, widget, read }]
    isReady(),
    hasError(),
    onChange(),
    read(),
    showErrors(),
}
```

An invalid plan raises a `TypeError` before any widget exists.

Every form plan carries a top-level `"v": 1`; a plan whose version is missing
or unsupported is rejected before any widget is constructed. See the
[plan contract](plan.md#version).

## Manual plans

`compileForm()` accepts a hand-written plan on the same terms as a generated
one. A plan is fully expanded (see the [plan contract](plan.md)): a missing or
unknown property is a `TypeError` before any widget exists, not a silent
default.

```text
plan.fields[0].node.options: is required
plan.fields[0].node.options.minLenght: unknown property
```

## Mounting

Mounting is explicit. `compileForm()` builds the elements; the application
decides where they go.

```javascript
const form = compileForm(plan);
const container = document.getElementById("form");

for (const field of form.fields) {
    container.append(field.widget.el);
}
```

Each entry of `form.fields` carries the field `name` from the plan and the
`Field` widget that wraps its control.

## Form state

```javascript
form.isReady()
form.hasError()
```

`isReady()` is true when every field currently represents a complete and
valid value. `hasError()` is true when at least one represented value is
invalid.

Both answer truthfully from the first instant. What waits for interaction is
only the visible message on a field the user has not touched: being invalid
and looking invalid are separate concerns.

```javascript
form.showErrors()
```

`form.showErrors()` closes that gap on demand: it marks every field as touched so
each reveals the message it had held back, with no user interaction. Call it when
the user submits a form they never fully visited — a required field left empty, or
one holding a value that breaks a constraint (typed, or assigned programmatically
through `setValue()`), turns red at once instead of failing silently.
It only affects what is *shown*: `value()`, `read()` and `isReady()` are
unchanged, and a switched-off optional field (never in error) is left alone. The
same method exists on every widget — `widget.showErrors()` reveals one subtree,
and containers propagate to their children — so a host can reveal a single field
or the whole form. A widget with no message of its own (a checkbox, a select) has
nothing to reveal and does nothing.

A field that is switched off represents `None`, so it is neither empty nor in
error.

```javascript
const unsubscribe = form.onChange(() => repaint());
```

`form.onChange()` subscribes to every field at once and fires the callback once
per change, wherever in the tree it happens — nested groups, list rows and union
branches all reach it through their root field. A change is usually a user
action, but a programmatic `setValue()` emits one too (it does not, however, mark
any field touched). It returns an idempotent
unsubscribe, the same contract as `widget.onChange()`, and changes nothing about
`form.read()`. It saves an application from wiring each `form.fields[i].widget`
by hand.

## Prefilling

`setValue()` is a direct-assignment operation on the widgets that support it — the
scalar inputs and `FileWidget` — so prefilling assigns one control at a time. There
is no `form.setValue()` and no composite `setValue()` on groups, lists or unions:
the widget tree is built from a plan through constructors and its `default` values,
not mutated wholesale afterwards.

Each entry of `form.fields` is `{ name, widget, read }`, where `widget` is the
`Field` wrapper and `widget.widget` is the assignable control inside it. To prefill
a top-level scalar or file field, find it by name and assign its inner widget:

```javascript
function prefill(form, name, value) {
    const field = form.fields.find((f) => f.name === name);

    if (field === undefined) {
        return false;                     // no such field
    }

    field.widget.widget.setValue(value);  // Field -> scalar widget
    return true;
}

const params = new URLSearchParams(location.search);

for (const [name, value] of params) {
    try {
        prefill(form, name, value);
    } catch {
        // an incompatible value, or a non-scalar field: see the note below
    }
}
```

`setValue()` takes the plain value the scalar represents — a string for a
`StrWidget`, a safe integer or `null` for an ordinary `IntWidget` (a slider
rejects `null`), one of its choices for a choice widget. It updates the control,
`value()`, readiness and error state, and emits one change event.

An **optional field that starts disabled** is two steps: enable the toggle with
`Field.setEnabled(true)`, then assign the inner widget. The `Field` is
`form.fields[i].widget`:

```javascript
const nickname = form.fields.find((f) => f.name === "nickname").widget;

nickname.setEnabled(true);        // flip the optional toggle on
nickname.widget.setValue("Ada");  // then assign the scalar
```

`setEnabled(false)` switches an optional field back off (it then reads as
`null`); calling it on a required field throws, because a required field is
always on.

The library supplies only the mechanics — locating a widget, assigning a value,
toggling an optional. **Policy is the caller's**: what to do when a value fails
to parse or is the wrong type (each `setValue()` throws independently), whether a
partial prefill is acceptable, and how to treat an unknown parameter. There is
no transaction — `form.setValue()` was removed, so nothing rolls a batch back;
each assignment stands on its own. To prefill whole subtrees at construction
time, put the values in the plan's `default` instead.

## Reading transport

```javascript
form.read()
```

returns the complete transport object described by the plan. Union branches
are wrapped according to their `mode`:

```javascript
// plain
{ reference: "INV-2024" }

// wrapped
{ reference: { $type: "str", $value: "INV-2024" } }

// inline
{ item: { $type: "Shirt", size: "M" } }
```

`widget.value()` answers a different question: the plain local value that a
single component represents, with no discriminators and no wrappers.

```javascript
form.fields[0].widget.value()   // "INV-2024"
```

### Union modes

A union with two or more branches is presented as a page-like navigator, not a
dropdown of type names:

```text
[ ‹ ]   Mode 1 of 3   [ › ]

[ active branch widget ]
```

One branch is visible at a time. The previous / next buttons move one branch
at a time — they do not wrap around — and the indicator shows `Mode N of M`.
Each branch keeps its own state while hidden, so moving away and back does not
lose what was typed. Inactive branches are detached from the DOM, so they are
not keyboard-focusable.

The technical branch id — `str`, `list[str]`, `Shirt` — is never shown. It
remains the transport discriminator: `form.read()` still returns a string or
an integer (or a `$type`-tagged object) according to the active branch, exactly
as before. `choice.selectedValue()` and `choice.activeIndex()` expose it
programmatically.

The button labels and the position template come from `WebConfig`
(`mode_previous_label`, `mode_next_label`, `mode_position_label`) and travel in
the plan on the choice node. The position template takes exactly `{current}`
and `{total}`.

An optional union such as `str | int | None` keeps `None` on the field's
optional toggle, not as a visible mode: switching the toggle off is `None`;
switching it on shows the navigator between `str` and `int`. Scalar `Choices`
and `Literal` stay native `<select>` dropdowns — the navigator is only for
structural branches.

When the mode changes, focus stays on the button that was activated, and the
first field of the new branch is not auto-focused. The one exception is an
extreme: moving to the first branch disables the previous button and moving to
the last disables the next, and a disabled control cannot hold focus, so focus
moves to the still-enabled sibling button rather than falling back to the body.

### Reading an incomplete form

`read()` is an inspection operation and is always callable. It never throws
because the form is incomplete, and it returns whatever the widgets currently
represent:

| Situation                            | Value in the transport object     |
| ------------------------------------ | --------------------------------- |
| integer with no number typed          | `null`                            |
| integer that cannot be parsed         | `null`                            |
| integer outside the JS safe range     | `null` (never the rounded number) |
| integer outside its bounds            | the number, unchanged             |
| float with no number typed            | `null`                            |
| float that cannot be parsed           | `null`                            |
| float that overflows to `Infinity`    | `null` (never transported)        |
| float outside its bounds              | the number, unchanged             |
| date/time with nothing picked         | `null`                            |
| date/time outside its bounds          | the ISO string, unchanged         |
| string breaking `minLength`           | the string, unchanged             |
| incomplete nested object              | an object with incomplete members |
| list holding an invalid item          | the item, unchanged               |
| optional switched off                 | `null`                            |
| optional switched on but incomplete   | `null`                            |
| choice on an incomplete branch        | wrapped as the branch `mode` says |

Invalid but representable values travel unchanged: `read()` reports state, it
does not filter. Note that an optional field reads as `null` both when it is
switched off and when it is switched on but still empty; `isReady()` is what
tells those apart.

Transport honesty has one hard edge. An invalid but *representable* safe value
travels exactly as typed — `read()` never silently corrects it. But a
syntactically valid integer that falls outside JavaScript's safe range
(`-(2⁵³−1)` … `2⁵³−1`) is **not** transported as a rounded number: `value()`
and `form.read()` return `null` while the raw text stays visible in the input
and `safeMessage` reports the problem after interaction. The classification is
done on the canonical integer text with a `BigInt` comparison, so
`"9007199254740993"` reads as `null`, never as the rounded `9007199254740992`.
Unparseable text (`abc`, `1.5`) and unsafe integer text both read as `null`;
only safe integers become numbers in the transport object. The stepper arrows
(and `ArrowUp`/`ArrowDown`) are a write command, not a read: on unparseable text
they start from the base value and replace it — a visible response to an explicit
action, not a silent correction.

`FloatWidget` parses with the same honesty, against an explicit grammar:
exactly `-?\d+(\.\d+)?` over the trimmed text — no scientific notation, no bare
`.5` or `5.`, no decimal comma. Text outside the grammar reads as `null` and
shows `invalidMessage`. A grammar-valid magnitude that overflows to `Infinity`
also reads as `null` and shows `finiteMessage`; it is never transported, the
float analogue of the unsafe integer. A bound is compared directly against the
double with its exclusivity flag, exactly as the core does — there is no ±1
conversion. `value()` and `read()` return a plain JavaScript number, `3`
included (every JS number is a double); turning that `3` back into the `float`
the core wants is [`decode()`](python.md#decode)'s job, not the widget's.

A live user value and a plan `default` are held to different standards. A value
the user types may stay representable while breaking a constraint, and the
widget reports it through `hasError()` / `isReady()`. A plan `default`, by
contrast, is producer configuration: `checkPlan()` validates it against the
full constraints of its node — string lengths, `pattern`, integer ranges,
`multipleOf`, `choices` and the slider `Step` grid — so a constraint-invalid
default never mounts, it fails before any widget is built.

Applications should require `isReady()` before submitting to a strict
consumer. `hasError()` is narrower: it is true only when a represented value
breaks a constraint, so a form with an untouched required field has
`isReady() === false` and `hasError() === false`.

## Direct widget usage

`fields.js` and `inputs.js` form a usable library on their own. Constructing
a widget by hand is normal use, not a shortcut:

```javascript
import { Field } from "./fields.js";
import { StrWidget } from "./inputs.js";

const widget = new StrWidget({ minLength: 3, placeholder: "Username" });
const field = new Field({ id: "username", name: "Username" }, widget);

document.body.append(field.el);
```

Every public widget — scalar or container — implements the same common contract:

| Member          | Meaning                                                   |
| --------------- | --------------------------------------------------------- |
| `el`            | the element the widget owns, including its message         |
| `value()`       | the plain value it represents                              |
| `isEmpty()`     | whether it currently represents no value                   |
| `error()`       | the current validation message, or `null`                  |
| `isReady()`     | not empty and not in error                                 |
| `hasError()`    | a leaf derives it from `error()`; a container aggregates its children's error state |
| `onChange(cb)`  | subscribe; returns an idempotent unsubscribe function      |
| `showErrors()`  | reveal any held-back message; recurses into children       |
| `control()`     | the single interactive control, or `null` for a container  |

`setValue(value)` is **not** part of that common contract. It is an additional
operation only on widgets that support direct assignment — the scalar inputs and
`FileWidget` — and is described next.

`setValue()` is a **direct-assignment** operation: validate and apply. It updates
the DOM control, `value()`, readiness and error state, and emits one change event.
The scalar inputs take a single value; `FileWidget` also accepts an array of
references in `multiple` mode (see below), so the exact category is "assignable",
not strictly "scalar". There is no composite `setValue()` on `Field`,
`GroupWidget`, `ListWidget` or `ChoiceWidget`, and no `form.setValue()`: a widget
tree is built from a plan through constructors and `default` values, not
reassigned wholesale.

| Widget                                | `setValue()` accepts             |
| ------------------------------------- | -------------------------------- |
| `StrWidget`                           | a string                         |
| `IntWidget`                           | a safe integer, or `null` (a slider rejects `null`) |
| `FloatWidget`                         | a finite number, or `null`       |
| `DateWidget` / `TimeWidget`           | a canonical ISO string, or `null` (a date must be a real calendar date) |
| `BoolWidget`                          | `true` or `false`                |
| `FileWidget`                          | an existing reference (string, or array of strings when `multiple`), or `null` — shown as the current file and transported verbatim; see below |
| `StrChoiceWidget` / `IntChoiceWidget` / `FloatChoiceWidget` | one of the declared choices |

An incompatible value is rejected with a `TypeError`, never silently discarded.

`isEmpty()` is not visual emptiness: `""`, `0` and `[]` are values. A
`StrWidget` holding `""` is not empty; an `IntWidget` with no number is.

`BoolWidget` is a native checkbox that, like a choice widget, always represents
a value: unchecked is `false`, checked is `true`. It is never empty, never in
error and always ready, and has no validation message. `setValue()` takes only
`true` or `false` — `null` or a string throws.

`FileWidget` mints its value **locally**: when the user picks a file it generates
a reference — the file's own name compressed to bare ASCII (its first 15
characters at most), a UUID, and the file's lowercased extension, as in
`informe-anual-<uuid>.pdf` — and that is `value()`. The name is a readable label
only; uniqueness lives entirely in the UUID, so two picks of the same name mint
two distinct references, and a name that keeps nothing (no ASCII survives the
compression) mints the bare `<uuid>.pdf`.
A `multiple` node (from `list[File]`) takes several files at once, mints one
reference each, and `value()` is the array (`files()` gives the raw `File`s,
`file()` the first); `minFiles`/`maxFiles` bound the count. A single node makes
`value()` a lone reference or `null`. A file whose extension the node does not
accept mints no reference and is *invalid* (`value()` `null`, `invalidMessage`
shown, `aria-invalid` set) — all-or-nothing on a single pick. A `multiple` field
builds a list: the native input **resets** it to the pick, while the **+** button
and a drop **append**; each chosen file is a card with its own **✕** to drop just
that one, and the earlier references stay stable. A single field replaces on each
pick. This is presentation over the same value contract — the array of minted
references is unchanged.

A file field has **two origins**, and the whole design follows from keeping them
distinct. A *local choice* is the one just described — the only source of *new*
references. An *existing* reference is what the host already holds and plants with
`setValue(string)` (or an array on a `multiple` node): a value from a past
`read()`, its own store. The widget shows it declared as such — "`Current file:
…`" with a **Replace** button, not editable and with the choose control hidden —
and `value()`/`read()` transport it **verbatim**, so a struct with a file path
survives an edit form untouched. The reference must clear the same extension
filter a minted one does. `isReady()` is `true` in that mode. **Replace** drops
the held reference and brings the native choose control back — the same for a
single file and a `multiple` list, where the input then resets the selection and
the **+** button grows it; choosing mints a fresh reference, picking nothing
leaves the field empty. It sets the current reference aside, so a **↺** button
undoes the replace and brings it back until the field is submitted or set anew.
`setValue()` accepts a single reference (`string | null`) on a single node and an
array of references (`string[] | null`) on a `multiple` node. `setValue(null)`
clears it programmatically; a value that is neither a reference — nor an array of
them in `multiple` mode — nor `null`, or one with a bad extension, throws. The two origins never blur: nothing from outside can fabricate a choice
that did not happen, so a set reference is always shown as *existing*, never as a
selected file. Turning the chosen files into stored bytes is the host's job — see
[Values completed outside the browser](#values-completed-outside-the-browser).

`StrChoiceWidget` and `IntChoiceWidget` take the list of choices and an optional
initial value: `new StrChoiceWidget(["red", "green", "blue"])`. A non-empty
choice widget always represents one of its choices — the initial value when
given, otherwise the first choice — so it is never empty and ready from the
start. Empty choices are rejected. `IntChoiceWidget` returns the integer, not
the option's text. `FloatChoiceWidget` is the float variant: its choices are
finite numbers and it returns the exact double from the plan, so equality is
exact — there is no "safe float" to guard, unlike the integer's safe range. A
closed set of dates or times is a select over ISO strings, so it reuses
`StrChoiceWidget` directly (an `enum` node is the same shape — a closed set of
member names — so it too mounts a `StrChoiceWidget`, over the names, with no
widget of its own) — a date/time value *is* a string.

`DateWidget` and `TimeWidget` wrap the native `date` and `time` inputs. The
browser presents a localized picker and its value comes out in canonical ISO, so
there is **no parsing grammar** the way `IntWidget`/`FloatWidget` have one:
`value()` is the ISO string (`"2026-07-22"`, `"14:30:00"`) or `null` when empty,
and `read()` reports it as-is. Bounds compare lexicographically over the
fixed-width ISO form.

A canonical date is **a real calendar date represented exactly as `YYYY-MM-DD`**,
not merely a string of that shape. `setValue()` refuses `"2026-02-31"` or
`"2026-13-01"` with a `TypeError` and leaves the previous value in place, and a
typed value that is not a real date reports `invalidMessage`. This matters
because a native date input silently blanks itself when handed an impossible
date, so the value is rejected before it reaches the control — never corrected,
trimmed or substituted. `isValidIsoDate` (`iso.js`) is the single implementation,
shared with the plan validator, so a manual plan and a directly built widget are
held to exactly the guarantee `pytypehint` already gives generated plans by
starting from real `datetime.date` objects. A date bound is inclusive (the adapter converted any
exclusive one by ±1 day); a time bound keeps its exclusive flag and the `time`
control opens its seconds field (`step=1`). Turning the ISO string back into a
`date`/`time` object is [`decode()`](python.md#decode)'s job, not the widget's.

A `StrWidget` whose `pattern` is exactly `COLOR_PATTERN` (exported from
`inputs.js`, the `#[0-9a-fA-F]{6}` string the `Color` alias emits) mounts a
colour picker beside the text field; any other pattern, even an equivalent one
written differently, does not. The text stays the source of truth — the picker
only writes a valid `#rrggbb` into it and rides the normal input flow — so it
adds no validation. It is widget presentation, not contract: a hand-written plan
gets the assistant by using that published pattern string, nothing else.

Containers — `Field`, `GroupWidget`, `ListWidget`, `ChoiceWidget` — use only
that contract on their children. They never inspect a child's concrete class.

Widget constructor defaults and plan defaults are separate contracts. They
agree wherever both exist, with one deliberate exception: a directly
constructed `IntWidget` shows the slider value by default, while the plan
default for `showValue` is `false`. Plan-created integer widgets always
receive the normalized value explicitly, so the two never collide.

## Values completed outside the browser

Some values are complete in the browser but only *promised* until something
outside it acts. A file is the first: `FileWidget` mints a reference the instant
the user picks a file (the slugged name, a UUID and the extension), so `value()`
and `read()` carry
it immediately — but the bytes are not stored until the host uploads them.

The cycle belongs to the host. On change it pairs each chosen file with the
reference the widget minted for it and uploads the bytes **labelled with that
reference** through its own channel:

```javascript
widget.onChange(() => {
  // Only a local choice carries a File to upload. An existing reference planted
  // with setValue() has none — its bytes already live on the host — so files()
  // is empty and nothing is uploaded for it. Guarding on files() is what keeps
  // this from calling upload(undefined, reference) on an edit form.
  const files = widget.files();                 // the raw File objects, local picks only
  if (files.length === 0) return;

  const value = widget.value();                 // minted references, aligned with files()
  const references = widget.multiple ? value : [value];
  files.forEach((file, i) => upload(file, references[i]));
});
```

Because a reference is ready before its bytes are, a host should hold submission
until the upload confirms — the bundled demo keeps its send button disabled until
then.

**Create and edit are the same form.** For the top-level fields whose inner widget
supports direct assignment — the scalar inputs and file fields — one loop restores
each stored value, with no special case for files: on a file field the string is an
*existing* reference, shown as the current file and transported back verbatim:

```javascript
for (const field of form.fields) {
  if (field.name in record) field.widget.widget.setValue(record[field.name]);
}
```

This flat loop fits a form of scalar and file fields. A `field.widget.widget` that
is a group, list or union has no `setValue()`, so a form with structural fields
needs the per-field handling shown under [Prefilling](#prefilling) instead — not a
new prefill API.

A `Struct` with an internal path — a `User.avatar` — thus goes to the form and
back **complete without moving bytes**: the untouched avatar returns as the exact
reference it went in as, a replaced one as the fresh reference the new choice
minted, and `build()` receives the whole struct. `read()` transports `null` for a
file once it is cleared — **Replace** drops the current file for the user (who
then picks a new one, or leaves it empty), `setValue(null)` for the host — and
*remove* vs *keep* is then the host's own semantics to resolve. New bytes are
uploaded only when the user actually picks a file. This is why plan defaults stay rejected while `setValue` may carry a
reference: a plan is a static artefact and a frozen reference in it is a promise
nobody renews, whereas the current file is runtime state the host sets fresh, from
its own truth, at mount.

**The library provides no net for the reference/bytes coherence.** It mints a
reference and checks only the extension; it never verifies that anything is stored
behind it. If the host never uploads the bytes, `build()` accepts a string that
points at nothing. A wrapper such as
[FuncToWeb](https://github.com/offerrall/FuncToWeb) that builds the upload cycle
must guarantee that coherence itself if it matters to it.

This is the general pattern for any value promised in the browser but completed
outside it: the widget produces the intent and a local token for it, and the host
redeems the token through its own channel. The bundled demo wires exactly this
cycle against a toy `/upload` endpoint — it is where a wrapper copies from.

## Subscriptions

```javascript
const unsubscribe = widget.onChange(() => render());

unsubscribe();
```

`onChange()` returns an idempotent cancel function, so a container can
release a child that leaves the tree. Calling it twice is safe.

## Accessibility

The widgets use native form controls — `input`, `textarea`, `select`,
`button`, `input[type=checkbox]` — so keyboard behaviour, focus order and
screen-reader roles come from the browser rather than from a custom layer.

What the widgets guarantee, and what the browser suite pins:

| Behaviour | How |
| --- | --- |
| Every labelled control has an accessible name | `<label for>` pointing at the control's generated `id` |
| Containers have an accessible name | `role="group"` plus `aria-labelledby` on the group element |
| Field descriptions are announced | `aria-describedby` on the control |
| Visible validation messages are announced | `aria-describedby`, added when the message appears and removed when it goes |
| Invalid values are exposed | `aria-invalid="true"` once the field is touched and its value is invalid; absent otherwise, and never before the first interaction |
| The optional toggle has a name and a target | `aria-labelledby` on the field label, `aria-controls` on the value control or group |
| A switched-off optional is out of reach | native `hidden` on the content |
| Repeated remove buttons are distinguishable | `aria-label` of `"<removeLabel> <n>"`, one-based and reindexed after every removal |
| The numeric stepper arrows have accessible names | `aria-label` from the node's `increaseLabel` / `decreaseLabel` (defaults `"Increase"` / `"Decrease"`, configurable through `WebConfig`); rendered only for an ordinary integer input, not a slider or a closed choice |
| List limits are conveyed natively | `disabled` on the add and remove buttons |
| Inactive union branches are not reachable | the branch element is detached from the DOM, not merely hidden |
| Messages do not interrupt | `role="status"` with `aria-live="polite"`, and no message is shown until the field is touched |

Touched state lives where the message lives. Each scalar widget owns its own
touched flag and its own message, so typing in an inner control reveals that
control's message without any field-level bookkeeping; the optional toggle and
list container track their own interaction the same way. A programmatic
`setValue()` never marks anything touched, so prefilling a form never makes it
accuse a field the user has not touched.

The invalid state, both `aria-invalid` and the stylesheet's red border, waits
for interaction exactly like the visible message: a freshly mounted field is
never shown as invalid, even when its value already fails a constraint.
`hasError()` and `isReady()` still tell the truth from the first instant — the
delay is presentation only, so the form never accuses a field the user has not
touched. Being invalid and being incomplete stay distinct: an integer with
nothing typed is not ready but not invalid, so it is never marked.

Every generated `id` is unique across the page. `compileForm()`'s `prefix`
option only chooses the readable part of the id; uniqueness does not depend on
callers picking different prefixes.

### What is not covered

- There is no formal WCAG conformance claim, and no automated screen-reader
  or browser-level test suite. The tests assert attributes and structure in a
  lightweight fake DOM.
- Focus after removing a list row is left to the browser. The library does not
  restore focus to a neighbouring row.
- The host application owns the page: landmarks, heading hierarchy, document
  language, form submission and the feedback that follows it.
- Replacing or overriding `widgets.css` can remove the focus indicator or hide
  labels. Semantic accessibility does not depend on the stylesheet, but visible
  focus styling does.

## Plan text is plain text

Every string a plan carries — field labels, descriptions, placeholders,
validation messages, list button labels, mode navigation strings, closed-choice
values and initial values — is inserted with `textContent`, `setAttribute` or
the control's `value` property. None of them is ever parsed as HTML.

The browser modules contain no `innerHTML`, `outerHTML`,
`insertAdjacentHTML`, `document.write`, `eval` or `new Function`, and never
build an element from a markup string. A test scans the shipped modules for
those sinks, and the browser suite mounts a form whose every text is a hostile
payload and asserts that no element it describes is created.

```javascript
label: "<b>Name</b>"
```

renders as the literal characters `<b>Name</b>`, not as bold text. Likewise:

```javascript
label: '<img src=x onerror="alert(1)">'
```

renders as text and executes nothing.

Attributes written from plan options are limited to a fixed set — `min`,
`max`, `step`, `rows`, `placeholder`, `title`, `type`, `accept`, `role` and the
`aria-*` attributes used above. A plan can never produce `href`, `src`,
`srcdoc`, `style` or an `on*` handler, and the plan contract has no URL-valued
property.

The native HTML `pattern` attribute is deliberately **not** among them. The
library validates patterns with its own compiled `RegExp` (the Unicode `u`
flag, wrapped as `^(?:…)$`) and owns the validation message and touched
behaviour. Writing `pattern` as well would let the browser's native
constraint-validation UI — possibly a different regex dialect, and unsupported
on `textarea` — compete with it. A pattern node still writes `title` as plain
help text; the pattern string travels as data and never becomes markup.

This is a rendering guarantee, not a sanitizer: nothing is stripped, escaped
or rewritten, and `form.read()` returns exactly what was typed. A plan is
data, and the application that supplies it is still responsible for where that
data came from — and for how it treats the transport object afterwards.

## Styling

`widgets.css` is the optional stylesheet. It ships inside the package, next to
the modules, and is loaded with a plain link:

```html
<link rel="stylesheet" href="widgets.css">
```

It is not part of the contract. The widgets are semantically correct,
keyboard-operable and accessible without it; loading it only changes their
appearance. Values and validation behave identically either way.

- Every rule is scoped to a `pth-*` class. The sheet carries no bare
  `input`, `select`, `button` or `label` selectors, so nothing outside a
  widget changes by loading it.
- All design tokens use the `--pth-*` namespace: typography, spacing, sizing,
  radii, borders, shadows, transitions and the colour palette.
- It never writes `outline: none`; keyboard focus stays visible through a
  `:focus-visible` outline in both themes.

### Light and dark themes

The palette follows the viewer's system preference automatically through
`@media (prefers-color-scheme: dark)`. An application can also force a theme,
with no JavaScript, by setting an attribute or a class on any ancestor:

```html
<div data-theme="dark"> … </div>
<body class="light-mode"> … </body>
```

`[data-theme="light"]`, `[data-theme="dark"]`, `.light-mode` and `.dark-mode`
are all honoured. These roots only redefine `--pth-*` variables; they do not
restyle host elements.

### Customising

Override any token on `:root` or on a scoped ancestor:

```css
:root {
    --pth-input-focus: #7c3aed;
    --pth-radius-base: 6px;
}
```

Because the tokens cascade, an application can theme a single form by setting
variables on its container rather than globally. The token set already covers
the shapes future scalar widgets will need — checkbox-like controls, numeric
inputs, native date and time inputs, and selects — so new widgets can reuse it
without new colours.

Element ids belong to the labelled control. Containers rely on classes only.

### Not styled here

The stylesheet covers every widget the library implements, the file input and
the colour picker among them. It has no rules for a submit/reset button row,
because the library has no submit step of its own: the bundled demo styles its
own send and reset buttons separately.

## Errors

Plan problems raise a `TypeError` with the failing path:

```text
plan.fields[2].node.kind: unknown node kind "tuple"
plan.fields[0].default: must be omitted when hasDefault is false
plan.fields[1].node.options: slider needs both min and max
```

Messages are generic and never mention Python, because a plan may have been
written by anyone. Directly constructed widgets validate their own arguments
and raise `TypeError` or `RangeError` on misuse.

Exact error strings are not part of any compatibility guarantee.
