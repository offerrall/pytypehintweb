import test from "node:test";
import assert from "node:assert/strict";

import { normalizePlan } from "../../src/pytypehintweb/static/normalize.js";
import { expandPlan } from "./plan-fixture.mjs";

// The plan is a single, fully expanded representation: every known property is
// mandatory. These tests drive the real normalizer directly (no harness) to
// pin both structural rejection and the "a missing key is an error" contract.


function planWith(node, extra = {}) {
    return expandPlan(
        { kind: "form", name: "example", fields: [{ name: "value", node, ...extra }] });
}


function rejects(plan, fragment) {
    assert.throws(() => normalizePlan(plan), (error) => {
        assert.ok(error instanceof TypeError, `expected a TypeError, got ${error}`);
        assert.ok(error.message.includes(fragment),
                  `expected ${JSON.stringify(error.message)} to mention `
                  + JSON.stringify(fragment));
        return true;
    });
}


// A fresh, fully valid plan whose single field exercises the requested node
// kind; every omission test deletes exactly one key from it.
function base(node = { kind: "str" }, extra = {}) {
    return planWith(node, extra);
}


// --- omission is always an error --------------------------------------------

const OMISSIONS = [
    ["form v", (p) => delete p.v, "plan.v: is required"],
    ["form name", (p) => delete p.name, "plan.name: is required"],
    ["form description", (p) => delete p.description,
     "plan.description: is required"],
    ["form fields", (p) => delete p.fields, "plan.fields: is required"],
    ["field name", (p) => delete p.fields[0].name,
     "plan.fields[0].name: is required"],
    ["field label", (p) => delete p.fields[0].label,
     "plan.fields[0].label: is required"],
    ["field description", (p) => delete p.fields[0].description,
     "plan.fields[0].description: is required"],
    ["field optional", (p) => delete p.fields[0].optional,
     "plan.fields[0].optional: is required"],
    ["field enabled", (p) => delete p.fields[0].enabled,
     "plan.fields[0].enabled: is required"],
    ["field hasDefault", (p) => delete p.fields[0].hasDefault,
     "plan.fields[0].hasDefault: is required"],
    ["field node", (p) => delete p.fields[0].node,
     "plan.fields[0].node: is required"],
    ["scalar options", (p) => delete p.fields[0].node.options,
     "plan.fields[0].node.options: is required"],
    ["str option", (p) => delete p.fields[0].node.options.minLength,
     "plan.fields[0].node.options.minLength: is required"],
];


for (const [label, mutate, fragment] of OMISSIONS) {
    test(`a missing ${label} is rejected`, () => {
        const plan = base();
        mutate(plan);
        rejects(plan, fragment);
    });
}


test("a missing int option is rejected", () => {
    const plan = base({ kind: "int" });
    delete plan.fields[0].node.options.multipleOfMessage;
    rejects(plan, "plan.fields[0].node.options.multipleOfMessage: is required");
});


test("a missing list key is rejected", () => {
    const plan = base({ kind: "list", item: { kind: "str" } });
    delete plan.fields[0].node.addLabel;
    rejects(plan, "plan.fields[0].node.addLabel: is required");
});


test("a missing list item is rejected", () => {
    const plan = base({ kind: "list", item: { kind: "str" } });
    delete plan.fields[0].node.item;
    rejects(plan, "plan.fields[0].node.item: is required");
});


test("a missing object fields is rejected", () => {
    const plan = base({
        kind: "object",
        fields: [{ name: "n", node: { kind: "str" } }],
    });
    delete plan.fields[0].node.fields;
    rejects(plan, "plan.fields[0].node.fields: is required");
});


test("a missing choice label is rejected", () => {
    const plan = base({
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    });
    delete plan.fields[0].node.previousLabel;
    rejects(plan, "plan.fields[0].node.previousLabel: is required");
});


for (const key of ["value", "mode", "node"]) {
    test(`a missing choice branch ${key} is rejected`, () => {
        const plan = base({
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
            ],
        });
        delete plan.fields[0].node.branches[0][key];
        rejects(plan, `plan.fields[0].node.branches[0].${key}: is required`);
    });
}


for (const key of ["label", "enabled"]) {
    test(`a missing optional ${key} is rejected`, () => {
        const plan = base({
            kind: "list",
            item: { kind: "optional", node: { kind: "str" } },
        });
        delete plan.fields[0].node.item[key];
        rejects(plan, `plan.fields[0].node.item.${key}: is required`);
    });
}


// --- unknown keys ------------------------------------------------------------

test("an unknown property on the form is rejected", () => {
    rejects({ kind: "form", name: "a", fields: [], version: 2 },
            "plan.version: unknown property");
});


test("an unknown property on a field is rejected", () => {
    rejects(planWith({ kind: "str" }, { required: true }),
            "plan.fields[0].required: unknown property");
});


test("an unknown property on a node is rejected", () => {
    rejects(planWith({ kind: "str", extra: 1 }),
            "plan.fields[0].node.extra: unknown property");
});


test("a misspelled option is rejected", () => {
    rejects(planWith({ kind: "str", options: { minLenght: 3 } }),
            "plan.fields[0].node.options.minLenght: unknown property");
});


