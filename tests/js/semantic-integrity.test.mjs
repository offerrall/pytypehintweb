import test from "node:test";
import assert from "node:assert/strict";

import { checkPlan } from "./harness.mjs";


function plan(fields) {
    return { v: 1, kind: "form", name: "example", fields };
}


function planWith(node, extra = {}) {
    return plan([{ name: "value", node, ...extra }]);
}


function rejects(input, fragment) {
    assert.throws(() => checkPlan(input), (error) => {
        assert.ok(error instanceof TypeError, `expected a TypeError, got ${error}`);
        assert.ok(error.message.includes(fragment),
                  `expected ${JSON.stringify(error.message)} to mention `
                  + JSON.stringify(fragment));
        return true;
    });
}


function twoBranch(first, second, extra = {}) {
    return planWith({ kind: "choice", branches: [first, second], ...extra });
}


// --- field identity ---------------------------------------------------------

test("an empty root field name is rejected", () => {
    rejects(plan([{ name: "", node: { kind: "str" } }]),
            "plan.fields[0].name: must be a non-empty string");
});


test("duplicate root field names are rejected", () => {
    rejects(plan([
        { name: "a", node: { kind: "str" } },
        { name: "a", node: { kind: "int" } },
    ]), "plan.fields[1].name: duplicated field name");
});


test("duplicate nested-object field names are rejected", () => {
    rejects(planWith({
        kind: "object",
        fields: [
            { name: "a", node: { kind: "str" } },
            { name: "a", node: { kind: "int" } },
        ],
    }), "plan.fields[0].node.fields[1].name: duplicated field name");
});


test("the same name in unrelated scopes is accepted", () => {
    assert.doesNotThrow(() => checkPlan(plan([
        { name: "x", node: { kind: "str" } },
        {
            name: "left",
            node: {
                kind: "object",
                fields: [{ name: "x", node: { kind: "str" } }],
            },
        },
        {
            name: "right",
            node: {
                kind: "object",
                fields: [{ name: "x", node: { kind: "int" } }],
            },
        },
    ])));
});


// --- union transport --------------------------------------------------------

const OBJECT_BRANCH = {
    value: "shirt",
    mode: "inline",
    node: { kind: "object", fields: [{ name: "size", node: { kind: "str" } }] },
};

const PLAIN_INT = { value: "int", mode: "plain", node: { kind: "int" } };


test("an inline string branch is rejected", () => {
    rejects(twoBranch(
        { value: "str", mode: "inline", node: { kind: "str" } }, PLAIN_INT),
            "inline requires an object node");
});


test("an inline integer branch is rejected", () => {
    rejects(twoBranch(
        { value: "n", mode: "inline", node: { kind: "int" } },
        { value: "s", mode: "plain", node: { kind: "str" } }),
            "inline requires an object node");
});


test("an inline list branch is rejected", () => {
    rejects(twoBranch(
        { value: "l", mode: "inline", node: { kind: "list", item: { kind: "str" } } },
        PLAIN_INT),
            "plan.fields[0].node.branches[0].mode: "
            + "inline requires an object node");
});


test("an inline object branch is accepted", () => {
    assert.doesNotThrow(() => checkPlan(twoBranch(OBJECT_BRANCH, PLAIN_INT)));
});


test("a plain object branch is still accepted", () => {
    assert.doesNotThrow(() => checkPlan(twoBranch(
        { ...OBJECT_BRANCH, mode: "plain" }, PLAIN_INT)));
});


// --- optional placement -----------------------------------------------------

test("an optional list item is accepted", () => {
    assert.doesNotThrow(() => checkPlan(planWith({
        kind: "list",
        item: { kind: "optional", node: { kind: "str" } },
    })));
});


test("an optional root field node is rejected", () => {
    rejects(planWith({ kind: "optional", node: { kind: "str" } }),
            "plan.fields[0].node.kind: "
            + "optional nodes are only valid as list items");
});


test("an optional object field node is rejected", () => {
    rejects(planWith({
        kind: "object",
        fields: [{ name: "n", node: { kind: "optional", node: { kind: "str" } } }],
    }), "plan.fields[0].node.fields[0].node.kind: "
        + "optional nodes are only valid as list items");
});


