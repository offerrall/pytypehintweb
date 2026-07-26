import re
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from datetime import date, time, timedelta
from types import FunctionType

from pytypehint import (
    MISSING, Bool, Date, EnumShape, Float, Int, List, NoneShape, Signature,
    Str, Struct, Time, signature_of, struct_of,
)

_PLAN_VERSION = 1

_MAX_SAFE_INT = 2 ** 53 - 1
_MIN_SAFE_INT = -_MAX_SAFE_INT


_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")

_WITH_VALUE = (
    "str_min_message",
    "str_max_message",
    "int_min_message",
    "int_max_message",
    "int_multiple_of_message",
    "float_min_message",
    "float_max_message",
    "date_min_message",
    "date_max_message",
    "time_min_message",
    "time_max_message",
    "list_min_message",
    "list_max_message",
    "file_min_message",
    "file_max_message",
)

_NO_PLACEHOLDER = (
    "list_add_label",
    "list_remove_label",
    "list_item_label",
    "mode_previous_label",
    "mode_next_label",
    "int_increase_label",
    "int_decrease_label",
    "file_current_remove_label",
    "file_current_replace_label",
    "file_current_restore_label",
)


def _reject_doubled_braces(name: str, text: str) -> None:
    # "{{value}}" and "}}" are not an escaped literal brace here: templates take
    # only bare {value} / {current} / {total} placeholders. Name the real cause
    # rather than reporting a vaguer "unbalanced braces".
    if "{{" in text or "}}" in text:
        raise TypeError(
            f"WebConfig.{name} contains an invalid or escaped placeholder form "
            f"(doubled braces are not supported): {text!r}")


def _check_template(name: str, text: str, *, needs_value: bool) -> None:
    _reject_doubled_braces(name, text)

    found = _PLACEHOLDER.findall(text)
    rest = _PLACEHOLDER.sub("", text)

    if "{" in rest or "}" in rest:
        raise TypeError(
            f"WebConfig.{name} has unbalanced braces: {text!r}")

    if not needs_value:
        if found:
            raise TypeError(
                f"WebConfig.{name} must not contain placeholders, got {text!r}")
        return

    if found != ["value"]:
        raise TypeError(
            f"WebConfig.{name} must contain exactly one {{value}} placeholder "
            f"and no other placeholders, got {text!r}")


def _check_position_template(name: str, text: str) -> None:
    _reject_doubled_braces(name, text)

    found = _PLACEHOLDER.findall(text)
    rest = _PLACEHOLDER.sub("", text)

    if "{" in rest or "}" in rest:
        raise TypeError(
            f"WebConfig.{name} has unbalanced braces: {text!r}")

    if sorted(found) != ["current", "total"]:
        raise TypeError(
            f"WebConfig.{name} must contain exactly one {{current}} and one "
            f"{{total}} placeholder, got {text!r}")


@dataclass(frozen=True, kw_only=True)
class WebConfig:
    list_add_label: str = "Add"
    list_remove_label: str = "Remove"
    list_item_label: str = "Item"
    str_min_message: str = "Must contain at least {value} characters"
    str_max_message: str = "Must contain at most {value} characters"
    str_pattern_message: str = "Invalid format"
    int_safe_message: str = "Must be a safe integer"
    int_invalid_message: str = "Enter a valid integer"
    int_min_message: str = "Must be at least {value}"
    int_max_message: str = "Must be at most {value}"
    int_multiple_of_message: str = "Must be a multiple of {value}"
    int_increase_label: str = "Increase"
    int_decrease_label: str = "Decrease"
    float_invalid_message: str = "Enter a valid number"
    float_finite_message: str = "Must be a finite number"
    float_min_message: str = "Must be at least {value}"
    float_max_message: str = "Must be at most {value}"
    date_invalid_message: str = "Enter a valid date"
    date_min_message: str = "Must be on or after {value}"
    date_max_message: str = "Must be on or before {value}"
    time_invalid_message: str = "Enter a valid time"
    time_min_message: str = "Must be at or after {value}"
    time_max_message: str = "Must be at or before {value}"
    list_min_message: str = "Add at least {value} items"
    list_max_message: str = "Keep at most {value} items"
    mode_previous_label: str = "Previous mode"
    mode_next_label: str = "Next mode"
    mode_position_label: str = "Mode {current} of {total}"
    file_invalid_message: str = "Not an accepted file type"
    file_min_message: str = "Add at least {value} files"
    file_max_message: str = "Keep at most {value} files"
    file_current_label: str = "Current file: {value}"
    file_current_remove_label: str = "Remove current file"
    file_current_replace_label: str = "Replace file"
    file_current_restore_label: str = "Restore current file"

    def __post_init__(self):
        for f in dataclass_fields(self):
            value = getattr(self, f.name)

            if type(value) is not str:
                raise TypeError(
                    f"WebConfig.{f.name} must be str, "
                    f"got {type(value).__name__}")

            if f.name == "mode_position_label":
                _check_position_template(f.name, value)
            elif f.name == "file_current_label":
                # A label carrying the chosen file's name in its one {value}.
                _check_template(f.name, value, needs_value=True)
            elif f.name in _NO_PLACEHOLDER:
                # These are button/accessible labels: plain, non-empty text with
                # no placeholders the widget could not fill.
                if value == "":
                    raise TypeError(f"WebConfig.{f.name} must not be empty")
                _check_template(f.name, value, needs_value=False)
            elif f.name.endswith("_message"):
                _check_template(f.name, value,
                                needs_value=f.name in _WITH_VALUE)


