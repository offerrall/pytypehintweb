import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { walk } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { checkPlan } from "../../src/pytypehintweb/static/contract.js";
import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { expandNode } from "./plan-fixture.mjs";
import {
    FloatChoiceWidget, FloatWidget,
} from "../../src/pytypehintweb/static/inputs.js";


function typeInto(widget, raw) {
    widget.input.value = raw;
    widget.input.dispatch("input");
}


function stepButtons(widget) {
    return walk(widget.el).filter((node) => node.className === "pth-number-btn");
}


// --- the parsing grammar ----------------------------------------------------

test("well-formed float text parses to the exact number", () => {
    const widget = new FloatWidget();

    for (const [raw, value] of [["3", 3], ["3.5", 3.5], ["-3.5", -3.5],
                                ["0", 0], ["-0.25", -0.25], ["12.0", 12]]) {
        typeInto(widget, raw);
        assert.equal(widget.value(), value, `${raw} should parse to ${value}`);
        assert.equal(widget.input.value, raw, `${raw} was rewritten`);
    }
});


test("text outside the grammar reads as null and is invalid", () => {
    const widget = new FloatWidget();

    // No scientific notation, no bare ".5" or "5.", no decimal comma.
    for (const raw of ["1e3", ".5", "5.", "1,5", "abc", "3.1.4", "--3", "+3",
                       "3 4", "Infinity", "NaN"]) {
        typeInto(widget, raw);
        assert.equal(widget.input.value, raw, `${raw} was rewritten`);
        assert.equal(widget.value(), null, `${raw} should read as null`);
        assert.equal(widget.hasError(), true, `${raw} should be invalid`);
        assert.equal(widget.error(), "Enter a valid number");
    }
});


test("surrounding whitespace is trimmed for parsing but kept in the text", () => {
    const widget = new FloatWidget();

    typeInto(widget, "  3.5  ");
    assert.equal(widget.value(), 3.5);
    assert.equal(widget.input.value, "  3.5  ");
});


test("empty float text is incomplete but not invalid", () => {
    const widget = new FloatWidget();

    typeInto(widget, "");
    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
    assert.equal(widget.hasError(), false);
    assert.equal(widget.error(), null);
});


test("a magnitude that overflows to Infinity reads as null, never transported", () => {
    const widget = new FloatWidget();

    const huge = `${"9".repeat(400)}.0`;
    typeInto(widget, huge);

    assert.equal(widget.input.value, huge);
    assert.equal(widget.value(), null);
    assert.equal(widget.number(), null);
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be a finite number");
});


test("empty, invalid and non-finite states are distinct", () => {
    const widget = new FloatWidget();

    typeInto(widget, "");
    assert.equal(widget.error(), null);

    typeInto(widget, "abc");
    assert.equal(widget.error(), "Enter a valid number");

    typeInto(widget, `${"9".repeat(400)}.0`);
    assert.equal(widget.error(), "Must be a finite number");
});


// --- bounds compared directly, with exclusivity -----------------------------

test("an inclusive bound accepts its own boundary value", () => {
    const widget = new FloatWidget({ min: 0, max: 1 });

    typeInto(widget, "0");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "1");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "-0.001");
    assert.equal(widget.error(), "Must be at least 0");

    typeInto(widget, "1.001");
    assert.equal(widget.error(), "Must be at most 1");
});


test("an exclusive minimum rejects the boundary but accepts just past it", () => {
    const widget = new FloatWidget({ min: 0, minExclusive: true });

    typeInto(widget, "0");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be at least 0");

    typeInto(widget, "0.001");
    assert.equal(widget.hasError(), false);
});


test("an exclusive maximum rejects the boundary but accepts just below it", () => {
    const widget = new FloatWidget({ max: 10, maxExclusive: true });

    typeInto(widget, "10");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be at most 10");

    typeInto(widget, "9.999");
    assert.equal(widget.hasError(), false);
});


// --- the stepper is presentation, not a grid --------------------------------

test("the stepper adds and subtracts the step, clamped to the raw bound", () => {
    const widget = new FloatWidget({ min: 0, max: 1, step: 0.25 });
    const [up, down] = stepButtons(widget);

    up.dispatch("click");
    assert.equal(widget.value(), 0.25);

    up.dispatch("click");
    up.dispatch("click");
    up.dispatch("click");
    up.dispatch("click");
    assert.equal(widget.value(), 1);

    down.dispatch("click");
    assert.equal(widget.value(), 0.75);
});


