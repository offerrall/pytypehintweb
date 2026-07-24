import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { compileForm } from "./harness.mjs";
import { checkPlan } from "../../src/pytypehintweb/static/contract.js";
import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { expandNode } from "./plan-fixture.mjs";


// --- node normalization -----------------------------------------------------

test("the enum node fills every documented option", () => {
    assert.deepEqual(
        normalizeNode(expandNode({
            kind: "enum",
            options: { choices: ["ACTIVO", "INACTIVO"] },
        })),
        {
            kind: "enum",
            options: {
                choices: ["ACTIVO", "INACTIVO"],
                placeholder: null,
                labels: null,
            },
        });
});


test("enum choices must be a non-empty array of unique strings", () => {
    assert.throws(
        () => normalizeNode(expandNode({ kind: "enum", options: { choices: [] } })),
        /options\.choices: expected a non-empty array/);

    assert.throws(
        () => normalizeNode(expandNode({
            kind: "enum", options: { choices: ["A", "A"] } })),
        /options\.choices\[1\]: duplicated choice/);

    assert.throws(
        () => normalizeNode(expandNode({
            kind: "enum", options: { choices: ["A", 2] } })),
        /options\.choices\[1\]: expected a string/);
});


test("placeholder and labels must be null on an enum node", () => {
    assert.throws(
        () => normalizeNode(expandNode({
            kind: "enum", options: { choices: ["A"], placeholder: "x" } })),
        /options\.placeholder: must be null/);

    assert.throws(
        () => normalizeNode(expandNode({
            kind: "enum", options: { choices: ["A"], labels: ["x"] } })),
        /options\.labels: must be null/);
});


test("a missing choices key is rejected as required", () => {
    assert.throws(
        () => normalizeNode({
            kind: "enum", options: { placeholder: null, labels: null } }),
        /options\.choices: is required/);
});


// --- as a compiled form -----------------------------------------------------

function enumPlan(node, field = {}) {
    return {
        v: 1, kind: "form", name: "f", description: null,
        fields: [{
            name: "value", label: "v", description: null,
            optional: false, enabled: true, hasDefault: false,
            node, ...field,
        }],
    };
}


test("an enum mounts a select over its member names", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "status",
            node: { kind: "enum", options: { choices: ["ACTIVO", "INACTIVO"] } },
        }],
    });

    const widget = form.fields[0].widget.widget;

    // Opens on the first member, reads its name, and never empty or in error.
    assert.equal(widget.value(), "ACTIVO");
    assert.equal(form.isReady(), true);
    assert.equal(form.hasError(), false);

    widget.setValue("INACTIVO");
    assert.equal(form.read().status, "INACTIVO");
});


test("an enum default mounts on its option", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "status",
            hasDefault: true,
            default: "EN_PROCESO",
            node: {
                kind: "enum",
                options: { choices: ["ACTIVO", "INACTIVO", "EN_PROCESO"] },
            },
        }],
    });

    assert.equal(form.fields[0].widget.widget.value(), "EN_PROCESO");
    assert.equal(form.read().status, "EN_PROCESO");
    assert.equal(form.isReady(), true);
});


test("an optional enum switched off reads as null", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "status",
            optional: true,
            enabled: false,
            node: { kind: "enum", options: { choices: ["ACTIVO", "INACTIVO"] } },
        }],
    });

    assert.equal(form.read().status, null);
    assert.equal(form.isReady(), true);
});


// --- semantic checks (checkPlan) --------------------------------------------

test("checkPlan accepts an enum default that is one of the choices", () => {
    assert.doesNotThrow(() => checkPlan(enumPlan(
        expandNode({ kind: "enum", options: { choices: ["ACTIVO", "INACTIVO"] } }),
        { hasDefault: true, default: "INACTIVO" })));
});


test("checkPlan rejects an enum default outside the choices", () => {
    assert.throws(
        () => checkPlan(enumPlan(
            expandNode({ kind: "enum", options: { choices: ["ACTIVO"] } }),
            { hasDefault: true, default: "NOPE" })),
        /default: expected one of the declared choices/);
});


test("checkPlan rejects a non-string enum default", () => {
    assert.throws(
        () => checkPlan(enumPlan(
            expandNode({ kind: "enum", options: { choices: ["ACTIVO"] } }),
            { hasDefault: true, default: 1 })),
        /default: expected a string for enum node/);
});