test("an unknown kind is rejected", () => {
    rejects(planWith({ kind: "tuple" }), "unknown node kind");
});


// --- version -----------------------------------------------------------------

test("a form without a version is rejected", () => {
    rejects({ kind: "form", name: "a", description: null, fields: [] },
            "plan.v: is required");
});


test("a non-integer version is rejected", () => {
    rejects({ v: "2", kind: "form", name: "a", description: null, fields: [] },
            "plan.v: must be an integer");
});


test("a boolean version is rejected", () => {
    rejects({ v: true, kind: "form", name: "a", description: null, fields: [] },
            "plan.v: must be an integer");
});


test("a version below one is rejected", () => {
    rejects({ v: 0, kind: "form", name: "a", description: null, fields: [] },
            "unsupported plan version: 0");
});


test("an unsupported future version is rejected", () => {
    rejects({ v: 2, kind: "form", name: "a", description: null, fields: [] },
            "unsupported plan version: 2");
});


test("the current plan version is accepted", () => {
    const normalized = normalizePlan(
        { v: 1, kind: "form", name: "a", description: null, fields: [] });

    assert.equal(normalized.v, 1);
});


// --- branch mode -------------------------------------------------------------

test("an unknown branch mode is rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: "str", mode: "raw", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    }), "plan.fields[0].node.branches[0].mode: expected plain, inline, wrapped");
});


// --- hasDefault / default pair ----------------------------------------------

test("hasDefault true without default is rejected", () => {
    rejects(planWith({ kind: "str" }, { hasDefault: true }),
            "plan.fields[0].default: expected a value because hasDefault is true");
});


test("a default without hasDefault is rejected", () => {
    rejects(planWith({ kind: "str" }, { default: "text" }),
            "plan.fields[0].default: must be omitted when hasDefault is false");
});


test("a default with hasDefault false is rejected", () => {
    rejects(planWith({ kind: "str" }, { hasDefault: false, default: "text" }),
            "plan.fields[0].default: must be omitted when hasDefault is false");
});


// --- value types -------------------------------------------------------------

test("a wrongly typed optional property is rejected", () => {
    rejects(planWith({ kind: "str", options: { minLength: "3" } }),
            "plan.fields[0].node.options.minLength: expected a number or null");
});


test("a non-integer length is rejected", () => {
    rejects(planWith({ kind: "str", options: { maxLength: 2.5 } }),
            "expected a safe integer");
});


test("a non-boolean flag is rejected", () => {
    rejects(planWith({ kind: "str", options: { password: "yes" } }),
            "plan.fields[0].node.options.password: expected a boolean");
});


test("a wrongly typed label is rejected", () => {
    rejects(planWith({ kind: "str" }, { label: 7 }),
            "plan.fields[0].label: expected a string");
});


test("a negative rows value is rejected", () => {
    rejects(planWith({ kind: "str", options: { rows: 0 } }),
            "must be a positive integer or null");
});


test("a negative minItems is rejected", () => {
    rejects(planWith({ kind: "list", minItems: -1, item: { kind: "str" } }),
            "must be a non-negative integer or null");
});


test("a non serializable default is rejected", () => {
    rejects(planWith({ kind: "str" }, { hasDefault: true, default: () => "x" }),
            "expected a JSON serializable value");
});


test("a zero multipleOf is rejected with its path, without a slider", () => {
    rejects(planWith({ kind: "int", options: { multipleOf: 0 } }),
            "plan.fields[0].node.options.multipleOf: must be a positive integer "
            + "or null");
});


test("a negative multipleOf is rejected, without a slider", () => {
    rejects(planWith({ kind: "int", options: { multipleOf: -3 } }),
            "plan.fields[0].node.options.multipleOf: must be a positive integer "
            + "or null");
});


test("a zero multipleOf is rejected before the slider reachability check", () => {
    rejects(planWith({
        kind: "int",
        options: { min: 0, max: 10, slider: true, multipleOf: 0 },
    }), "multipleOf: must be a positive integer or null");
});


test("a negative multipleOf is rejected with a slider", () => {
    rejects(planWith({
        kind: "int",
        options: { min: 0, max: 10, slider: true, multipleOf: -5 },
    }), "multipleOf: must be a positive integer or null");
});


test("a negative minLength is rejected", () => {
    rejects(planWith({ kind: "str", options: { minLength: -1 } }),
            "plan.fields[0].node.options.minLength: must be a non-negative "
            + "integer or null");
});


test("a negative maxLength is rejected", () => {
    rejects(planWith({ kind: "str", options: { maxLength: -1 } }),
            "plan.fields[0].node.options.maxLength: must be a non-negative "
            + "integer or null");
});


// --- overrides that are values, not absences --------------------------------

test("a zero minLength and maxLength are accepted", () => {
    const normalized = normalizePlan(
        planWith({ kind: "str", options: { minLength: 0, maxLength: 0 } }));
    const options = normalized.fields[0].node.options;

    assert.equal(options.minLength, 0);
    assert.equal(options.maxLength, 0);
});


test("a positive multipleOf is accepted", () => {
    const normalized = normalizePlan(
        planWith({ kind: "int", options: { multipleOf: 5 } }));

    assert.equal(normalized.fields[0].node.options.multipleOf, 5);
});
