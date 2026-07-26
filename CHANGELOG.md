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


## [0.0.1] - 2026-07-22

First release. `pytypehintweb` is the browser form layer for
[`pytypehint`](https://github.com/offerrall/pytypehint): it converts a compiled
type schema into a JSON-serializable form plan and renders it with framework-free
JavaScript widgets. Requires `pytypehint >= 0.0.6`.