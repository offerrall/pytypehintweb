import {
    BRANCH_KEYS, CHOICE_KEYS, FIELD_KEYS, FORM_KEYS, KINDS, LIST_KEYS, MODES,
    OBJECT_KEYS, OPTIONAL_KEYS, PLAN_VERSION, SCALAR_KEYS,
} from "./defaults.js";
import { isValidIsoDate } from "./iso.js";


export function fail(path, message) {
    throw new TypeError(`${path}: ${message}`);
}


export function putKey(target, key, value) {
    Object.defineProperty(target, key, {
        value, writable: true, enumerable: true, configurable: true,
    });

    return target;
}


export function ownValue(source, key) {
    return Object.prototype.hasOwnProperty.call(source, key)
        ? source[key]
        : undefined;
}


function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}


function asRecord(value, path) {
    if (!isRecord(value)) {
        fail(path, "expected an object");
    }

    return value;
}


function asArray(value, path) {
    if (!Array.isArray(value)) {
        fail(path, "expected an array");
    }

    return value;
}


function asString(value, path) {
    if (typeof value !== "string") {
        fail(path, "expected a string");
    }

    return value;
}


function asStringOrNull(value, path) {
    if (value !== null && typeof value !== "string") {
        fail(path, "expected a string or null");
    }

    return value;
}


function asBoolean(value, path) {
    if (typeof value !== "boolean") {
        fail(path, "expected a boolean");
    }

    return value;
}


function asIntegerOrNull(value, path) {
    if (value === null) {
        return value;
    }

    if (typeof value !== "number") {
        fail(path, "expected a number or null");
    }

    if (!Number.isSafeInteger(value)) {
        fail(path, "expected a safe integer");
    }

    return value;
}


function asPositiveOrNull(value, path) {
    asIntegerOrNull(value, path);

    if (value !== null && value <= 0) {
        fail(path, "must be a positive integer or null");
    }

    return value;
}


function asCountOrNull(value, path) {
    asIntegerOrNull(value, path);

    if (value !== null && value < 0) {
        fail(path, "must be a non-negative integer or null");
    }

    return value;
}


function asFiniteNumberOrNull(value, path) {
    if (value === null) {
        return value;
    }

    if (typeof value !== "number") {
        fail(path, "expected a number or null");
    }

    if (!Number.isFinite(value)) {
        fail(path, "expected a finite number");
    }

    return value;
}


function asPositiveFiniteOrNull(value, path) {
    asFiniteNumberOrNull(value, path);

    if (value !== null && value <= 0) {
        fail(path, "must be a positive number or null");
    }

    return value;
}


function stringChoices(value, path) {
    if (value === null) {
        return null;
    }

    asArray(value, path);

    return value.map((choice, i) => asString(choice, `${path}[${i}]`));
}


function floatChoices(value, path) {
    if (value === null) {
        return null;
    }

    asArray(value, path);

    return value.map((choice, i) => {
        if (typeof choice !== "number" || !Number.isFinite(choice)) {
            fail(`${path}[${i}]`, "expected a finite number");
        }

        return choice;
    });
}


export const ISO_TIME = /^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$/;


function asIsoDateOrNull(value, path) {
    if (value === null) {
        return value;
    }

    if (!isValidIsoDate(value)) {
        fail(path, "expected an ISO date (YYYY-MM-DD) or null");
    }

    return value;
}


function asIsoTimeOrNull(value, path) {
    if (value === null) {
        return value;
    }

    if (typeof value !== "string" || !ISO_TIME.test(value)) {
        fail(path, "expected an ISO time (HH:MM:SS) or null");
    }

    return value;
}


function dateChoices(value, path) {
    if (value === null) {
        return null;
    }

    asArray(value, path);

    return value.map((choice, i) => {
        if (!isValidIsoDate(choice)) {
            fail(`${path}[${i}]`, "expected an ISO date (YYYY-MM-DD)");
        }

        return choice;
    });
}


