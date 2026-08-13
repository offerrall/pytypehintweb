from collections.abc import Callable
from typing import Any

from pytypehint import Field, List, NoneShape, Shape, Signature, Str, Struct

# Reserved keys of the discriminated transport, mirrored from the core. A field
# can never carry them: field names must be identifiers, and neither is.
_TYPE = "$type"
_VALUE = "$value"

_Resolver = Callable[[str], str]


def decode(schema: Signature | Struct, data: Any, *,
           file_resolver: _Resolver | None = None) -> Any:
    # Prepare a JSON-parsed transport object for schema.build().
    #
    # The answer is a dict for the transport this is written for, but the return
    # type says Any because it is not one for every input: decode prepares and
    # does not validate, so a `data` that is not a dict is handed back as it
    # came, for build() to report. Promising dict[str, Any] would be a promise
    # the function does not keep, and a caller would be typed into trusting it.
    #
    # The portable representation belongs to the core, and schema.decode() is
    # where it lives: it restores the float a JSON writer flattened to an int,
    # the date and time the wire carried as text and the enum member it carried
    # as a name, and it consumes the discriminated wrapper wherever the exact
    # value is enough on its own. pytypehintweb does not repeat any of that —
    # one reading of the transport is what keeps the browser and the core
    # agreeing on what a value means.
    #
    # What the core deliberately does not own is storage. file_resolver, when
    # given, is called with the reference at every file node of the decoded
    # tree and its return value continues down the pipeline, so a host can map
    # a reference to a path or an object-store key without decode knowing what
    # storage means. An exception it raises propagates unchanged.
    fields = _fields_of(schema)
    decoded = schema.decode(data)

    if file_resolver is None:
        return decoded

    return _resolve_fields(fields, decoded, file_resolver)


def _fields_of(schema: Any) -> tuple[Field, ...]:
    if type(schema) is Struct:
        return schema.fields

    if type(schema) is Signature:
        return schema.params

    raise TypeError(
        f"decode expects a compiled Signature or Struct, got "
        f"{type(schema).__name__}")


def _resolve_fields(fields: tuple[Field, ...], data: Any,
                    resolver: _Resolver) -> Any:
    if type(data) is not dict:
        # Not the shape the walk descends; build() reports the mismatch.
        return data

    known = {field.name: field for field in fields}
    result = {}

    for key, value in data.items():
        # An unknown key travels intact, and only a string can name a field.
        field = known.get(key) if type(key) is str else None
        result[key] = (value if field is None
                       else _resolve(field.shape, value, resolver))

    return result


def _is_file(shape: Shape) -> bool:
    return type(shape) is Str and shape.file_hint is not None


def _resolve(shapes: tuple[Shape, ...], value: Any,
             resolver: _Resolver) -> Any:
    # A None is a value, not a path to descend, so nothing below it — the file
    # resolver included — ever sees it. A field the transport omits entirely is
    # never reached at all: it takes its default.
    if type(value) is str:
        # The resolver only fires on an unambiguous file reading: a lone Str
        # carrying FileHint. The core admits at most one Str per option group —
        # two would share the option id "str" — so the count is a guard for
        # shapes assembled by hand rather than a case the compiler can produce.
        strings = [s for s in shapes if type(s) is Str]

        if len(strings) == 1 and _is_file(strings[0]):
            return resolver(value)

        return value

    if type(value) is list:
        lists = [s for s in shapes if type(s) is List]

        # A bare list only reaches here with a single List branch; a union of
        # lists shares one Python type, so the core keeps its wrapper and the
        # branch below names which List this is.
        if len(lists) == 1:
            return [_resolve(lists[0].item, item, resolver) for item in value]

        return value

    if type(value) is dict:
        return _resolve_dict(shapes, value, resolver)

    return value


def _transport_type(shape: Shape) -> type:
    # The runtime type a value arrives as — a dataclass as a dict, anything else
    # as its pytype. This is the grouping the core keeps a wrapper for.
    return dict if type(shape) is Struct else shape.pytype


def _kept_branch(shapes: tuple[Shape, ...], discriminator: Any) -> Shape | None:
    # The core leaves a wrapper standing only where several options share one
    # runtime type, because there the discriminator is still what tells them
    # apart. Dataclasses are left out: they share the dict and name themselves
    # inline instead. Anywhere else a wrapper is malformed transport the core
    # declined to consume, and descending into one would hand the host a
    # reference from a path that never carried a wrapped value.
    groups: dict[type, list[Shape]] = {}

    for shape in shapes:
        groups.setdefault(_transport_type(shape), []).append(shape)

    for transport, group in groups.items():
        if len(group) == 1 or transport is dict:
            continue

        for shape in group:
            if shape.option_id() == discriminator:
                return shape

    return None


def _resolve_dict(shapes: tuple[Shape, ...], value: dict[str, Any],
                  resolver: _Resolver) -> Any:
    # decode() has already run, so a wrapper still standing is one the core
    # kept, and its payload is data like any other. A dict that merely resembles
    # a wrapper — on a path that never travels wrapped, or naming a branch that
    # does not — is malformed transport, and it travels intact for build() to
    # report. Nothing below it is walked and the resolver never sees it.
    if set(value) == {_TYPE, _VALUE}:
        branch = _kept_branch(shapes, value[_TYPE])

        if branch is None:
            return value

        return {_TYPE: value[_TYPE],
                _VALUE: _resolve((branch,), value[_VALUE], resolver)}

    structs = [s for s in shapes if type(s) is Struct]

    # Several dataclasses are told apart by an inline "$type", by the same
    # class name the core matches. The key itself is not a field: _resolve_fields
    # finds no field named "$type" and passes it through.
    if len(structs) > 1:
        structs = [s for s in structs if s.cls.__name__ == value.get(_TYPE)]

    if len(structs) == 1:
        return _resolve_fields(structs[0].fields, value, resolver)

    return value
