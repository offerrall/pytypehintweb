# Changelog



## [0.0.2] - 2026-07-26

A minted file reference now carries the name of the file it came from. When the
user picks a file, `FileWidget` compresses that file's name to bare ASCII —
diacritics folded away, lowercased, every other run of characters collapsed to
`-` — keeps at most its first 15 characters, and puts it in front of the UUID:
`informe-anual-<uuid>.pdf` instead of `<uuid>.pdf`. A name that keeps nothing
(an empty stem, or one written in a script that folds away entirely) still mints
the bare `<uuid>.pdf`.

Uniqueness is unchanged — it lives entirely in the UUID, so two picks of the same
name still mint two distinct references — and so is every contract around it: the
reference is still opaque to the core, still filtered only by extension, still a
`str` on the wire, and an existing reference planted with `setValue()` is still
transported verbatim. The slug alphabet is `[a-z0-9-]`, so a reference remains a
safe single path segment.

`decode()` now accepts an optional keyword-only `file_resolver`
(`Callable[[str], str]`). When supplied, every file reference the existing
transport walk reaches is passed through that callable and its return value
continues down the pipeline: file fields at the root, `list[File]` (once per
reference, in order), files inside structs, inside lists, and inside the selected
branch of a union — `plain`, `inline` and `wrapped` alike. Without a resolver,
references travel untouched exactly as before, so the call with no keyword is
unchanged in every respect.

The resolver is deliberately storage-agnostic: `pytypehintweb` still knows only
that the value belongs to a file node — decided by the shape, never by what the
string looks like — while the host decides whether that reference becomes a local
path, an object-store key or any other string. Nothing about storage, existence,
paths or security enters the library. An absent field, a `None` and an empty list
never reach the resolver, and an exception it raises propagates unchanged: it is
the host's error, not one `pytypehintweb` names or swallows. This is the one way
`decode()` can raise on a value, and only because the host asked for it.

A host like FuncToWeb can therefore turn references into persistent paths without
reimplementing the walk over objects, lists, optionals and unions.

The browser modules now ship without comments. They are served exactly as they
are written, with no build step in between, so every explanatory line was weight
downloaded by every page that loads the runtime. The reasoning they held is not
lost — it lives in `docs/`, which is where a reader looks for it anyway.

Only comments were removed: same code, same tokens, same behaviour, whole suite
green. Measured with LF endings, the runtime drops from 143 130 to 116 829 raw
bytes and from 33 337 to 21 939 gzipped, a third of the compressed download. The
size budget's ceilings drop with it, keeping the same headroom as before. The
demo page's inline script was stripped the same way, keeping only the four
markers its tests use to extract helpers.

A float field now accepts a comma as the decimal separator. The comma is folded
to a point over the trimmed text before the parsing grammar runs, so `1,5` and
`1.5` are the same value and every restriction the grammar already had survives
untouched: one separator at most, so `1.000,5` and `3,1,4` stay invalid, as does
a lone `,`, and `1,000` reads as `1` — a comma is never a thousands mark. An
integer field is unaffected and still refuses it.

This is an input convenience, not a contract change. The widget never rewrites
what was typed, and `value()`, `read()` and the plan carry the plain number they
always did, so nothing downstream — transport, `decode()` or the core — can tell
which separator was used. It costs 19 bytes.

The motivation is a mobile keyboard. A float control is a text input with
`inputmode="decimal"`, which on iOS opens the system numeric keypad; on a device
whose locale writes decimals with a comma, that keypad offers a comma and no
point. The key the phone hands the user was the one the widget rejected, and
reaching a point meant switching keyboards. On a desktop the problem is invisible
because the point is typed without thinking.

A time field now completes the seconds a picker does not offer. The `time` node
asks its control for `step=1`, which opens the seconds field on a desktop picker
and made `HH:MM:SS` the value the widget could count on. iOS ignores the request:
its wheel picker has hours and minutes only and reports `HH:MM`, so on an iPhone
every time a user picked read as invalid and no form carrying one could be sent.
Whole minutes are inside the domain the core admits, so `TimeWidget` now reads a
well-formed, in-range `HH:MM` as `HH:MM:00` instead of rejecting it.

The completion is deliberately narrow. Only a value that is already a whole,
in-range `HH:MM` is completed; `12:3`, `24:00`, `12:60` and a stray fraction stay
exactly as the control reported them and stay invalid, so nothing malformed is
repaired into something plausible. A control that does report seconds is left
untouched, the widget never rewrites the text its control shows, and `setValue()`
is unchanged — it still demands the canonical `HH:MM:SS`. Bounds are compared
after completion, so an exclusive `09:00:00` still rejects a picked `09:00`, and
`read()` transports whole seconds exactly as before.

A slider now reaches its maximum even when the stride cannot land on it.
`Annotated[int, Min(1), Max(100), Step(5), Slider()]` used to stop at 96: the
grid was `min + k*step` and nothing else, so `100` — a value the plan itself
declares valid — was impossible to choose. The control was refusing a valid
value, which the doctrine forbids. The maximum is now a grid position of its
own, reached by a final short step (`… 91, 96, 100`).

Only the maximum is added, never a value inside a stride: `97`, `98` and `99`
are still refused, exactly as `2` and `3` are. `multipleOf` reachability follows
the same grid, so a slider whose only valid multiple *is* the maximum is
reachable and starts there instead of being rejected as unsatisfiable. The rule
lives in `slider.js` and is read by both the widget and `checkPlan()`, and the
Python adapter's `_slider_reaches` and slider-default check match it, so a plan
`plan_of()` emits and a plan the browser accepts still agree exactly.

A native `<input type="range">` cannot express this grid — it only offers
`min + k*step` and snaps anything else — so a slider whose stride misses the
maximum now drives its range input by grid *index* and maps index to value, and
carries `aria-valuetext` so a screen reader announces the value rather than the
index. The value contract is untouched: `value()` returns the integer,
`setValue()` takes the integer, and an off-grid value is still refused rather
than silently snapped. A slider whose stride *does* divide its range is
unchanged in every respect — its range input still carries the real `min`, `max`
and `step`, with no mapping.


## [0.0.1] - 2026-07-22

First release. `pytypehintweb` is the browser form layer for
[`pytypehint`](https://github.com/offerrall/pytypehint): it converts a compiled
type schema into a JSON-serializable form plan and renders it with framework-free
JavaScript widgets. Requires `pytypehint >= 0.0.6`.