function timeChoices(value, path) {
    if (value === null) {
        return null;
    }

    asArray(value, path);

    return value.map((choice, i) => {
        if (typeof choice !== "string" || !ISO_TIME.test(choice)) {
            fail(`${path}[${i}]`, "expected an ISO time (HH:MM:SS)");
        }

        return choice;
    });
}


function enumChoices(value, path) {
    asArray(value, path);

    if (value.length === 0) {
        fail(path, "expected a non-empty array");
    }

    const seen = new Set();

    value.forEach((choice, i) => {
        asString(choice, `${path}[${i}]`);

        if (seen.has(choice)) {
            fail(`${path}[${i}]`, "duplicated choice");
        }

        seen.add(choice);
    });

    return value.slice();
}


function mustBeNull(value, path) {
    if (value !== null) {
        fail(path, "must be null");
    }

    return value;
}


function intChoices(value, path) {
    if (value === null) {
        return null;
    }

    asArray(value, path);

    return value.map((choice, i) => {
        if (!Number.isSafeInteger(choice)) {
            fail(`${path}[${i}]`, "expected a safe integer");
        }

        return choice;
    });
}


function fileExtensions(value, path) {
    asArray(value, path);

    const seen = new Set();

    value.forEach((extension, i) => {
        const at = `${path}[${i}]`;
        asString(extension, at);

        if (extension.length < 2 || extension[0] !== "."
                || extension !== extension.toLowerCase()) {
            fail(at, 'expected a lowercase extension starting with "." like ".pdf"');
        }

        if (seen.has(extension)) {
            fail(at, "duplicated extension");
        }

        seen.add(extension);
    });

    return value.slice();
}


const FILE_CHECKS = {
    extensions: fileExtensions,
    invalidMessage: asString,
    multiple: asBoolean,
    minFiles: asCountOrNull,
    maxFiles: asCountOrNull,
    minSize: asCountOrNull,
    maxSize: asCountOrNull,
    minMessage: asString,
    maxMessage: asString,
    minSizeMessage: asString,
    maxSizeMessage: asString,
    currentLabel: asString,
    currentRemoveLabel: asString,
    currentReplaceLabel: asString,
    currentRestoreLabel: asString,
};

const STR_CHECKS = {
    minLength: asCountOrNull,
    maxLength: asCountOrNull,
    pattern: asStringOrNull,
    patternMessage: asString,
    minMessage: asString,
    maxMessage: asString,
    placeholder: asStringOrNull,
    password: asBoolean,
    rows: asPositiveOrNull,
    choices: stringChoices,
};

const INT_CHECKS = {
    min: asIntegerOrNull,
    max: asIntegerOrNull,
    multipleOf: asPositiveOrNull,
    step: asPositiveOrNull,
    slider: asBoolean,
    showValue: asBoolean,
    placeholder: asStringOrNull,
    choices: intChoices,
    safeMessage: asString,
    invalidMessage: asString,
    minMessage: asString,
    maxMessage: asString,
    multipleOfMessage: asString,
    increaseLabel: asString,
    decreaseLabel: asString,
};

const FLOAT_CHECKS = {
    min: asFiniteNumberOrNull,
    max: asFiniteNumberOrNull,
    minExclusive: asBoolean,
    maxExclusive: asBoolean,
    step: asPositiveFiniteOrNull,
    choices: floatChoices,
    placeholder: asStringOrNull,
    invalidMessage: asString,
    finiteMessage: asString,
    minMessage: asString,
    maxMessage: asString,
    increaseLabel: asString,
    decreaseLabel: asString,
};

const DATE_CHECKS = {
    min: asIsoDateOrNull,
    max: asIsoDateOrNull,
    placeholder: asStringOrNull,
    choices: dateChoices,
    invalidMessage: asString,
    minMessage: asString,
    maxMessage: asString,
};

const TIME_CHECKS = {
    min: asIsoTimeOrNull,
    max: asIsoTimeOrNull,
    minExclusive: asBoolean,
    maxExclusive: asBoolean,
    placeholder: asStringOrNull,
    choices: timeChoices,
    invalidMessage: asString,
    minMessage: asString,
    maxMessage: asString,
};