test("the stepper falls back to a stride of one when no step is given", () => {
    const widget = new FloatWidget();

    assert.equal(widget.stepAmount, 1);

    stepButtons(widget)[0].dispatch("click");
    assert.equal(widget.value(), 1);
});


test("the stepper buttons carry the default accessibility labels", () => {
    const labels = stepButtons(new FloatWidget())
        .map((button) => button.getAttribute("aria-label"));

    assert.deepEqual(labels, ["Increase", "Decrease"]);
});


// --- setValue ---------------------------------------------------------------

test("setValue applies a finite number and keeps the number type", () => {
    const widget = new FloatWidget();
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    widget.setValue(3.5);
    assert.equal(widget.value(), 3.5);
    assert.equal(typeof widget.value(), "number");
    assert.equal(changes, 1);
});


test("setValue(null) empties the control", () => {
    const widget = new FloatWidget();

    widget.setValue(2.5);
    widget.setValue(null);

    assert.equal(widget.input.value, "");
    assert.equal(widget.isEmpty(), true);
    assert.equal(widget.value(), null);
});


test("setValue rejects a string, NaN, Infinity and booleans", () => {
    const widget = new FloatWidget();

    for (const bad of ["3", NaN, Infinity, -Infinity, true, {}]) {
        assert.throws(() => widget.setValue(bad),
                      /expects a finite number or null/);
    }
});


test("a positive step is required to be a positive finite number", () => {
    assert.throws(() => new FloatWidget({ step: 0 }), /positive finite number/);
    assert.throws(() => new FloatWidget({ step: -1 }), /positive finite number/);
    assert.throws(() => new FloatWidget({ step: NaN }), /positive finite number/);
});


// --- the widget in a compiled form ------------------------------------------

test("a float default mounts prefilled and ready", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "ratio",
            hasDefault: true,
            default: 0.5,
            node: { kind: "float", options: { min: 0, max: 1 } },
        }],
    });

    const widget = form.fields[0].widget.widget;

    assert.equal(widget.value(), 0.5);
    assert.equal(form.isReady(), true);
    assert.equal(form.read().ratio, 0.5);
});


test("an optional float switched off reads as null", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "value",
            optional: true,
            enabled: false,
            node: { kind: "float" },
        }],
    });

    assert.equal(form.read().value, null);
    assert.equal(form.isReady(), true);
});


test("read() reports a plain number, 3 included", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{ name: "value", node: { kind: "float" } }],
    });

    const widget = form.fields[0].widget.widget;
    typeInto(widget, "3");

    assert.equal(form.read().value, 3);
    assert.equal(typeof form.read().value, "number");
});


// --- the choice variant -----------------------------------------------------

test("float choices select the exact double from the plan", () => {
    const widget = new FloatChoiceWidget([0.25, 0.5, 0.75], 0.5);

    assert.equal(widget.value(), 0.5);

    widget.setValue(0.75);
    assert.equal(widget.value(), 0.75);
});


test("a float choice widget rejects a non-finite choice", () => {
    assert.throws(() => new FloatChoiceWidget([1, Infinity]),
                  /invalid choice/);
    assert.throws(() => new FloatChoiceWidget([1, "x"]),
                  /invalid choice/);
});


// --- node normalization -----------------------------------------------------

test("the float node fills every documented option", () => {
    const normalized = normalizeNode(expandNode({ kind: "float" }));

    assert.deepEqual(normalized, {
        kind: "float",
        options: {
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
        },
    });
});


test("a missing float option is rejected, never defaulted", () => {
    assert.throws(
        () => normalizeNode({ kind: "float", options: { min: 0 } }),
        /options\.max: is required/);
});


test("an unknown float option is rejected", () => {
    assert.throws(
        () => normalizeNode(expandNode({
            kind: "float", options: { slider: true } })),
        /options\.slider: unknown property/);
});


test("a wrongly typed float option is rejected", () => {
    assert.throws(
        () => normalizeNode(expandNode({
            kind: "float", options: { min: "0" } })),
        /options\.min: expected a number or null/);

    assert.throws(
        () => normalizeNode(expandNode({
            kind: "float", options: { minExclusive: "yes" } })),
        /options\.minExclusive: expected a boolean/);

    assert.throws(
        () => normalizeNode(expandNode({
            kind: "float", options: { step: 0 } })),
        /options\.step: must be a positive number or null/);
});


