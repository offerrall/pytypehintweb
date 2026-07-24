from datetime import date, time

from pytypehint import (
    Date, EnumShape, Float, Int, List, NoneShape, Signature, Str, Struct, Time,
)

# The reserved keys of the discriminated transport, mirrored from the core. A
# field can never carry them: field names must be identifiers, and neither is.
_TYPE = "$type"
_VALUE = "$value"


def decode(schema, data):
    # Prepare a JSON-parsed transport object for schema.build(). Some values the
    # transport cannot express by the exact type the core demands: JSON and the
    # browser collapse 3.0 to 3, so an int arrives where a float is wanted; and a
    # date or a time travels as an ISO string where a date/time object is wanted.
    # decode walks the schema shapes and, guided by the shape at each path,
    # coerces int -> float and str -> date/time wherever that shape is the only
    # possible reading. Everything else passes through untouched.
    #
    # It never guesses from a value's content: a string is turned into a date only
    # because the shape (or an explicit $type) says so, never because it "looks
    # like" one. decode prepares, it does not validate — a value the core will
    # reject passes through unchanged so build() reports it with its own error.
    # The returned dict is always new; the input is never mutated.
    return _decode_fields(_fields_of(schema), data)


def _fields_of(schema):
    if type(schema) is Struct:
        return schema.fields

    if type(schema) is Signature:
        return schema.params

    raise TypeError(
        f"decode expects a compiled Signature or Struct, got "
        f"{type(schema).__name__}")


def _transport_type(shape):
    # The runtime type a value arrives as: every dataclass arrives as a dict,
    # every other shape as its own pytype. This is the grouping the core uses to
    # decide whether a wrapper is required.
    return dict if type(shape) is Struct else shape.pytype


def _field_by_name(fields, name):
    for field in fields:
        if field.name == name:
            return field

    return None


def _decode_fields(fields, data):
    if type(data) is not dict:
        # Not the shape decode walks; build() reports the mismatch.
        return data

    result = {}

    for key, value in data.items():
        field = _field_by_name(fields, key)

        # An unknown key is not decode's to interpret; it travels intact and
        # build() rejects it.
        result[key] = (value if field is None
                       else _decode_options(field.shape, value))

    return result


def _decode_options(shapes, value):
    if value is None:
        return None

    if type(value) is dict:
        return _decode_dict(shapes, value)

    if type(value) is list:
        return _decode_list(shapes, value)

    if type(value) is str:
        return _decode_string(shapes, value)

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
        # cls[name] resolves through __members__, so an alias name returns its
        # canonical member. A name that does not exist raises KeyError: pass it
        # intact, build() rejects it as the wrong type. decode never validates.
        return shape.cls[value]
    except KeyError:
        return value


def _decode_string(shapes, value):
    # A Str reading keeps a string a string: only convert where a single Date,
    # Time or enum shape is the unambiguous reading and no Str competes. The
    # content of the string is never inspected — a str that "looks like" a date
    # stays a str, and a name is turned into a member only because the shape says
    # so. When more than one string-transport shape reads the path (date | time,
    # date | Estado), the reading is ambiguous, so decode leaves it for the core.
    has_str = any(type(s) is Str for s in shapes)

    if has_str:
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
    # bool is a subtype of int in Python, but `type(value) is int` already
    # excludes it: a JSON true/false is never a number here.
    if type(value) is int:
        has_float = any(type(s) is Float for s in shapes)
        has_int = any(type(s) is Int for s in shapes)

        # Coerce only where Float is the single numeric reading. An Int in the
        # same position (int | float) makes a bare number ambiguous, so decode
        # leaves it for the core to route by exact type.
        if has_float and not has_int:
            return float(value)

    return value


def _decode_list(shapes, value):
    lists = [s for s in shapes if type(s) is List]

    # A bare list only reaches here when a single List branch reads the path; a
    # union of lists collides on the transport type and travels wrapped instead.
    if len(lists) == 1:
        return [_decode_options(lists[0].item, item) for item in value]

    return value


def _decode_dict(shapes, value):
    # $value is the reserved payload key of the discriminated wrapper; a
    # dataclass can never carry it, so it tells a wrapper from an inline struct.
    if _VALUE in value:
        return _decode_wrapped(shapes, value)

    if _TYPE in value:
        return _decode_inline_struct(shapes, value)

    return _decode_plain_struct(shapes, value)


def _decode_wrapped(shapes, value):
    # A wrapped payload is exactly {$type, $value} — no missing key, no extra
    # key. A dict that only resembles one (a missing $value, an unexpected key,
    # an unknown discriminator, or a wrapper where the schema never asks for one)
    # is malformed transport, not decode's to repair: it travels intact so
    # build() reports it. The exact-set check keeps an explicit null payload
    # ({"$type": t, "$value": null}) distinct from an absent $value — the routing
    # in _decode_dict never reaches here without $value, and value[_VALUE] then
    # reads the real payload rather than conflating null with absence.
    if set(value) != {_TYPE, _VALUE}:
        return value

    # The wrapper is the wire format of a union. A single-branch path never
    # travels wrapped, so a wrapper there is malformed, not a value to unwrap.
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

    inner = _decode_options((selected,), value[_VALUE])

    # The wrapper is the adapter's wire format. The core keeps it only where it
    # sees a genuine collision — several options sharing one runtime type. int
    # and float share a JSON number but not a Python type, so the core routes
    # them bare: decode consumes the wrapper, turning $type into the real type
    # distinction the coerced payload already answers. Where the core does keep
    # the wrapper (list | list, ...), decode keeps it and only prepares $value.
    group = [s for s in branches
             if _transport_type(s) == _transport_type(selected)]

    if len(group) == 1:
        return inner

    return {_TYPE: discriminator, _VALUE: inner}


def _decode_inline_struct(shapes, value):
    discriminator = value.get(_TYPE)

    struct = next(
        (s for s in shapes
         if type(s) is Struct and s.option_id() == discriminator),
        None)

    if struct is None:
        return value

    return _decode_struct(struct, value)


def _decode_plain_struct(shapes, value):
    structs = [s for s in shapes if type(s) is Struct]

    if len(structs) == 1:
        return _decode_struct(structs[0], value)

    return value


def _decode_struct(struct, value):
    result = {}

    for key, item in value.items():
        # $type is the discriminator of an inline struct, not a field; it stays.
        if key == _TYPE:
            result[key] = item
            continue

        field = _field_by_name(struct.fields, key)
        result[key] = (item if field is None
                       else _decode_options(field.shape, item))

    return result
