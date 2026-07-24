import test from "node:test";
import assert from "node:assert/strict";

import {
    INT_DEFAULTS, LIST_DEFAULTS, OPTIONAL_DEFAULTS, STR_DEFAULTS,
} from "../../src/pytypehintweb/static/defaults.js";
import {
    normalizeNode, normalizePlan,
} from "../../src/pytypehintweb/static/normalize.js";
import { expandNode, expandPlan } from "./plan-fixture.mjs";

// The plan contract has a single, fully expanded representation. These tests
// author compact specs for readability and expand them the way a producer
// would; what is under test is normalization's copy/recursion/override
// behaviour, not any default filling (which no longer exists — see
// structure.test.mjs for the "omission is rejected" contract).


function planWith(node) {
    return expandPlan(
        { kind: "form", name: "example", fields: [{ name: "value", node }] });
}


test("normalizePlan leaves the received object untouched", () => {
    const plan = planWith({ kind: "str" });
    const before = JSON.stringify(plan);

    normalizePlan(plan);

    assert.equal(JSON.stringify(plan), before);
});


test("normalizePlan returns fresh objects", () => {
    const plan = planWith({ kind: "str" });
    const normalized = normalizePlan(plan);

    assert.notEqual(normalized, plan);
    assert.notEqual(normalized.fields, plan.fields);
    assert.notEqual(normalized.fields[0], plan.fields[0]);
    assert.notEqual(normalized.fields[0].node, plan.fields[0].node);
});


test("two normalized nodes never share their options object", () => {
    const plan = expandPlan({
        kind: "form",
        name: "example",
        fields: [
            { name: "a", node: { kind: "str" } },
            { name: "b", node: { kind: "str" } },
        ],
    });

    const normalized = normalizePlan(plan);

    assert.notEqual(normalized.fields[0].node.options,
                    normalized.fields[1].node.options);

    normalized.fields[0].node.options.minLength = 5;

    assert.equal(normalized.fields[1].node.options.minLength, null);
    assert.equal(STR_DEFAULTS.minLength, null);
});


test("a field keeps an explicit label", () => {
    const plan = planWith({ kind: "str" });
    plan.fields[0].label = "Valor";

    assert.equal(normalizePlan(plan).fields[0].label, "Valor");
});


test("an empty string override survives normalization", () => {
    const normalized = normalizeNode(
        expandNode({ kind: "str", options: { placeholder: "" } }));

    assert.equal(normalized.options.placeholder, "");
});


test("a zero override survives normalization", () => {
    const normalized = normalizeNode(expandNode({
        kind: "str",
        options: { minLength: 0, maxLength: 0 },
    }));

    assert.equal(normalized.options.minLength, 0);
    assert.equal(normalized.options.maxLength, 0);
});


test("an empty array default survives normalization", () => {
    const plan = planWith({ kind: "list", item: { kind: "str" } });
    plan.fields[0].hasDefault = true;
    plan.fields[0].default = [];

    const field = normalizePlan(plan).fields[0];

    assert.deepEqual(field.default, []);
    assert.notEqual(field.default, plan.fields[0].default);
});


test("a null default is kept and is not confused with absence", () => {
    const plan = planWith({ kind: "str" });
    plan.fields[0].optional = true;
    plan.fields[0].enabled = false;
    plan.fields[0].hasDefault = true;
    plan.fields[0].default = null;

    const field = normalizePlan(plan).fields[0];

    assert.equal(field.hasDefault, true);
    assert.equal("default" in field, true);
    assert.equal(field.default, null);
});


test("list items are normalized recursively", () => {
    const normalized = normalizeNode(expandNode({
        kind: "list",
        item: { kind: "int", options: { min: 1 } },
    }));

    assert.deepEqual(normalized.item.options, { ...INT_DEFAULTS, min: 1 });
});


test("object fields are normalized recursively", () => {
    const normalized = normalizeNode(expandNode({
        kind: "object",
        fields: [{ name: "city", node: { kind: "str" } }],
    }));

    assert.equal(normalized.fields[0].label, "city");
    assert.deepEqual(normalized.fields[0].node.options, { ...STR_DEFAULTS });
});