const ENUM_CHECKS = {
    choices: enumChoices,
    placeholder: mustBeNull,
    labels: mustBeNull,
};

const LIST_CHECKS = {
    addLabel: asString,
    removeLabel: asString,
    minItems: asCountOrNull,
    maxItems: asCountOrNull,
    minMessage: asString,
    maxMessage: asString,
};

const CHOICE_CHECKS = {
    previousLabel: asString,
    nextLabel: asString,
    positionLabel: asString,
};

const BOOL_CHECKS = {};

const SCALARS = {
    str: STR_CHECKS,
    int: INT_CHECKS,
    float: FLOAT_CHECKS,
    date: DATE_CHECKS,
    time: TIME_CHECKS,
    bool: BOOL_CHECKS,
    enum: ENUM_CHECKS,
    file: FILE_CHECKS,
};


function rejectUnknown(value, keys, path) {
    for (const key of Object.keys(value)) {
        if (!keys.includes(key)) {
            fail(`${path}.${key}`, "unknown property");
        }
    }
}


function requireKeys(value, keys, path) {
    for (const key of keys) {
        if (value[key] === undefined) {
            fail(`${path}.${key}`, "is required");
        }
    }
}


function fill(source, checks, path) {
    const result = {};

    for (const key of Object.keys(checks)) {
        const given = source[key];

        if (given === undefined) {
            fail(`${path}.${key}`, "is required");
        }

        result[key] = checks[key](given, `${path}.${key}`);
    }

    return result;
}


function clonePlain(value, path) {
    if (value === null || typeof value === "boolean"
            || typeof value === "string") {
        return value;
    }

    if (typeof value === "number") {
        if (!Number.isFinite(value)) {
            fail(path, "expected a finite number");
        }

        return value;
    }

    if (Array.isArray(value)) {
        return value.map((item, i) => clonePlain(item, `${path}[${i}]`));
    }

    if (isRecord(value)) {
        const result = {};

        for (const [key, item] of Object.entries(value)) {
            putKey(result, key, clonePlain(item, `${path}.${key}`));
        }

        return result;
    }

    fail(path, "expected a JSON serializable value");
}


function normalizeScalar(node, path) {
    rejectUnknown(node, SCALAR_KEYS, path);
    requireKeys(node, ["options"], path);

    const checks = SCALARS[node.kind];
    const given = asRecord(node.options, `${path}.options`);

    rejectUnknown(given, Object.keys(checks), `${path}.options`);

    const options = fill(given, checks, `${path}.options`);

    return { kind: node.kind, options };
}


function normalizeList(node, path) {
    rejectUnknown(node, LIST_KEYS, path);
    requireKeys(node, ["item"], path);

    return {
        kind: "list",
        ...fill(node, LIST_CHECKS, path),
        item: normalizeNode(node.item, `${path}.item`, true),
    };
}


function normalizeObject(node, path) {
    rejectUnknown(node, OBJECT_KEYS, path);
    requireKeys(node, ["fields"], path);
    asArray(node.fields, `${path}.fields`);

    return {
        kind: "object",
        fields: node.fields.map(
            (field, i) => normalizeField(field, `${path}.fields[${i}]`)),
    };
}


function normalizeBranch(branch, path) {
    asRecord(branch, path);
    rejectUnknown(branch, BRANCH_KEYS, path);
    requireKeys(branch, ["value", "mode", "node"], path);

    const value = asString(branch.value, `${path}.value`);

    if (value === "") {
        fail(`${path}.value`, "must be a non-empty string");
    }

    if (!MODES.includes(branch.mode)) {
        fail(`${path}.mode`, `expected ${MODES.join(", ")}`);
    }

    return {
        value,
        mode: branch.mode,
        node: normalizeNode(branch.node, `${path}.node`),
    };
}