PLAIN = "plain"
INLINE = "inline"
WRAPPED = "wrapped"

_FLOAT_UNSUPPORTED = ("slider",)

# On a file field (a Str carrying IsPathFile) the other Str atoms describe a text
# box and have no meaning on a file control, so any of them alongside IsPathFile
# is deferred until a real case asks for it. The core allows the combination; the
# adapter, like Float.slider, simply does not emit it yet.
_FILE_UNSUPPORTED = ("min", "max", "pattern", "choices", "is_password", "rows",
                     "placeholder")

# A JSON number carries no evidence of whether it was an int or a float; on the
# wire 3 and 3.0 are the same token. Grouping union branches by this sentinel
# instead of by Python type makes int and float collide, so both travel wrapped
# with a $type the browser can round-trip. See docs/plan.md (Union transport).
_JSON_NUMBER = "number"

# str, date and time all travel as a JSON string (date and time as ISO text), so
# they collide on the wire the same way int and float do. Any union mixing two of
# them wraps every string branch with a $type the browser can round-trip.
_JSON_STRING = "string"

_UNPORTABLE_ESCAPES = "dDwWsSbBAZzG"

_LITERAL_ESCAPES = "^$\\.*+?()[]{}|/"

_CONTROL_ESCAPES = "nrtfv"

_HEX_DIGITS = "0123456789abcdefABCDEF"

_HEX_ESCAPES = {"x": 2, "u": 4}

_SURROGATES = range(0xD800, 0xE000)

_DOT_REASON = "the unescaped dot has different line-terminator semantics"

_LOOSE_BRACKET_REASON = "an unescaped ] outside a character class"

_LEADING_BRACKET_REASON = "a literal ] as the first member of a character class"

_LOOSE_OPEN_BRACE_REASON = "an unescaped { that is not a supported quantifier"

_LOOSE_CLOSE_BRACE_REASON = "an unescaped } outside a character class"

_UNCLOSED_CLASS_REASON = "an unclosed character class"

_UNPORTABLE_GROUPS = (
    ("(?P", "Python named groups and backreferences"),
    ("(?>", "atomic groups"),
    ("(?<=", "lookbehind"),
    ("(?<!", "negative lookbehind"),
    ("(?#", "inline comments"),
    ("(?(", "conditional matching"),
)

_INLINE_FLAGS = re.compile(r"\(\?(?:[aiLmsux]*-[aiLmsux]+|[aiLmsux]+)[:)]")

_BRACE_QUANTIFIER = re.compile(r"\{\d+(?:,\d*)?\}")

_QUANTIFIERS = "*+?"

_QUANTIFIED_LOOKAHEAD_REASON = "a quantified lookahead"

_LOOKAHEAD_PREFIXES = ("(?=", "(?!")

_GROUP_PREFIX = "(?:"


def _starts_quantifier(pattern: str, index: int) -> bool:
    if index >= len(pattern):
        return False

    if pattern[index] in _QUANTIFIERS:
        return True

    return _BRACE_QUANTIFIER.match(pattern, index) is not None


def _error(path: str, message: str) -> TypeError:
    return TypeError(f"{path}: {message}")


def _reject(shape, names, path: str) -> None:
    for name in names:
        if getattr(shape, name) is not None:
            raise _error(
                path, f"{type(shape).__name__}.{name} is not supported yet")


def _group_reason(pattern: str, start: int) -> str | None:
    for token, reason in _UNPORTABLE_GROUPS:
        if pattern.startswith(token, start):
            return reason

    if _INLINE_FLAGS.match(pattern, start):
        return "inline flags"

    return None