test("an optional choice branch is rejected", () => {
    rejects(twoBranch(
        { value: "opt", mode: "plain",
          node: { kind: "optional", node: { kind: "str" } } },
        PLAIN_INT),
            "plan.fields[0].node.branches[0].node.kind: "
            + "optional nodes are only valid as list items");
});


test("an optional wrapping another optional is rejected", () => {
    rejects(planWith({
        kind: "list",
        item: {
            kind: "optional",
            node: { kind: "optional", node: { kind: "str" } },
        },
    }), "optional nodes are only valid as list items");
});


// --- ordinary multipleOf reachability is NOT a checkPlan concern -------------
// The core rejects an unsatisfiable ordinary range when it compiles the schema,
// and such a range corrupts nothing at runtime (the widget just stays invalid),
// so checkPlan does not re-verify it — a manual plan carrying one is accepted.

test("an ordinary unsatisfiable multipleOf range is accepted by checkPlan", () => {
    assert.doesNotThrow(() => checkPlan(planWith(
        { kind: "int", options: { min: 1, max: 4, multipleOf: 7 } })));
    assert.doesNotThrow(() => checkPlan(planWith(
        { kind: "int", options: { min: -4, max: -1, multipleOf: 7 } })));
});


test("the slider grid, unlike the ordinary range, is still checked", () => {
    // A slider seeds an initial value, so its reachability must hold; this is a
    // corruption-preventing check, not the redundant ordinary-range one.
    rejects(planWith({
        kind: "int",
        options: { slider: true, min: 1, max: 9, step: 4, multipleOf: 10 },
    }), "is a multiple of 10");
});


// --- field optional/enabled coherence ---------------------------------------

test("a non-optional field with enabled false is rejected", () => {
    rejects(plan([{ name: "value", enabled: false, node: { kind: "str" } }]),
            "plan.fields[0].enabled: must be true when the field is not optional");
});


test("a non-optional field with enabled false is rejected inside an object", () => {
    rejects(planWith({
        kind: "object",
        fields: [{ name: "inner", enabled: false, node: { kind: "str" } }],
    }), "must be true when the field is not optional");
});


test("an optional field with enabled false is accepted", () => {
    assert.doesNotThrow(() => checkPlan(plan([
        { name: "value", optional: true, enabled: false, node: { kind: "str" } },
    ])));
});


test("a non-optional field with enabled true is accepted", () => {
    assert.doesNotThrow(() => checkPlan(plan([
        { name: "value", enabled: true, node: { kind: "str" } },
    ])));
});


test("a null default on a non-optional slider field is rejected", () => {
    // A range input has no empty state, so a non-optional slider field cannot
    // carry a null default. checkPlan covers it through the general rule that a
    // non-optional int field's default must be a safe integer (not null).
    rejects(planWith(
        { kind: "int", options: { slider: true, min: 0, max: 10 } },
        { hasDefault: true, default: null }),
        "plan.fields[0].default: expected a safe integer for int node");
});


// --- configurable stepper labels --------------------------------------------

test("an empty stepper increase label is rejected", () => {
    rejects(planWith({ kind: "int", options: { increaseLabel: "" } }),
            "plan.fields[0].node.options.increaseLabel: must not be empty");
});


test("a stepper label with a placeholder is rejected", () => {
    rejects(planWith({ kind: "int", options: { decreaseLabel: "Down {value}" } }),
            "must not contain placeholders");
});


test("custom stepper labels are accepted and normalized", () => {
    const normalized = checkPlan(planWith({
        kind: "int",
        options: { increaseLabel: "Subir", decreaseLabel: "Bajar" },
    }));

    assert.equal(normalized.fields[0].node.options.increaseLabel, "Subir");
    assert.equal(normalized.fields[0].node.options.decreaseLabel, "Bajar");
});


// --- other configurable labels ----------------------------------------------

test("an empty list add label is rejected", () => {
    rejects(planWith({ kind: "list", addLabel: "", item: { kind: "str" } }),
            "plan.fields[0].node.addLabel: must not be empty");
});


test("an empty optional item label is rejected", () => {
    rejects(planWith({
        kind: "list",
        item: { kind: "optional", label: "", node: { kind: "str" } },
    }), "must not be empty");
});


test("an empty mode navigation label is rejected", () => {
    rejects(twoBranch(
        { value: "str", mode: "plain", node: { kind: "str" } },
        PLAIN_INT,
        { previousLabel: "" }),
            "plan.fields[0].node.previousLabel: must not be empty");
});
