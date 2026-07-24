import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { walk } from "./dom.mjs";
import { IntWidget } from "../../src/pytypehintweb/static/inputs.js";


function typeInto(widget, raw) {
    widget.input.value = raw;
    widget.input.dispatch("input");
}


function stepButtons(widget) {
    return walk(widget.el).filter(
        (node) => node.className === "pth-number-btn");
}


test("well-formed integer text parses to the exact value", () => {
    const widget = new IntWidget();

    typeInto(widget, "12");
    assert.equal(widget.value(), 12);
    assert.equal(widget.input.value, "12");

    typeInto(widget, "-12");
    assert.equal(widget.value(), -12);
    assert.equal(widget.input.value, "-12");
});


test("empty integer text is incomplete but not invalid", () => {
    const widget = new IntWidget();

    typeInto(widget, "");
    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
    assert.equal(widget.hasError(), false);
});


test("malformed integer text stays verbatim and reads as null", () => {
    const widget = new IntWidget();

    for (const raw of ["1.5", "1-2", "abc", "3.14e2", "- 5"]) {
        typeInto(widget, raw);
        assert.equal(widget.input.value, raw, `raw text ${raw} was rewritten`);
        assert.equal(widget.value(), null, `${raw} should read as null`);
        assert.equal(widget.hasError(), true, `${raw} should be invalid`);
    }
});


test("no character is silently deleted, trimmed or reordered", () => {
    const widget = new IntWidget();

    typeInto(widget, "12a3");
    assert.equal(widget.input.value, "12a3");
    assert.equal(widget.value(), null);
});


// --- unsafe integers are never transported as a rounded number --------------

test("a raw unsafe positive integer stays visible and reads as null", () => {
    const widget = new IntWidget();

    typeInto(widget, "9007199254740993");

    assert.equal(widget.input.value, "9007199254740993");
    assert.equal(widget.value(), null);
    assert.equal(widget.isReady(), false);
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be a safe integer");
});


test("a raw unsafe negative integer stays visible and reads as null", () => {
    const widget = new IntWidget();

    typeInto(widget, "-9007199254740993");

    assert.equal(widget.input.value, "-9007199254740993");
    assert.equal(widget.value(), null);
    assert.equal(widget.error(), "Must be a safe integer");
});


test("the rounded number never appears anywhere for an unsafe integer", () => {
    const widget = new IntWidget();

    // Number("9007199254740993") rounds to 9007199254740992; that value must
    // not surface through value(), number() or the visible text.
    typeInto(widget, "9007199254740993");

    assert.notEqual(widget.value(), 9007199254740992);
    assert.notEqual(widget.number(), 9007199254740992);
    assert.equal(widget.value(), null);
    assert.equal(widget.input.value.includes("9007199254740992"), false);
});


test("the largest safe integer is valid", () => {
    const widget = new IntWidget();

    typeInto(widget, "9007199254740991");

    assert.equal(widget.value(), 9007199254740991);
    assert.equal(widget.hasError(), false);
});


test("empty, invalid and unsafe integer states are distinct", () => {
    const widget = new IntWidget();

    typeInto(widget, "");
    assert.equal(widget.error(), null);

    typeInto(widget, "1.5");
    assert.equal(widget.error(), "Enter a valid integer");

    typeInto(widget, "9007199254740993");
    assert.equal(widget.error(), "Must be a safe integer");
});


// --- numeric stepper stride (item: pin step ?? multipleOf ?? 1) -------------

test("an explicit step drives the stepper increment", () => {
    const widget = new IntWidget({ step: 5 });

    assert.equal(widget.stepAmount, 5);

    widget._step(1);
    assert.equal(widget.value(), 5);
});


test("multipleOf drives the stepper increment when step is absent", () => {
    const widget = new IntWidget({ multipleOf: 3 });

    assert.equal(widget.stepAmount, 3);

    widget._step(1);
    assert.equal(widget.value(), 3);
});


test("the stepper increment falls back to one", () => {
    const widget = new IntWidget();

    assert.equal(widget.stepAmount, 1);

    widget._step(1);
    assert.equal(widget.value(), 1);
});


test("a slider grid ignores multipleOf and stays step ?? 1", () => {
    const withStep = new IntWidget({ slider: true, min: 0, max: 20, step: 5 });
    assert.equal(withStep.input.getAttribute("step"), "5");

    const withMultiple =
        new IntWidget({ slider: true, min: 0, max: 20, multipleOf: 5 });
    assert.equal(withMultiple.input.getAttribute("step"), "1");
});


// --- configurable stepper accessibility labels ------------------------------

test("the stepper buttons carry the default accessibility labels", () => {
    const labels = stepButtons(new IntWidget())
        .map((button) => button.getAttribute("aria-label"));

    assert.deepEqual(labels, ["Increase", "Decrease"]);
});


test("custom stepper labels become the button aria labels", () => {
    const widget = new IntWidget({ increaseLabel: "Subir", decreaseLabel: "Bajar" });
    const labels = stepButtons(widget).map((b) => b.getAttribute("aria-label"));

    assert.deepEqual(labels, ["Subir", "Bajar"]);
});


test("a slider renders no stepper buttons to label", () => {
    const widget = new IntWidget({ slider: true, min: 0, max: 10 });

    assert.equal(stepButtons(widget).length, 0);
});