def _escape_reason(pattern: str, index: int,
                   in_class: bool) -> tuple[str | None, int]:
    escaped = pattern[index + 1]

    if escaped in _UNPORTABLE_ESCAPES:
        return f"the \\{escaped} escape", index

    if escaped == "N" and pattern.startswith("{", index + 2):
        return "the \\N{...} escape", index

    if escaped in _LITERAL_ESCAPES or escaped in _CONTROL_ESCAPES:
        return None, index + 2

    if escaped == "-" and in_class:
        return None, index + 2

    if escaped in _HEX_ESCAPES:
        start = index + 2
        end = start + _HEX_ESCAPES[escaped]
        digits = pattern[start:end]

        if len(digits) == end - start and all(d in _HEX_DIGITS for d in digits):
            if int(digits, 16) in _SURROGATES:
                return f"the surrogate escape \\{escaped}{digits}", index

            return None, end

    return f"the \\{escaped} escape", index


def _pattern_reason(pattern: str) -> str | None:
    index = 0
    in_class = False
    class_start = -1
    quantifier_end = -1
    groups: list[str] = []

    while index < len(pattern):
        char = pattern[index]

        if char == "\\":
            if index + 1 == len(pattern):
                return "a trailing backslash"

            reason, index = _escape_reason(pattern, index, in_class)

            if reason is not None:
                return reason

            continue

        if in_class:
            if char == "]":
                if index == class_start:
                    return _LEADING_BRACKET_REASON

                in_class = False

            index += 1
            continue

        if char == "[":
            in_class = True
            class_start = index + 1

            if pattern.startswith("^", class_start):
                class_start += 1

            index += 1
            continue

        if char == "]":
            return _LOOSE_BRACKET_REASON

        if char == "}":
            return _LOOSE_CLOSE_BRACE_REASON

        if char == ".":
            return _DOT_REASON

        if char == "(":
            reason = _group_reason(pattern, index)

            if reason is not None:
                return reason

            # Track the group kind so a quantifier on a lookahead can be
            # rejected when the group closes. After _group_reason(), a "(?"
            # is a lookahead or a non-capturing group; anything else opens a
            # capturing group.
            if pattern.startswith(_LOOKAHEAD_PREFIXES, index):
                groups.append("lookahead")
                index += 3
            elif pattern.startswith(_GROUP_PREFIX, index):
                groups.append("group")
                index += 3
            else:
                groups.append("group")
                index += 1

            continue

        if char == ")":
            kind = groups.pop() if groups else "group"
            index += 1

            if kind == "lookahead" and _starts_quantifier(pattern, index):
                return _QUANTIFIED_LOOKAHEAD_REASON

            continue

        if char == "+" and index == quantifier_end:
            return "possessive quantifiers"

        if char in _QUANTIFIERS:
            index += 1
            quantifier_end = index
            continue

        if char == "{":
            match = _BRACE_QUANTIFIER.match(pattern, index)

            if match is None:
                return _LOOSE_OPEN_BRACE_REASON

            index = match.end()
            quantifier_end = index
            continue

        index += 1

    if in_class:
        return _UNCLOSED_CLASS_REASON

    return None


def _check_javascript_pattern(pattern: str, path: str) -> None:
    reason = _pattern_reason(pattern)

    if reason is None:
        return

    raise _error(
        path,
        f"Pattern {pattern!r} is valid in pytypehint but {reason} is outside "
        f"the portable RegExp subset supported by pytypehintweb")


def _transport_group(shape):
    # The transport type a value arrives as, which is what decides collisions in
    # a union. A dataclass is a dict and keeps that identity so the inline form
    # can route it by an in-object $type. int and float share one JSON number
    # token; str, date and time share one JSON string token; each shared group
    # goes wrapped. A number and a string stay distinct, so str | int is
    # untouched, while str | date and date | time collide.
    if type(shape) is Struct:
        return dict

    # An enum member travels as its name, a JSON string, so it joins the string
    # group and collides with str, date, time and other enums the same way. Its
    # pytype is the enum class, not str, so this is decided by shape, not pytype.
    if type(shape) is EnumShape:
        return _JSON_STRING

    if shape.pytype in (int, float):
        return _JSON_NUMBER

    if shape.pytype in (str, date, time):
        return _JSON_STRING

    return shape.pytype


def _modes(shapes) -> list[str]:
    groups: dict[object, list[int]] = {}
    for i, shape in enumerate(shapes):
        groups.setdefault(_transport_group(shape), []).append(i)

    modes = [PLAIN] * len(shapes)

    for group_key, group in groups.items():
        if len(group) == 1:
            continue
        for i in group:
            modes[i] = INLINE if group_key is dict else WRAPPED

    return modes


def _is_safe(value) -> bool:
    return _MIN_SAFE_INT <= value <= _MAX_SAFE_INT


