export const PLAN_VERSION = 1;

export const KINDS = Object.freeze([
    "str", "int", "float", "date", "time", "bool", "enum", "file", "list",
    "object", "choice", "optional",
]);

export const MODES = Object.freeze(["plain", "inline", "wrapped"]);

// The scalar/list/choice/optional default tables below are the widget
// contract for hand-built widgets (fields.js / inputs.js), not plan filling:
// a plan carries every property explicitly.
export const STR_DEFAULTS = Object.freeze({
    minLength: null,
    maxLength: null,
    pattern: null,
    patternMessage: "Invalid format",
    minMessage: "Must contain at least {value} characters",
    maxMessage: "Must contain at most {value} characters",
    placeholder: null,
    password: false,
    rows: null,
    choices: null,
});

// A checkbox has no configurable atoms, so its node's options object is empty.
export const BOOL_DEFAULTS = Object.freeze({});

export const INT_DEFAULTS = Object.freeze({
    min: null,
    max: null,
    multipleOf: null,
    step: null,
    slider: false,
    showValue: false,
    placeholder: null,
    choices: null,
    safeMessage: "Must be a safe integer",
    invalidMessage: "Enter a valid integer",
    minMessage: "Must be at least {value}",
    maxMessage: "Must be at most {value}",
    multipleOfMessage: "Must be a multiple of {value}",
    increaseLabel: "Increase",
    decreaseLabel: "Decrease",
});

// A float bound travels as a value beside a boolean flag, never converted: the
// widget compares the double directly, exactly as the core does. minExclusive
// and maxExclusive are always present, false when there is no bound.
export const FLOAT_DEFAULTS = Object.freeze({
    min: null,
    max: null,
    minExclusive: false,
    maxExclusive: false,
    step: null,
    choices: null,
    placeholder: null,
    invalidMessage: "Enter a valid number",
    finiteMessage: "Must be a finite number",
    minMessage: "Must be at least {value}",
    maxMessage: "Must be at most {value}",
    increaseLabel: "Increase",
    decreaseLabel: "Decrease",
});

// Date and time travel as ISO strings, compared lexicographically. A date bound
// is inclusive (plan_of converts an exclusive one by ±1 day, like an int); a
// time bound keeps its exclusive flag (the core compares directly, like a float).
export const DATE_DEFAULTS = Object.freeze({
    min: null,
    max: null,
    placeholder: null,
    choices: null,
    invalidMessage: "Enter a valid date",
    minMessage: "Must be on or after {value}",
    maxMessage: "Must be on or before {value}",
});

export const TIME_DEFAULTS = Object.freeze({
    min: null,
    max: null,
    minExclusive: false,
    maxExclusive: false,
    placeholder: null,
    choices: null,
    invalidMessage: "Enter a valid time",
    minMessage: "Must be at or after {value}",
    maxMessage: "Must be at or before {value}",
});

// An enum is a closed set of member names, rendered as a select over strings.
// choices is always non-empty and filled by the plan; placeholder and labels
// are always null (a closed select needs no prompt, and member labels wait for
// a future Extra vocabulary). There are no validation messages: a select over a
// fixed set cannot be in error.
export const ENUM_DEFAULTS = Object.freeze({
    choices: null,
    placeholder: null,
    labels: null,
});

// A file field is a str (or list[str]) on the wire: its value is a reference the
// widget generates locally from the chosen file. extensions is possibly empty
// (any file) and maps to the input's accept attribute; invalidMessage shows only
// when the browser lets through a file whose extension is not accepted, so no
// reference is minted. `multiple` (list[File]) makes value() an array and turns on
// minFiles / maxFiles count bounds with their messages. currentLabel /
// currentRemoveLabel / currentReplaceLabel drive the "current file" display
// setValue() puts the widget into. There is no placeholder and no default: a file
// input has neither.
export const FILE_DEFAULTS = Object.freeze({
    extensions: [],
    invalidMessage: "Not an accepted file type",
    multiple: false,
    minFiles: null,
    maxFiles: null,
    minMessage: "Add at least {value} files",
    maxMessage: "Keep at most {value} files",
    currentLabel: "Current file: {value}",
    currentRemoveLabel: "Remove current file",
    currentReplaceLabel: "Replace file",
    currentRestoreLabel: "Restore current file",
});

export const LIST_DEFAULTS = Object.freeze({
    addLabel: "Add",
    removeLabel: "Remove",
    minItems: null,
    maxItems: null,
    minMessage: "Add at least {value} items",
    maxMessage: "Keep at most {value} items",
});

export const OPTIONAL_DEFAULTS = Object.freeze({
    label: "Item",
    enabled: true,
});

export const CHOICE_DEFAULTS = Object.freeze({
    previousLabel: "Previous mode",
    nextLabel: "Next mode",
    positionLabel: "Mode {current} of {total}",
});

export const FORM_KEYS = Object.freeze(["v", "kind", "name", "description", "fields"]);

export const FIELD_KEYS = Object.freeze([
    "name", "label", "description", "optional", "enabled", "hasDefault",
    "default", "node",
]);

export const LIST_KEYS = Object.freeze([
    "kind", "addLabel", "removeLabel", "minItems", "maxItems", "minMessage",
    "maxMessage", "item",
]);

export const OBJECT_KEYS = Object.freeze(["kind", "fields"]);

export const CHOICE_KEYS = Object.freeze([
    "kind", "previousLabel", "nextLabel", "positionLabel", "branches",
]);

export const BRANCH_KEYS = Object.freeze(["value", "mode", "node"]);

export const OPTIONAL_KEYS = Object.freeze(["kind", "label", "enabled", "node"]);

export const SCALAR_KEYS = Object.freeze(["kind", "options"]);
