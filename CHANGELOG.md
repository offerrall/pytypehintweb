# Changelog



## [0.0.4] - 2026-07-28

The current-file label is compacted now. A planted reference is whatever the host
already holds — a local server path, a stored name, a URL — and the widget used to
print it whole, so a deep `UPLOADS_DIR` path or a long URL spilled across the
field and put the server's directory layout on screen. It shows the name after the
last `/` or `\`, and when even that is long, a `…` followed by its last 32
characters. A name that already fits is untouched.

The cut is by characters, not by UTF-16 units, so a name of astral symbols is
never split mid pair, and it happens at render time only: `value()`, `read()` and
`uploads()` carry the reference exactly as it arrived, the extension filter still
sees the whole string, and replacing the current file with a local pick behaves as
it always did. Nothing about it is configurable and nothing new travels in the
plan — the shortened text exists only inside the label element, written with
`textContent`, and the full reference is not mirrored into a `title`, which would
have put it back on screen on hover.

This is presentation for **every** file field, not for images. The layer has no
notion of an image: one `FileWidget` serves a `.png` and a `.pdf` alike, and the
plan carries extensions, not types. Compacting only some of them would have meant
inventing a category here to decide how a label reads, which is the wrong place
for it — the problem was never the kind of file, it was the length of the string.


## [0.0.3] - 2026-07-27

A file field can carry a default now, and it means what `FileWidget.setValue()`
has always meant: an existing reference the host declares, shown as the current
file and transported back untouched. It carries no bytes, it is not a local
selection and it starts no upload — `file()` and `files()` stay empty and
`uploads()` reports nothing, while a user's own pick appears in all three. A
single node takes a `str`, a `multiple` one a `list[str]`, and an optional file
takes `null` for its off state.

The refusal was incoherent rather than merely strict. The widget already
represented an existing file, `value()` and `read()` already carried it back, and
no upload was ever started for it — but the plan rejected the same reference on
the way in, so the general prefill mechanism broke on file fields: a prefill is
expressed as a temporary default, and a form with a file could not have one.
There were three separate refusals, one in `plan_of()` for a lone file field, one
deeper in the value walk for a file nested anywhere, and one in `checkPlan()`.

Underneath, there is now a single implementation. `compileForm()` builds the
`FileWidget` and applies the default by calling its public `setValue()` — the
same entry point a host uses — so the two paths cannot drift, and the tests
assert exactly that: compiling with a default produces the same observable state
as compiling without one and calling `setValue()` afterwards, both at the widget
level and across the real Python → plan → browser boundary. It also fixes the
second half of the incoherence, since the compiler was ignoring the initial value
for file nodes even where one could be expressed.

`checkPlan()` polices the shape and the widget owns the semantics: a default must
match its node's arity (a bare string on a `multiple` node and an array on a
single one are both rejected, with the failing path), every reference must be a
non-empty string passing the same `endswith` extension filter, and a multiple
default must sit within `minFiles` and `maxFiles`.

One thing worth stating plainly, because it decides where a prefill can come
from. A default written into a **Python** schema is certified by `IsPathFile`
while the schema compiles, so `plan_of()` only ever sees a reference the core
already accepted — which, since 0.0.7, means a real local file. A host whose
references are not local paths, an object-store key say, cannot pass one through
a schema default; it plants it with `setValue()` after mounting, which the plan
layer and the widget accept as the opaque reference it is, and resolves it on the
way back with `decode(..., file_resolver=...)`. Nothing in the browser ever
checks that bytes stand behind a reference: an expired one shows in the form and
fails when the host resolves it, which is correct, because the form and the
storage are different layers.

Nothing about the transport moved: the plan version, the property names, the file
node's shape, the reference on the wire, the upload API and
`decode(file_resolver=...)` are all unchanged, and a plan without file defaults
behaves exactly as before.

A file composes like any other node now, at any depth. `list[File | None]`,
`list[File | int]`, `list[list[File]]` and `list[SomeDataclassHoldingAFile]` all
compile, along with anything else built from them.

They were never unrepresentable. The plan already had every node the shapes need
— `list`, `optional`, `choice`, `object`, `file` — the Python adapter already
recursed over them, `compileForm()` already compiled a list item by calling
`compileNode()` on it, `checkPlan()` already validated defaults recursively, and
`decode()` already walked files to any depth. Hand-writing those plans and
mounting them worked before this release; the only thing standing in the way was
one predicate in `plan_of()` that asked "does this list's item contain a file
anywhere?" and refused if so. That is a blanket policy, not a structural limit,
and it is gone — with the predicate itself, which had no other caller.

What remains is the one file-specific decision worth keeping, and it is a
shortcut rather than a rule: a *bare* `list[File]` still becomes a single
`multiple` file node, because that is what a user expects from it. It is chosen
by an exact shape match, so it captures nothing wider — which is also why
`list[list[File]]` is a list whose rows are `multiple` file nodes, the shortcut
applying at the inner level while the outer list stays a list. The structure is
never flattened.

The genuine ambiguity is documented as what it is. `File | str`, and so
`list[File | str]`, is inconstructible because a file *is* a `Str`: both branches
carry the option id `"str"` and the core rejects the schema with `duplicate
option types in shape`. Nothing can tell them apart on the wire. That says
nothing about `File | None` or `File | int`, whose branches are distinguishable
and which both work.

The two roads a reference can take are now stated apart, since only one of them
carries a guarantee when the page renders. A default in a **Python schema** — a
prefill included, a prefill being a temporary default — is certified by
`IsPathFile` before a plan can exist: exact `str`, the file exists, it is a
regular file, the extension matches, and the byte bounds hold when used. A
missing one fails with `file does not exist` and produces no plan, which is what
stops a form from displaying a file nobody has; a `list[File]` default is
certified element by element, list bounds included. A reference applied at
runtime with **`setValue()`** certifies nothing by itself: it is frontend state,
and the guarantee arrives later, when the host resolves it with
`decode(..., file_resolver=...)` and the core checks the path it resolved to.
Both land the widget in the same observable state; only the first has been
checked by render time.

`IsPathFile(min_size=...)` and `max_size=...` stopped being refused and started
being carried. The refusal rested on a rule worth stating the other way round:
**a restriction the browser cannot check must not make the type unrepresentable.**
Refusing the plan did not protect anyone — it only meant a schema the core
validates perfectly could not produce a form at all.

They travel as `minSize` and `maxSize` on the file node, in bytes and **per
file**, so three 4 MB files under a 5 MB bound are three valid files; counting
them stays `minFiles` / `maxFiles`. They belong to the node, so they arrive
wherever a file node arrives — inside a list, a union branch, a nested struct —
with no rule about depth.

A local `File` carries a `.size`, so `FileWidget` now weighs one and refuses it
before any upload: exactly at a bound is inside, one byte past it is not, the
message names the bound the way the widget names a size ("minimum 2 KB"), the
error joins `hasError()` / `isReady()` / `showErrors()`, and a refused pick mints
no reference, so `uploads()` never offers it. A batch that contains one bad file
is refused whole rather than half-accepted. `WebConfig` gained
`file_min_size_message` and `file_max_size_message` for the two texts.

What the widget does **not** do is guess. A reference the host plants — a
default, or a runtime `setValue()` — names a file the browser never saw, so it
carries no size and none is invented, no request is made to find one out, and
nothing marks it as certified. Both readings end in the same place: `build()`
measures the real file. That is what a hand-written HTTP call, a stale
reference, or a file edited after upload all run into, and it is why the browser
check is a courtesy rather than the verdict.

Every icon the interface draws is a file now. The select arrow was a
`data:image/svg+xml` written into `widgets.css` and the list's remove glyph was
an `<svg>` the runtime assembled node by node; both are `.svg` files under
`static/icons/`, referenced from the stylesheet and from nowhere else.

The point is the page's Content-Security-Policy. A data URI in a stylesheet is
still an image the browser fetches, so the arrow forced every host that loads
`widgets.css` to allow `img-src data:` — a broad permission granted for one
12×12 chevron. The icons now load under a plain `img-src 'self'`, and the sheet
contains no `data:` and no base64 at all.

Paths are relative to the stylesheet (`url("./icons/select-arrow-light.svg")`),
not to the document and not absolute, so they follow it under any static prefix:
a host that serves the package's static directory at `/assets/pth/` needs to
configure nothing. What it does have to serve is the whole directory, the new
`icons/` subdirectory included. The bundled demo's own static route was reaching
only the flat files, so it grew a path segment — with the containment check
tightened to match, since accepting a slash is exactly how a traversal gets in.

The remove glyph keeps its colour. An external SVG loaded as an image cannot see
the page's `currentColor`, so it would have frozen to one colour and lost both
the theme and the red it turns on hover; it is painted through a `mask` instead,
with the colour coming from the element. The runtime therefore builds no SVG of
its own any more — it mints an empty, `aria-hidden` span the stylesheet masks —
and the button's size, accessible name and behaviour are unchanged. If the file
does not load the glyph is simply not painted: measured, not assumed.

The tokens are the same three, `--pth-select-arrow-light` / `-dark` and the
active `--pth-select-arrow`, and the select rule still reads only the active one.
Contrast is still asserted, but now against the asset: the test reads the stroke
colour out of the `.svg` the browser will actually fetch, so the guarantee covers
what is painted rather than a copy of it kept in the stylesheet.

Packaging was verified rather than assumed — nothing under `src/` ships just for
being there — and `static/icons/*.svg` is declared as package data. The three
files appear in both the wheel and the sdist.

The documentation's own anchor checker was wrong, and quietly so. It slugged
headings by deleting every character outside `[a-z0-9 -]`, underscores included,
so a correct link like `[file_resolver](#file_resolver)` over a
`### \`file_resolver\`` heading was reported as broken — and had been worked
around by demoting the link to plain text. It also read every `#` line in the
document as a heading, so the shell comments inside fenced code blocks became
anchors the rendered page never offers.

`tests/python/markdown_anchors.py` now reproduces GitHub's rule and documents
it: inline Markdown is reduced to the text it renders as, the text is
lowercased, everything that is not a letter, digit, `_`, `-` or space is dropped
without leaving a separator (so `HTTP / transport` gives `http--transport`, with
both spaces surviving), spaces become hyphens, non-ASCII letters are kept
(`Café` gives `café`), and a repeated slug takes `-1`, `-2`. The heading parser
reads ATX and Setext, skips fenced blocks whole, and honours fence lengths. The
link is a link again, and a table of thirty-odd cases pins the semantics so the
next change to it has to be deliberate.


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

The stylesheet now has one theme contract, and it is entirely CSS. Widgets are
mounted inside a `.pth-root` container; without an override that root follows
`prefers-color-scheme`, and `data-pth-theme="light"` or `"dark"` — on the root
or on any ancestor, `<html>` included — forces one. Nothing else exists: no
`theme` in the plan, no option on `compileForm()`, no theme JavaScript in the
runtime, no `localStorage`, no global theme manager. Because the automatic mode
resolves in pure CSS the widgets cannot flash light-then-dark; a host that
restores a remembered *manual* preference still has to write the attribute
before the first paint, which is its own job and is documented as such.

Overrides win by source order rather than by weight — the manual blocks follow
the automatic one and the automatic one skips any root carrying an override
itself or inheriting one — so there is no `!important` anywhere near a theme.
The tokens land on the element holding the attribute and reach the widgets by
inheritance, which is what makes the *nearest* override win: two roots on one
page can hold different themes, and a subtree can disagree with its ancestor.

The pre-1.0 `[data-theme="light"|"dark"]` attribute and the `.light-mode` /
`.dark-mode` classes are gone, not aliased, and the sheet no longer writes to
`:root` at all. Every rule now starts at `.pth-root`, so loading the stylesheet
cannot reach a host element and widgets mounted outside a root are plainly
unstyled instead of half-styled. `color-scheme` is set on the library's own
controls only. The root paints `--pth-surface`, the background the palette is
calibrated against, which is what lets a forced dark form sit on a light page
without unreadable labels.

Colours are two levels now: a `--pth-<name>-light` / `--pth-<name>-dark` pair
per palette entry, and the active `--pth-<name>` token the widgets read. Nothing
outside a theme block reads half a pair, and no colour is written into a rule.
The naming inconsistency is gone (`--pth-nested-bg-light` vs
`--pth-nested-background`), the colour aliases that had no per-theme source
(`--pth-item-background`, `--pth-choice-border-color`, `--pth-index-color` and
the rest) were dropped in favour of the tokens they pointed at, and `-bg`
became `-background` throughout.

Three colours that could not follow the theme now do. Button text is
`--pth-submit-text` instead of a hard `#ffffff`, on the submit-coloured
controls and on every hover that paints text over the focus colour; the error
red is a pair, because one red cannot clear 4.5:1 on both a white and a near
black background; and the select chevron, which was a `#6b7280` baked into its
data URI, is a pair of its own. The switch knob gained one too.

The palette was retuned for contrast and measured rather than eyeballed. Input
borders were the worst offender — `#d1d5db` on white is 1.5:1, and the border is
the main signal that a control is there — and now clear 3:1 against the surface,
the input, the nested background and the hover. Text, error messages and button
text clear 4.5:1 in both themes; borders, focus rings, the knob and the arrow
clear 3:1. The tests assert those relations against thresholds, never a specific
hex, so the palette stays tunable.

The sheet is now tested as a contract rather than as a file. The Python suite
reads it as data — selectors, blocks, token sets, palette pairs — and measures
the contrast relations, and a new static page, `tests/browser/theme.html`, puts
the cascade itself in front of a real browser, because specificity, inheritance
and proximity do not exist in a text assertion. CI runs it once per system
preference so automatic mode is covered both ways.

`pytypehint 0.0.7` hardened `IsPathFile`, and the file field follows it. The core
now certifies the file itself on the way in — extension, existence, regular file
and byte size — so a reference the host never turned into real storage is refused
by `build()` with `file does not exist` instead of travelling on as a promise
nobody checks. Nothing in the browser changes: the widget still mints an opaque
reference and still filters by extension alone. What changes is that the host has
to close the gap, and the seam for that already existed —
`decode(..., file_resolver=...)`, added earlier in this release.

The bundled demo now uses it, because without it every one of its six file forms
answered `file does not exist`. `/build` passes a resolver that maps a reference
to the temp directory `/upload` writes into, and the two "edit an existing record"
cases seed their sample files at startup, since a prefilled record names a file
the host is supposed to already hold. The tests follow the same rule: anything
that reaches a `Choices` list, a default or `build()` now points at a real file
created under `tmp_path`, while the many tests that only inspect a plan still need
nothing on disk — a plan is compiled from the shape, never from a value.

`IsPathFile`'s new `min_size` and `max_size` are **refused at compile** rather
than dropped. The plan has no way to carry a byte bound and the widget has no way
to show one, so a form would have accepted a file the core then rejected *after*
the upload had already happened. `plan_of()` raises `TypeError`
("`IsPathFile.min_size` is not supported yet"), the same deferral `Float.slider`
and the other `Str` atoms get, until the widget can check `File.size` itself.
(Reversed in 0.0.3: the widget checks it now, and the bounds travel.)

Two testing defects surfaced while checking the theme work and are fixed here.
The browser smoke page had never actually gated anything: CI matched a bare
`SMOKE: PASS`, which the page's own comment contains, so the step reported success
whatever the page did — and it did fail, silently, about half the time. That half
was a race, not a shortfall: a top-level `await import(...)` settles after the load
event, so `--dump-dom` captured `PENDING`. Both pages now import statically (which
also loses nothing — the `try`/`catch` started after the awaits, so it never caught
an import failure), and both CI steps read the verdict from the `#result` element
and dump the page when it is not PASS. Measured after the fix: 24 consecutive runs,
all green.

Not touched, deliberately: `prefers-reduced-motion` is unchanged and still has
nothing to do with the theme, no transition animates `all`, no `light-dark()` —
explicit blocks keep a subtree themable without a global `color-scheme` — and
the widgets, the plan, the transport and validation are byte-for-byte the same.


## [0.0.1] - 2026-07-22

First release. `pytypehintweb` is the browser form layer for
[`pytypehint`](https://github.com/offerrall/pytypehint): it converts a compiled
type schema into a JSON-serializable form plan and renders it with framework-free
JavaScript widgets. Requires `pytypehint >= 0.0.6`.