def _safe_int(value, path: str, what: str) -> int:
    if not _is_safe(value):
        raise _error(
            path,
            f"{what}: {value} is valid in pytypehint but cannot be "
            f"represented exactly by pytypehintweb; JavaScript safe integer "
            f"range is {_MIN_SAFE_INT} to {_MAX_SAFE_INT}")

    return value


def _bound(bound, delta, path: str, what: str):
    if bound is None:
        return None

    if not bound.exclusive:
        return _safe_int(bound.value, path, what)

    inclusive = bound.value + delta

    if not _is_safe(inclusive):
        raise _error(
            path,
            f"{what} exclusive bound {bound.value} requires the inclusive "
            f"value {inclusive}, which is outside the JavaScript safe "
            f"integer range")

    return inclusive


def _inclusive_length(bound, path: str, what: str):
    # String and list length bounds are inclusive in the browser contract. The
    # core rejects exclusive length bounds, so a compiled schema never carries
    # one; the adapter still refuses one defensively rather than reading .value
    # and silently dropping .exclusive, which would weaken the bound.
    if bound is None:
        return None

    if bound.exclusive:
        raise _error(
            path,
            f"{what}: exclusive length bounds are not supported; a browser "
            f"length bound is inclusive")

    return _safe_int(bound.value, path, what)


def _mod_inverse(value: int, modulus: int) -> int:
    old, current = value % modulus, modulus
    old_coeff, coeff = 1, 0

    while current:
        quotient = old // current
        old, current = current, old - quotient * current
        old_coeff, coeff = coeff, old_coeff - quotient * coeff

    return old_coeff % modulus