test("choice branches are normalized recursively", () => {
    const normalized = normalizeNode(expandNode({
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    }));

    assert.equal(normalized.branches[0].value, "str");
    assert.equal(normalized.branches[0].mode, "plain");
    assert.deepEqual(normalized.branches[0].node.options, { ...STR_DEFAULTS });
    assert.deepEqual(normalized.branches[1].node.options, { ...INT_DEFAULTS });
});


test("a branch carries only value, mode and node; a label is unknown", () => {
    assert.throws(() => normalizeNode(expandNode({
        kind: "choice",
        branches: [
            { label: "Texto", value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    })), /branches\[0\]\.label: unknown property/);
});


test("a branch value must be a non-empty transport identifier", () => {
    assert.throws(() => normalizeNode(expandNode({
        kind: "choice",
        branches: [
            { value: "", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    })), /branches\[0\]\.value: must be a non-empty string/);
});


test("an optional list item normalizes its label and enabled flag", () => {
    // Optional nodes are only valid as list items, so normalizeNode is asked to
    // allow one here.
    const normalized = normalizeNode(
        expandNode({ kind: "optional", node: { kind: "str" } }), "node", true);

    assert.equal(normalized.label, OPTIONAL_DEFAULTS.label);
    assert.equal(normalized.enabled, OPTIONAL_DEFAULTS.enabled);
    assert.deepEqual(normalized.node.options, { ...STR_DEFAULTS });
});


test("choices carry no placeholder of their own", () => {
    const normalized = normalizeNode(expandNode({
        kind: "str",
        options: { choices: ["a", "b"] },
    }));

    assert.equal(normalized.options.placeholder, null);
});


test("normalization leaves an explicit null placeholder as null", () => {
    const normalized = normalizeNode(expandNode({
        kind: "str",
        options: { choices: ["a", "b"], placeholder: null },
    }));

    assert.equal(normalized.options.placeholder, null);
});


test("choices arrays are copied instead of shared", () => {
    const node = expandNode({ kind: "str", options: { choices: ["a", "b"] } });
    const normalized = normalizeNode(node);

    assert.notEqual(normalized.options.choices, node.options.choices);
    assert.deepEqual(normalized.options.choices, ["a", "b"]);
});


// --- no mutable value is shared with the input ------------------------------
//
// enumChoices and fileExtensions validate in place and used to hand the very
// array they received straight back, so the normalized plan and its source
// aliased one array in both directions. Every other choices normalizer already
// built a fresh one.

test("enum choices are a fresh array, isolated in both directions", () => {
    const node = expandNode({ kind: "enum", options: { choices: ["A", "B"] } });
    const normalized = normalizeNode(node);

    assert.notEqual(normalized.options.choices, node.options.choices);
    assert.deepEqual(normalized.options.choices, ["A", "B"]);

    node.options.choices.push("C");
    assert.deepEqual(normalized.options.choices, ["A", "B"]);

    normalized.options.choices.push("Z");
    assert.deepEqual(node.options.choices, ["A", "B", "C"]);
});


test("file extensions are a fresh array, isolated in both directions", () => {
    const node = expandNode({ kind: "file", options: { extensions: [".pdf"] } });
    const normalized = normalizeNode(node);

    assert.notEqual(normalized.options.extensions, node.options.extensions);
    assert.deepEqual(normalized.options.extensions, [".pdf"]);

    node.options.extensions.push(".png");
    assert.deepEqual(normalized.options.extensions, [".pdf"]);

    normalized.options.extensions.push(".exe");
    assert.deepEqual(node.options.extensions, [".pdf", ".png"]);
});


test("the other choices normalizers stay isolated too", () => {
    const cases = [
        [{ kind: "str", options: { choices: ["x", "y"] } }, "choices"],
        [{ kind: "int", options: { choices: [1, 2] } }, "choices"],
        [{ kind: "float", options: { choices: [0.5, 1.5] } }, "choices"],
        [{ kind: "date", options: { choices: ["2026-01-01"] } }, "choices"],
        [{ kind: "time", options: { choices: ["09:00:00"] } }, "choices"],
    ];

    for (const [source, key] of cases) {
        const node = expandNode(source);
        const normalized = normalizeNode(node);

        assert.notEqual(normalized.options[key], node.options[key],
                        `${source.kind} ${key} should be a fresh array`);
        assert.deepEqual(normalized.options[key], node.options[key]);
    }
});
