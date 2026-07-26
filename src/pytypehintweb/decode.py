from collections.abc import Callable
from datetime import date, time

from pytypehint import (
    Date, EnumShape, Float, Int, List, NoneShape, Signature, Str, Struct, Time,
)

# Reserved keys of the discriminated transport, mirrored from the core. A field
# can never carry them: field names must be identifiers, and neither is.
_TYPE = "$type"
_VALUE = "$value"


def decode(schema, data, *,
           file_resolver: Callable[[str], str] | None = None):
    # Prepare a JSON-parsed transport object for schema.build(). JSON collapses
    # 3.0 to 3 and carries a date or time as an ISO string, so decode walks the
    # schema and coerces int -> float and str -> date/time wherever the shape is
    # the only possible reading. Everything else passes through untouched.
    #
    # The shape decides, never the content: a str that looks like a date stays a
    # str unless the shape says otherwise. decode prepares, it does not validate;
    # a value the core will reject travels unchanged so build() reports it. The
    # returned dict is always new.
    #
    # file_resolver, when given, is called with the reference at every file node
    # reached and its return value continues down the pipeline, so a host can map
    # a reference to a path or an object-store key without decode knowing what
    # storage means. An exception it raises propagates unchanged.
    return _decode_fields(_fields_of(schema), data, file_resolver)


def _fields_of(schema):
    if type(schema) is Struct:
        return schema.fields

    if type(schema) is Signature:
        return schema.params

    raise TypeError(
        f"decode expects a compiled Signature or Struct, got "
        f"{type(schema).__name__}")


def _transport_type(shape):
    # The runtime type a value arrives as — a dataclass as a dict, anything else
    # as its pytype. This is the grouping the core uses to decide on a wrapper.
    return dict if type(shape) is Struct else shape.pytype


def _field_by_name(fields, name):
    for field in fields:
        if field.name == name:
            return field

    return None


def _decode_fields(fields, data, resolver):
    if type(data) is not dict:
        # Not the shape decode walks; build() reports the mismatch.
        return data

    result = {}

    for key, value in data.items():
        field = _field_by_name(fields, key)

        # An unknown key travels intact; rejecting it is build()'s job.
        result[key] = (value if field is None
                       else _decode_options(field.shape, value, resolver))

    return result


def _decode_options(shapes, value, resolver):
    # A None is a value, not a path to descend, so nothing below it — the file
    # resolver included — ever sees it. A field the transport omits entirely is
    # never reached at all: it takes its default.
    if value is None:
        return None

    if type(value) is dict:
        return _decode_dict(shapes, value, resolver)

    if type(value) is list:
        return _decode_list(shapes, value, resolver)

    if type(value) is str:
        return _decode_string(shapes, value, resolver)

    return _decode_scalar(shapes, value)


def _to_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        # Not an ISO date: pass intact, build() rejects it as the wrong type.
        return value


def _to_time(value):
    try:
        return time.fromisoformat(value)
    except ValueError:
        return value


def _to_enum_member(shape, value):
    try:
        # cls[name] resolves through __members__, so an alias returns its
        # canonical member. An unknown name passes intact for build() to reject.
        return shape.cls[value]
    except KeyError:
        return value


def _is_file(shape):
    return type(shape) is Str and shape.is_path_file is not None


def _decode_string(shapes, value, resolver):
    # The resolver only fires on an unambiguous file reading: a lone Str carrying
    # IsPathFile. Another Str competing for the path leaves the reference alone
    # rather than guessing. Whatever the host returns continues as the value.
    strings = [s for s in shapes if type(s) is Str]

    if resolver is not None and len(strings) == 1 and _is_file(strings[0]):
        return resolver(value)

    # A Str reading keeps a string a string. Otherwise convert only where a
    # single Date, Time or enum shape is the one reading; two of them competing
    # (date | time, date | Estado) is ambiguous, so it goes to the core intact.
    if strings:
        return value

    dates = [s for s in shapes if type(s) is Date]
    times = [s for s in shapes if type(s) is Time]
    enums = [s for s in shapes if type(s) is EnumShape]

    if (bool(dates) + bool(times) + bool(enums)) != 1:
        return value

    if len(dates) == 1:
        return _to_date(value)

    if len(times) == 1:
        return _to_time(value)

    if len(enums) == 1:
        return _to_enum_member(enums[0], value)

    return value


def _decode_scalar(shapes, value):
    # `type(value) is int` excludes bool, so a JSON true/false is never a number
    # here despite bool subclassing int.
    if type(value) is int:
        has_float = any(type(s) is Float for s in shapes)
        has_int = any(type(s) is Int for s in shapes)

        # Coerce only where Float is the single numeric reading; an Int in the
        # same position (int | float) is ambiguous and the core routes it.
        if has_float and not has_int:
            return float(value)

    return value


def _decode_list(shapes, value, resolver):
    lists = [s for s in shapes if type(s) is List]

    # A bare list only reaches here with a single List branch; a union of lists
    # collides on the transport type and travels wrapped instead.
    if len(lists) == 1:
        return [_decode_options(lists[0].item, item, resolver)
                for item in value]

    return value


def _decode_dict(shapes, value, resolver):
    # A dataclass can never carry $value, so it tells a wrapper from a struct.
    if _VALUE in value:
        return _decode_wrapped(shapes, value, resolver)

    if _TYPE in value:
        return _decode_inline_struct(shapes, value, resolver)

    return _decode_plain_struct(shapes, value, resolver)


def _decode_wrapped(shapes, value, resolver):
    # A wrapped payload is exactly {$type, $value}: anything that only resembles
    # one is malformed transport and travels intact for build() to report. The
    # exact-set check also keeps an explicit null payload distinct from an
    # absent $value, so value[_VALUE] below reads a real payload.
    if set(value) != {_TYPE, _VALUE}:
        return value

    # The wrapper is the wire format of a union, so a single-branch path never
    # travels wrapped: a wrapper there is malformed, not a value to unwrap.
    branches = [s for s in shapes if type(s) is not NoneShape]

    if len(branches) < 2:
        return value

    discriminator = value[_TYPE]

    selected = next(
        (s for s in branches if s.option_id() == discriminator),
        None)

    if selected is None:
        # Not a branch decode can name; build() reports it.
        return value

    inner = _decode_options((selected,), value[_VALUE], resolver)

    # The core only keeps the wrapper where several options share one runtime
    # type. int and float share a JSON number but not a Python type, so it
    # routes them bare and decode consumes the wrapper — the coerced payload
    # already carries the distinction. Otherwise the wrapper stays.
    group = [s for s in branches
             if _transport_type(s) == _transport_type(selected)]

    if len(group) == 1:
        return inner

    return {_TYPE: discriminator, _VALUE: inner}


def _decode_inline_struct(shapes, value, resolver):
    discriminator = value.get(_TYPE)

    struct = next(
        (s for s in shapes
         if type(s) is Struct and s.option_id() == discriminator),
        None)

    if struct is None:
        return value

    return _decode_struct(struct, value, resolver)


def _decode_plain_struct(shapes, value, resolver):
    structs = [s for s in shapes if type(s) is Struct]

    if len(structs) == 1:
        return _decode_struct(structs[0], value, resolver)

    return value


def _decode_struct(struct, value, resolver):
    result = {}

    for key, item in value.items():
        # $type is the discriminator of an inline struct, not a field; it stays.
        if key == _TYPE:
            result[key] = item
            continue

        field = _field_by_name(struct.fields, key)
        result[key] = (item if field is None
                       else _decode_options(field.shape, item, resolver))

    return result