def _slider_reaches(minimum: int, maximum: int, step: int, multiple: int) -> bool:
    from math import gcd

    divisor = gcd(step, multiple)

    if minimum % divisor != 0:
        return False

    modulus = multiple // divisor

    if modulus == 1:
        steps = 0
    else:
        steps = ((-minimum // divisor) % modulus
                 * _mod_inverse(step // divisor, modulus)) % modulus

    return minimum + steps * step <= maximum


def _check_slider(minimum, maximum, step, multiple, path: str) -> None:
    if minimum is None or maximum is None:
        raise _error(path, "Int.slider requires both min and max")

    if multiple is None:
        return

    stride = 1 if step is None else step

    if not _slider_reaches(minimum, maximum, stride, multiple):
        raise _error(
            path,
            f"Int.slider has no reachable position between {minimum} and "
            f"{maximum} stepping by {stride} that is a multiple of {multiple}")


def _incompatible(path: str, name: str, first: str, second: str) -> None:
    raise _error(
        path,
        f"{name}: {first} and {second} ask for different controls; "
        f"pytypehintweb will not pick one silently")


def _is_file_shape(shape) -> bool:
    return type(shape) is Str and shape.is_path_file is not None


def _is_multiple_file_shape(shape) -> bool:
    # list[File]: a List whose sole item is a file. It becomes one `multiple` file
    # node, not a generic list of single-file widgets.
    return (type(shape) is List and len(shape.item) == 1
            and _is_file_shape(shape.item[0]))


def _contains_file(shapes) -> bool:
    # A file reached anywhere below a list item that is not a bare list[File] — an
    # optional item, a union, a nested list, a dataclass field. These combinations
    # are deferred until a real case asks for them.
    for shape in shapes:
        if _is_file_shape(shape):
            return True
        if type(shape) is List and _contains_file(shape.item):
            return True
        if type(shape) is Struct and any(
                _contains_file(f.shape) for f in shape.fields):
            return True
    return False


def _file_node(shape, config, path: str) -> dict:
    # IsPathFile turns a Str into a file field. The value is a reference string the
    # browser widget generates locally from the chosen file (its name slugged to
    # bare ASCII, a UUID and its extension); the core certifies it only by
    # extension (an honest-mistake filter
    # over value.lower().endswith(ext), never a check that bytes exist). extensions
    # is possibly empty (any file); it maps to the input's accept attribute. A file
    # carries no default — its reference comes from the user's choice — so a
    # default on a file field is rejected (see _field_node / _plain_value). Nothing
    # about transport or decode() changes: a file field is a str on the wire.
    #
    # `multiple` is always present (false here, true for list[File]); minFiles /
    # maxFiles are null on a single file and carry the list's Min / Max on a
    # multiple one. currentLabel / currentRemoveLabel / currentReplaceLabel drive
    # the "current file" display setValue() puts the widget into (see
    # docs/javascript.md).
    for name in _FILE_UNSUPPORTED:
        if getattr(shape, name) is not None:
            raise _error(
                path, f"Str.{name} with IsPathFile is not supported yet")

    return {
        "kind": "file",
        "options": {
            "extensions": list(shape.is_path_file.extensions),
            "invalidMessage": config.file_invalid_message,
            "multiple": False,
            "minFiles": None,
            "maxFiles": None,
            "minMessage": config.file_min_message,
            "maxMessage": config.file_max_message,
            "currentLabel": config.file_current_label,
            "currentRemoveLabel": config.file_current_remove_label,
            "currentReplaceLabel": config.file_current_replace_label,
            "currentRestoreLabel": config.file_current_restore_label,
        },
    }


def _multiple_file_node(shape, config, path: str) -> dict:
    # list[File]: one `multiple` file node. The list's Min / Max become file-count
    # bounds; a default on the list is rejected the same as on a single file.
    node = _file_node(shape.item[0], config, path)

    min_files = _inclusive_length(shape.min, path, "List.min")
    max_files = _inclusive_length(shape.max, path, "List.max")

    if (min_files is not None and max_files is not None
            and min_files > max_files):
        raise _error(
            path,
            "List min and max leave no representable length; the converted "
            "length bounds form an empty range")

    node["options"]["multiple"] = True
    node["options"]["minFiles"] = min_files
    node["options"]["maxFiles"] = max_files

    return node


def _str_node(shape, config, path: str) -> dict:
    if shape.is_path_file is not None:
        return _file_node(shape, config, path)

    password = shape.is_password is not None
    rows = shape.rows.value if shape.rows else None
    choices = list(shape.choices.values) if shape.choices else None

    if choices is not None and password:
        _incompatible(path, "Str", "Choices", "IsPassword")

    if choices is not None and rows is not None:
        _incompatible(path, "Str", "Choices", "Rows")

    if rows is not None and password:
        _incompatible(path, "Str", "Rows", "IsPassword")

    if rows is not None:
        _safe_int(rows, path, "Str.rows")

    pattern_message = config.str_pattern_message

    if shape.pattern is not None:
        _check_javascript_pattern(shape.pattern.value, path)
        if shape.pattern.message is not None:
            pattern_message = shape.pattern.message

    placeholder = shape.placeholder.value if shape.placeholder else None

    if choices is not None and placeholder is not None:
        _incompatible(path, "Str", "Choices", "Placeholder")

    min_length = _inclusive_length(shape.min, path, "Str.min")
    max_length = _inclusive_length(shape.max, path, "Str.max")

    if (min_length is not None and max_length is not None
            and min_length > max_length):
        raise _error(
            path,
            "Str min and max leave no representable length; the converted "
            "length bounds form an empty range")

    pattern = shape.pattern.value if shape.pattern else None

    return {
        "kind": "str",
        "options": {
            "minLength": min_length,
            "maxLength": max_length,
            "pattern": pattern,
            "patternMessage": pattern_message,
            "minMessage": config.str_min_message,
            "maxMessage": config.str_max_message,
            "placeholder": placeholder,
            "password": password,
            "rows": rows,
            "choices": choices,
        },
    }


def _int_node(shape, config, path: str) -> dict:
    choices = ([_safe_int(v, path, "Int.choices") for v in shape.choices.values]
               if shape.choices else None)
    slider = shape.slider is not None

    if choices is not None and slider:
        _incompatible(path, "Int", "Choices", "Slider")

    placeholder = shape.placeholder.value if shape.placeholder else None

    if choices is not None and placeholder is not None:
        _incompatible(path, "Int", "Choices", "Placeholder")

    if slider and placeholder is not None:
        _incompatible(path, "Int", "Slider", "Placeholder")

    minimum = _bound(shape.min, 1, path, "Int.min")
    maximum = _bound(shape.max, -1, path, "Int.max")

    if minimum is not None and maximum is not None and minimum > maximum:
        raise _error(
            path,
            "Int min and max leave no representable value; the exclusive "
            "integer bounds convert to an empty range")

    multiple_of = (_safe_int(shape.multiple_of.value, path, "Int.multiple_of")
                   if shape.multiple_of else None)
    step = _safe_int(shape.step.value, path, "Int.step") if shape.step else None

    # An ordinary range whose bounds admit no multiple of multiple_of is already
    # rejected by the core when it compiles the schema (Int.__post_init__:
    # "no multiple of {m} in range"), so the adapter does not re-check it. The
    # slider grid is the adapter's own concern and stays.
    if slider:
        _check_slider(minimum, maximum, step, multiple_of, path)

    return {
        "kind": "int",
        "options": {
            "min": minimum,
            "max": maximum,
            "multipleOf": multiple_of,
            "step": step,
            "slider": slider,
            "showValue": bool(slider and shape.slider.show_value),
            "placeholder": placeholder,
            "choices": choices,
            "safeMessage": config.int_safe_message,
            "invalidMessage": config.int_invalid_message,
            "minMessage": config.int_min_message,
            "maxMessage": config.int_max_message,
            "multipleOfMessage": config.int_multiple_of_message,
            "increaseLabel": config.int_increase_label,
            "decreaseLabel": config.int_decrease_label,
        },
    }


def _float_node(shape, config, path: str) -> dict:
    _reject(shape, _FLOAT_UNSUPPORTED, path)

    choices = (list(shape.choices.values) if shape.choices else None)
    placeholder = shape.placeholder.value if shape.placeholder else None

    if choices is not None and placeholder is not None:
        _incompatible(path, "Float", "Choices", "Placeholder")

    # No conversion: the core compares a float directly against its bound and its
    # flag, and every finite double is representable in the browser, so the value
    # travels as is with the exclusive flag beside it. The empty range the core
    # rejects at compile time is never re-checked here.
    minimum = shape.min.value if shape.min else None
    maximum = shape.max.value if shape.max else None

    step = shape.step.value if shape.step else None

    return {
        "kind": "float",
        "options": {
            "min": minimum,
            "max": maximum,
            "minExclusive": shape.min.exclusive if shape.min else False,
            "maxExclusive": shape.max.exclusive if shape.max else False,
            "step": step,
            "choices": choices,
            "placeholder": placeholder,
            "invalidMessage": config.float_invalid_message,
            "finiteMessage": config.float_finite_message,
            "minMessage": config.float_min_message,
            "maxMessage": config.float_max_message,
            "increaseLabel": config.int_increase_label,
            "decreaseLabel": config.int_decrease_label,
        },
    }


def _date_bound(bound, delta_days: int):
    # Like Int, an exclusive date bound converts to the neighbouring inclusive
    # one: strictly-after becomes on-or-after the next day, and symmetrically for
    # max. The core rejects an exclusive bound at the calendar edge, so the
    # neighbour always exists by the time a compiled schema reaches here.
    if bound is None:
        return None

    value = bound.value

    if bound.exclusive:
        value = value + timedelta(days=delta_days)

    return value.isoformat()


def _date_node(shape, config, path: str) -> dict:
    choices = ([v.isoformat() for v in shape.choices.values]
               if shape.choices else None)
    placeholder = shape.placeholder.value if shape.placeholder else None

    if choices is not None and placeholder is not None:
        _incompatible(path, "Date", "Choices", "Placeholder")

    return {
        "kind": "date",
        "options": {
            "min": _date_bound(shape.min, 1),
            "max": _date_bound(shape.max, -1),
            "placeholder": placeholder,
            "choices": choices,
            "invalidMessage": config.date_invalid_message,
            "minMessage": config.date_min_message,
            "maxMessage": config.date_max_message,
        },
    }


def _time_node(shape, config, path: str) -> dict:
    choices = ([v.isoformat() for v in shape.choices.values]
               if shape.choices else None)
    placeholder = shape.placeholder.value if shape.placeholder else None

    if choices is not None and placeholder is not None:
        _incompatible(path, "Time", "Choices", "Placeholder")

    # Time carries the exclusive flag like Float: the core compares directly with
    # no conversion (there is no natural ±1 for a clock), so the bound travels as
    # canonical ISO text with its flag beside it and the widget compares
    # lexicographically. The empty range the core rejects at compile time — which
    # includes equal bounds with an exclusive side — is never re-checked here.
    return {
        "kind": "time",
        "options": {
            "min": shape.min.value.isoformat() if shape.min else None,
            "max": shape.max.value.isoformat() if shape.max else None,
            "minExclusive": shape.min.exclusive if shape.min else False,
            "maxExclusive": shape.max.exclusive if shape.max else False,
            "placeholder": placeholder,
            "choices": choices,
            "invalidMessage": config.time_invalid_message,
            "minMessage": config.time_min_message,
            "maxMessage": config.time_max_message,
        },
    }


def _enum_node(shape, config, path: str) -> dict:
    # An enum is a closed set of members. Each travels as its name (.name), in
    # declaration order — list(cls) yields only canonical members, so an alias
    # never appears twice. The name, never the value, is the transport: a value
    # can be anything, repeat across aliases, or not serialize.
    #
    # choices is always non-empty (the core rejects an empty enum). placeholder
    # is always null: an enum is a closed select that always holds a value (the
    # default or the first member), never empty, never in error, so there is
    # nothing to prompt for; the key exists only for structural symmetry with the
    # other scalars. labels is the reserved slot for member labels a future Extra
    # vocabulary would supply; it is always null today. Extra is not interpreted.
    return {
        "kind": "enum",
        "options": {
            "choices": [member.name for member in shape.cls],
            "placeholder": None,
            "labels": None,
        },
    }


def _shape_node(shape, config, path: str) -> dict:
    if type(shape) is Str:
        return _str_node(shape, config, path)

    if type(shape) is EnumShape:
        return _enum_node(shape, config, path)

    if type(shape) is Int:
        return _int_node(shape, config, path)

    if type(shape) is Float:
        return _float_node(shape, config, path)

    if type(shape) is Date:
        return _date_node(shape, config, path)

    if type(shape) is Time:
        return _time_node(shape, config, path)

    if type(shape) is Bool:
        # Bool has no configurable atoms, so its node carries an empty options
        # object: present and validated as an object, but with no keys.
        return {"kind": "bool", "options": {}}

    if type(shape) is List:
        # list[File] is one `multiple` file node, not a generic list of file
        # widgets. A file anywhere else inside a list is deferred.
        if _is_multiple_file_shape(shape):
            return _multiple_file_node(shape, config, path)

        if _contains_file(shape.item):
            raise _error(
                path,
                "a file inside a list is only supported as a plain list[File]; "
                "this combination is not supported yet")

        min_items = _inclusive_length(shape.min, path, "List.min")
        max_items = _inclusive_length(shape.max, path, "List.max")

        if (min_items is not None and max_items is not None
                and min_items > max_items):
            raise _error(
                path,
                "List min and max leave no representable length; the converted "
                "length bounds form an empty range")

        return {
            "kind": "list",
            "addLabel": config.list_add_label,
            "removeLabel": config.list_remove_label,
            "minItems": min_items,
            "maxItems": max_items,
            "minMessage": config.list_min_message,
            "maxMessage": config.list_max_message,
            "item": _options_node(shape.item, config, f"{path}.item", item=True),
        }

    if type(shape) is Struct:
        if not shape.fields:
            raise _error(
                path,
                f"{shape.cls.__name__} has no fields: pytypehintweb cannot "
                f"build a nested object without controls")

        return {
            "kind": "object",
            "fields": [_field_node(f, config, path) for f in shape.fields],
        }

    raise _error(path, f"{type(shape).__name__} is not supported yet")


def _check_branches(shapes, path: str) -> None:
    # option_id() is the wrapper $type the browser and decode() read to tell
    # branches apart, so two branches sharing one are unroutable. Since core 0.0.5
    # _check_discriminators rejects the collision the normal Field path can produce
    # (homonym enums or dataclasses in a union) before a compiled schema reaches
    # here; the adapter keeps this guard as defense in depth against future
    # relaxations of that core rule and shapes assembled off the normal path.
    seen = set()

    for shape in shapes:
        option_id = shape.option_id()

        if option_id in seen:
            raise _error(
                path,
                f"two branches share the option id {option_id!r}: "
                f"pytypehintweb cannot tell them apart")

        seen.add(option_id)


def _options_node(shapes, config, path: str, *, item: bool = False) -> dict:
    real = [s for s in shapes if type(s) is not NoneShape]
    optional = len(real) != len(shapes)

    if not real:
        raise _error(path, "a union needs at least one branch that is not None")

    if len(real) == 1:
        node = _shape_node(real[0], config, path)
    else:
        _check_branches(real, path)
        node = {
            "kind": "choice",
            "previousLabel": config.mode_previous_label,
            "nextLabel": config.mode_next_label,
            "positionLabel": config.mode_position_label,
            "branches": [
                {
                    "value": shape.option_id(),
                    "mode": mode,
                    "node": _shape_node(shape, config,
                                        f"{path}[{shape.option_id()}]"),
                }
                for shape, mode in zip(real, _modes(real))
            ],
        }

    if optional and item:
        return {
            "kind": "optional",
            "label": config.list_item_label,
            "enabled": True,
            "node": node,
        }

    return node


def _accepts(shape, value) -> bool:
    if type(shape) is Struct:
        return type(value) is shape.cls

    if type(shape) is List:
        if type(value) is not list:
            return False
        return all(_accepted_by_any(shape.item, item) for item in value)

    return type(value) is shape.pytype


def _accepted_by_any(shapes, value) -> bool:
    if value is None:
        return any(type(s) is NoneShape for s in shapes)

    return any(_accepts(s, value) for s in shapes)


def _branch_index(shapes, value, path: str) -> int:
    for index, shape in enumerate(shapes):
        if _accepts(shape, value):
            return index

    options = " | ".join(shape.option_id() for shape in shapes)

    raise _error(
        path, f"default {value!r} matches none of the options {options}")


def _plain_value(shape, value, path: str):
    # A file mints its reference from the user's choice, so it carries no default.
    # Reaching one here means a default reached a file shape — directly, or nested
    # in a list item, struct field or union branch — which is rejected.
    if _is_file_shape(shape):
        raise _error(
            path,
            "a file field cannot carry a default; its reference is generated "
            "locally")

    if type(shape) is Struct:
        return {f.name: _initial_value(f.shape, getattr(value, f.name),
                                       f"{path}.{f.name}")
                for f in shape.fields}

    if type(shape) is List:
        return [_initial_value(shape.item, item, f"{path}[{index}]")
                for index, item in enumerate(value)]

    if type(shape) is Int:
        safe = _safe_int(value, path, "Int default")
        _check_slider_default(shape, safe, path)
        return safe

    # A date/time default is a Python object; the plan is JSON, so it travels as
    # canonical ISO text, the same form its bounds and choices take.
    if type(shape) is Date or type(shape) is Time:
        return value.isoformat()

    # An enum default is a member certified by the core; it travels as its name,
    # the same transport its choices take.
    if type(shape) is EnumShape:
        return value.name

    return value


def _check_slider_default(shape, value: int, path: str) -> None:
    # The core validates a default against min, max and multiple_of, but not
    # against the slider's Step grid. A slider default that cannot land on a
    # step position is off the converted browser contract, so the adapter
    # rejects it before emitting the plan (the browser would reject it too).
    if shape.slider is None or shape.step is None:
        return

    minimum = _bound(shape.min, 1, path, "Int.min")

    if minimum is not None and (value - minimum) % shape.step.value != 0:
        raise _error(
            path,
            f"Int slider default {value} is not on the grid stepping by "
            f"{shape.step.value} from {minimum}")


def _initial_value(shapes, value, path: str):
    real = [s for s in shapes if type(s) is not NoneShape]

    if value is None:
        return None

    if len(real) == 1:
        return _plain_value(real[0], value, path)

    index = _branch_index(real, value, path)

    return {"branch": index,
            "value": _plain_value(real[index], value, path)}


def _enabled(field) -> bool:
    if field.optional_toggle is not None:
        return field.optional_toggle.enabled

    if field.default is MISSING:
        return True

    return field.default is not None


def _field_node(field, config, path: str) -> dict:
    optional = any(type(s) is NoneShape for s in field.shape)
    has_default = field.default is not MISSING
    where = f"{path}.{field.name}"

    # A lone file field carries no default — single or multiple (list[File]), not
    # even the None a switched-off optional would use, nor an empty list. Catch it
    # here because _plain_value never sees that None (it returns early) and never
    # descends into an empty list. A file as one branch of a wider union is left to
    # _plain_value, which rejects only a default that lands on the file branch.
    real = [s for s in field.shape if type(s) is not NoneShape]
    if (has_default and len(real) == 1
            and (_is_file_shape(real[0]) or _is_multiple_file_shape(real[0]))):
        raise _error(
            where,
            "a file field cannot carry a default; its reference is generated "
            "locally")

    label = field.label.value if field.label else field.name
    description = field.description.value if field.description else None
    enabled = _enabled(field) if optional else True

    node = {
        "name": field.name,
        "label": label,
        "description": description,
        "optional": optional,
        "enabled": enabled,
        "hasDefault": has_default,
        "node": _options_node(field.shape, config, where),
    }

    if has_default:
        node["default"] = _initial_value(field.shape, field.default, where)

    return node


def _form_node(name, description, fields, config) -> dict:
    plan = {"v": _PLAN_VERSION, "kind": "form", "name": name,
            "description": description}

    plan["fields"] = [_field_node(f, config, "fields") for f in fields]

    return plan


def plan_of(obj, *, config: WebConfig | None = None) -> dict:
    if config is None:
        config = WebConfig()
    elif type(config) is not WebConfig:
        raise TypeError(
            f"config must be WebConfig or None, got {type(config).__name__}")

    if type(obj) is Struct:
        return _form_node(obj.cls.__name__, None, obj.fields, config)

    if type(obj) is Signature:
        return _form_node(obj.name, obj.doc, obj.params, config)

    if is_dataclass(obj):
        if not isinstance(obj, type):
            raise TypeError(
                f"expected a dataclass type, got an instance of "
                f"{type(obj).__name__}")

        return plan_of(struct_of(obj), config=config)

    if isinstance(obj, FunctionType):
        if obj.__name__ == "<lambda>":
            raise TypeError(
                "plan_of() does not accept lambdas: lambdas have no usable "
                "name")

        return plan_of(signature_of(obj), config=config)

    raise TypeError(
        f"expected a plain function, a dataclass type, a Signature or a "
        f"Struct, got {obj!r}")