function normalizeChoice(node, path) {
    rejectUnknown(node, CHOICE_KEYS, path);
    requireKeys(node, ["branches"], path);
    asArray(node.branches, `${path}.branches`);

    return {
        kind: "choice",
        ...fill(node, CHOICE_CHECKS, path),
        branches: node.branches.map(
            (branch, i) => normalizeBranch(branch, `${path}.branches[${i}]`)),
    };
}


function normalizeOptional(node, path) {
    rejectUnknown(node, OPTIONAL_KEYS, path);
    requireKeys(node, ["label", "enabled", "node"], path);

    return {
        kind: "optional",
        label: asString(node.label, `${path}.label`),
        enabled: asBoolean(node.enabled, `${path}.enabled`),
        node: normalizeNode(node.node, `${path}.node`, false),
    };
}


export function normalizeNode(node, path = "node", allowOptional = false) {
    asRecord(node, path);
    asString(node.kind, `${path}.kind`);

    if (!KINDS.includes(node.kind)) {
        fail(`${path}.kind`, `unknown node kind ${JSON.stringify(node.kind)}`);
    }

    if (node.kind === "str" || node.kind === "int" || node.kind === "float"
            || node.kind === "date" || node.kind === "time"
            || node.kind === "bool" || node.kind === "enum"
            || node.kind === "file") {
        return normalizeScalar(node, path);
    }

    if (node.kind === "list") {
        return normalizeList(node, path);
    }

    if (node.kind === "object") {
        return normalizeObject(node, path);
    }

    if (node.kind === "choice") {
        return normalizeChoice(node, path);
    }

    if (!allowOptional) {
        fail(`${path}.kind`, "optional nodes are only valid as list items");
    }

    return normalizeOptional(node, path);
}


export function normalizeField(field, path = "field") {
    asRecord(field, path);
    rejectUnknown(field, FIELD_KEYS, path);
    requireKeys(
        field,
        ["name", "label", "description", "optional", "enabled", "hasDefault",
         "node"],
        path);

    const name = asString(field.name, `${path}.name`);

    if (name === "") {
        fail(`${path}.name`, "must be a non-empty string");
    }

    if (name === "$type" || name === "$value") {
        fail(`${path}.name`,
             `"${name}" is reserved by the transport and cannot be a field name`);
    }

    const result = {
        name,
        label: asString(field.label, `${path}.label`),
        description: asStringOrNull(field.description, `${path}.description`),
        optional: asBoolean(field.optional, `${path}.optional`),
        enabled: asBoolean(field.enabled, `${path}.enabled`),
        hasDefault: asBoolean(field.hasDefault, `${path}.hasDefault`),
        node: normalizeNode(field.node, `${path}.node`),
    };

    if (!result.optional && result.enabled === false) {
        fail(`${path}.enabled`,
             "must be true when the field is not optional");
    }

    if (result.hasDefault && field.default === undefined) {
        fail(`${path}.default`, "expected a value because hasDefault is true");
    }

    if (!result.hasDefault && field.default !== undefined) {
        fail(`${path}.default`, "must be omitted when hasDefault is false");
    }

    if (result.hasDefault) {
        result.default = clonePlain(field.default, `${path}.default`);
    }

    return result;
}


export function normalizePlan(plan) {
    asRecord(plan, "plan");
    rejectUnknown(plan, FORM_KEYS, "plan");
    requireKeys(plan, ["v", "kind", "name", "description", "fields"], "plan");

    if (typeof plan.v !== "number" || !Number.isInteger(plan.v)) {
        fail("plan.v", "must be an integer");
    }

    if (plan.v !== PLAN_VERSION) {
        fail("plan.v", `unsupported plan version: ${plan.v}`);
    }

    if (plan.kind !== "form") {
        fail("plan.kind", 'expected "form"');
    }

    asArray(plan.fields, "plan.fields");

    return {
        v: PLAN_VERSION,
        kind: "form",
        name: asString(plan.name, "plan.name"),
        description: asStringOrNull(plan.description, "plan.description"),
        fields: plan.fields.map(
            (field, i) => normalizeField(field, `plan.fields[${i}]`)),
    };
}
