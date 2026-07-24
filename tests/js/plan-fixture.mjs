// Test convenience: the plan contract is a single, fully expanded
// representation, so hand-written test plans would otherwise have to spell out
// every property. This helper stands in for a producer (like Python's
// plan_of): it deep-fills the mandatory keys with their documented defaults so
// tests can keep authoring compact specs. It never overrides a value that is
// present, so a test can still exercise any explicit override.

import {
    BOOL_DEFAULTS, CHOICE_DEFAULTS, DATE_DEFAULTS, ENUM_DEFAULTS, FILE_DEFAULTS,
    FLOAT_DEFAULTS, INT_DEFAULTS, LIST_DEFAULTS, OPTIONAL_DEFAULTS, STR_DEFAULTS,
    TIME_DEFAULTS,
} from "../../src/pytypehintweb/static/defaults.js";

const SCALAR_DEFAULTS = {
    str: STR_DEFAULTS, int: INT_DEFAULTS, float: FLOAT_DEFAULTS,
    date: DATE_DEFAULTS, time: TIME_DEFAULTS, bool: BOOL_DEFAULTS,
    enum: ENUM_DEFAULTS, file: FILE_DEFAULTS,
};

const LIST_OPTION_KEYS = [
    "addLabel", "removeLabel", "minItems", "maxItems", "minMessage",
    "maxMessage",
];


function withDefaults(source, defaults, keys = Object.keys(defaults)) {
    const result = { ...source };

    for (const key of keys) {
        if (result[key] === undefined) {
            result[key] = defaults[key];
        }
    }

    return result;
}


export function expandNode(node) {
    if (node === null || typeof node !== "object" || Array.isArray(node)) {
        return node;
    }

    if (node.kind === "str" || node.kind === "int" || node.kind === "float"
            || node.kind === "date" || node.kind === "time"
            || node.kind === "bool" || node.kind === "enum"
            || node.kind === "file") {
        const options = node.options === undefined ? {} : node.options;
        return {
            kind: node.kind,
            ...node,
            options: withDefaults(options, SCALAR_DEFAULTS[node.kind]),
        };
    }

    if (node.kind === "list") {
        return {
            ...withDefaults(node, LIST_DEFAULTS, LIST_OPTION_KEYS),
            item: expandNode(node.item),
        };
    }

    if (node.kind === "object") {
        return {
            ...node,
            fields: Array.isArray(node.fields)
                ? node.fields.map(expandField)
                : node.fields,
        };
    }

    if (node.kind === "choice") {
        return {
            ...withDefaults(node, CHOICE_DEFAULTS),
            branches: Array.isArray(node.branches)
                ? node.branches.map(
                    (branch) => (branch !== null && typeof branch === "object"
                        ? { ...branch, node: expandNode(branch.node) }
                        : branch))
                : node.branches,
        };
    }

    if (node.kind === "optional") {
        return {
            ...withDefaults(node, OPTIONAL_DEFAULTS),
            node: expandNode(node.node),
        };
    }

    return node;
}


export function expandField(field) {
    if (field === null || typeof field !== "object" || Array.isArray(field)) {
        return field;
    }

    const withName = { label: field.name, ...field };

    return withDefaults(
        { ...withName, node: expandNode(field.node) },
        { description: null, optional: false, enabled: true, hasDefault: false },
    );
}


export function expandPlan(plan) {
    if (plan === null || typeof plan !== "object" || Array.isArray(plan)) {
        return plan;
    }

    return withDefaults(
        {
            kind: "form",
            ...plan,
            // A fully expanded fixture always targets the current contract
            // version; force it so compact test plans need not repeat it.
            v: 1,
            fields: Array.isArray(plan.fields)
                ? plan.fields.map(expandField)
                : plan.fields,
        },
        { description: null },
    );
}