test("a non-finite float bound is rejected", () => {
    assert.throws(
        () => normalizeNode(expandNode({
            kind: "float", options: { min: Infinity } })),
        /options\.min: expected a finite number/);
});


// --- semantic checks (checkPlan, via a full plan) ---------------------------

function planWith(node) {
    return { v: 1, kind: "form", name: "f", description: null,
             fields: [{ name: "value", label: "v", description: null,
                        optional: false, enabled: true, hasDefault: false,
                        node }] };
}


test("checkPlan rejects an empty float range", () => {
    const node = expandNode({ kind: "float", options: { min: 1, max: 0 } });

    assert.throws(() => checkPlan(planWith(node)),
                  /min and max leave no representable value/);
});


test("checkPlan rejects equal bounds when a side is exclusive", () => {
    const node = expandNode({
        kind: "float", options: { min: 1, max: 1, minExclusive: true } });

    assert.throws(() => checkPlan(planWith(node)),
                  /min and max leave no representable value/);
});


test("checkPlan accepts equal inclusive bounds", () => {
    const node = expandNode({ kind: "float", options: { min: 1, max: 1 } });

    assert.doesNotThrow(() => checkPlan(planWith(node)));
});


test("checkPlan rejects a choice outside an exclusive bound", () => {
    const node = expandNode({
        kind: "float",
        options: { min: 0, minExclusive: true, choices: [0, 0.5] } });

    assert.throws(() => checkPlan(planWith(node)),
                  /choices\[0\]: is below min 0/);
});


// --- only numbers JavaScript writes as a simple decimal ---------------------
//
// The widget's grammar is `-?\d+(\.\d+)?`. A finite double outside it — 1e-7,
// 1e21 — would be written as exponent text the widget itself then reports as
// invalid, silently destroying whatever the control held. It is refused before
// anything is written, never expanded, rounded or truncated to fit.

const EXPONENT_NUMBERS = [1e-7, 1e21, 1e-21, 5e-324, -1e-7, 1e+21];


test("setValue refuses a number that only prints as an exponent", () => {
    for (const bad of EXPONENT_NUMBERS) {
        const widget = new FloatWidget();

        widget.setValue(1.5);
        assert.throws(() => widget.setValue(bad), /simple decimal/);

        // The previous state survives exactly: text, value and readiness.
        assert.equal(widget.input.value, "1.5");
        assert.equal(widget.value(), 1.5);
        assert.equal(widget.hasError(), false);
    }
});


test("setValue still accepts every plain decimal", () => {
    const widget = new FloatWidget();

    for (const good of [0, 1, -1, 0.1, -0.1, 0.0001, -123.456, 1e6]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
        assert.equal(widget.hasError(), false);
    }
});


test("setValue still refuses a non-finite number and a non-number", () => {
    const widget = new FloatWidget();

    for (const bad of [NaN, Infinity, -Infinity]) {
        assert.throws(() => widget.setValue(bad), /finite number/);
    }

    for (const bad of [".1", "1.", "+1", "1e-7", true]) {
        assert.throws(() => widget.setValue(bad), /finite number/);
    }
});


test("the constructor refuses an exponent-only number", () => {
    assert.throws(() => new FloatWidget({ value: 1e-7 }), /simple decimal/);

    // A plain decimal still mounts, and an empty control is still the default.
    assert.equal(new FloatWidget({ value: 0.5 }).input.value, "0.5");
    assert.equal(new FloatWidget().input.value, "");
});


test("a plan default that only prints as an exponent fails at compile time", () => {
    const plan = {
        v: 1, kind: "form", name: "f", description: null,
        fields: [{
            name: "amount", label: "a", description: null,
            optional: false, enabled: true, hasDefault: true,
            default: 1e-7, node: expandNode({ kind: "float" }),
        }],
    };

    // Before the guard this mounted a control holding "1e-7" whose own grammar
    // reported it invalid, so the field could never become ready.
    assert.throws(() => compileForm(plan), /simple decimal/);
});


test("stepping never writes an exponent into the control", () => {
    const widget = new FloatWidget({ step: 1e-7 });

    widget.setValue(0);
    widget._step(1);

    // The step would land on 1e-7, so the widget refuses to move rather than
    // write text it would then call invalid.
    assert.equal(widget.input.value, "0");
    assert.equal(widget.value(), 0);
});
