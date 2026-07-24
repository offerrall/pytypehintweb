import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { checkPlan, compileForm } from "./harness.mjs";
import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { BoolWidget } from "../../src/pytypehintweb/static/inputs.js";


function plan(fields) {
    return { v: 1, kind: "form", name: "example", fields };
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


// --- node normalization -----------------------------------------------------

test("a bool node normalizes to an empty options object", () => {
    const normalized = normalizeNode({ kind: "bool", options: {} });
    assert.deepEqual(normalized, { kind: "bool", options: {} });
});


test("a bool node requires its options object", () => {
    // The raw normalizer (not the test fixture, which fills it) rejects a bool
    // node with no options object.
    assert.throws(() => normalizeNode({ kind: "bool" }),
                  /node\.options: is required/);
});


test("a bool node rejects any unknown option", () => {
    rejects(plan([{ name: "a", node: { kind: "bool", options: { placeholder: null } } }]),
            "plan.fields[0].node.options.placeholder: unknown property");
});


// --- default validation -----------------------------------------------------

test("a non-boolean bool default is rejected", () => {
    rejects(plan([{ name: "a", hasDefault: true, default: 1,
                    node: { kind: "bool", options: {} } }]),
            "plan.fields[0].default: expected a boolean for bool node");
});


test("a true or false default is accepted", () => {
    assert.doesNotThrow(() => checkPlan(plan([
        { name: "a", hasDefault: true, default: true, node: { kind: "bool" } },
    ])));
    assert.doesNotThrow(() => checkPlan(plan([
        { name: "b", hasDefault: true, default: false, node: { kind: "bool" } },
    ])));
});


// --- BoolWidget contract ----------------------------------------------------

test("a checkbox always represents a value and is never empty or in error", () => {
    const widget = new BoolWidget();

    assert.equal(widget.value(), false);          // unchecked is false
    assert.equal(widget.isEmpty(), false);
    assert.equal(widget.isReady(), true);
    assert.equal(widget.hasError(), false);
    assert.equal(widget.control(), widget.input);
    assert.equal(widget.input.type, "checkbox");
});


test("setValue accepts only true or false", () => {
    const widget = new BoolWidget();

    widget.setValue(true);
    assert.equal(widget.value(), true);
    widget.setValue(false);
    assert.equal(widget.value(), false);

    assert.throws(() => widget.setValue(null), /expects true or false/);
    assert.throws(() => widget.setValue("true"), /expects true or false/);
    assert.throws(() => widget.setValue(1), /expects true or false/);
});


test("toggling the checkbox emits a change and updates value()", () => {
    const widget = new BoolWidget();
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    widget.input.checked = true;
    widget.input.dispatch("change");

    assert.equal(changes, 1);
    assert.equal(widget.value(), true);
});


test("an initial value of true starts the checkbox checked", () => {
    assert.equal(new BoolWidget({ value: true }).value(), true);
    assert.equal(new BoolWidget({ value: false }).value(), false);
});


// --- through a compiled form ------------------------------------------------

function boolForm(extra = {}) {
    return compileForm(plan([{ name: "agree", node: { kind: "bool" }, ...extra }]));
}


test("a bool field with no default starts unchecked and reads false", () => {
    const form = boolForm();

    assert.equal(form.fields[0].widget.widget.value(), false);
    assert.deepEqual(form.read(), { agree: false });
    assert.equal(form.isReady(), true);
});


test("a default of true mounts the checkbox checked", () => {
    const form = boolForm({ hasDefault: true, default: true });
    const widget = form.fields[0].widget.widget;

    assert.equal(widget.input.checked, true);
    assert.deepEqual(form.read(), { agree: true });
});


test("an optional bool switched off reads null", () => {
    const form = compileForm(plan([{
        name: "agree", optional: true, enabled: false, hasDefault: true,
        default: null, node: { kind: "bool" },
    }]));

    assert.equal(form.fields[0].widget.enabled(), false);
    assert.deepEqual(form.read(), { agree: null });
});


test("a bool branch of a union travels flat as true or false", () => {
    const form = compileForm(plan([{
        name: "value",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "bool", mode: "plain", node: { kind: "bool" } },
            ],
        },
    }]));

    const choice = form.fields[0].widget.widget;
    choice.next.dispatch("click");            // move to the bool branch
    const bool = choice.active();
    bool.input.checked = true;
    bool.input.dispatch("change");

    assert.deepEqual(form.read(), { value: true });
});
