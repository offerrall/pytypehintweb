import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { Field } from "../../src/pytypehintweb/static/fields.js";
import {
    IntChoiceWidget, IntWidget, StrChoiceWidget, StrWidget,
} from "../../src/pytypehintweb/static/inputs.js";

// setValue() is a scalar-widget operation: validate and apply. Containers are
// built from a plan through constructors, not mutated wholesale, so there is no
// composite setValue, form.setValue, candidate protocol or event batching. A
// Field's optional toggle is driven by setEnabled().


function counting(widget) {
    const state = { count: 0 };
    widget.onChange(() => { state.count += 1; });
    return state;
}


function optionalField(optionalEnabled) {
    return new Field(
        { name: "nickname", optional: true, optionalEnabled },
        new StrWidget());
}


test("str setValue updates value, readiness and emits", () => {
    const widget = new StrWidget({ minLength: 3 });
    const changes = counting(widget);

    assert.equal(widget.isReady(), false);

    widget.setValue("hello");

    assert.equal(widget.value(), "hello");
    assert.equal(widget.isReady(), true);
    assert.equal(changes.count, 1);
});


test("int setValue keeps the integer type", () => {
    const widget = new IntWidget({ min: 0, max: 100 });

    widget.setValue(42);

    assert.equal(widget.value(), 42);
    assert.equal(typeof widget.value(), "number");
});


test("slider setValue moves the slider", () => {
    const widget = new IntWidget({ slider: true, min: 0, max: 10 });

    widget.setValue(7);

    assert.equal(widget.value(), 7);
});


test("choice setValue selects one of the choices and preserves type", () => {
    const str = new StrChoiceWidget(["red", "green", "blue"]);
    str.setValue("green");
    assert.equal(str.value(), "green");

    const int = new IntChoiceWidget([10, 20, 50]);
    int.setValue(20);
    assert.equal(int.value(), 20);
    assert.equal(typeof int.value(), "number");
});


test("scalar setValue rejects incompatible values", () => {
    assert.throws(() => new StrWidget().setValue(5), /expects a string/);
    assert.throws(() => new IntWidget().setValue(1.5), /safe integer/);
    assert.throws(() => new StrChoiceWidget(["a", "b"]).setValue("z"),
                  /only one of its choices/);
});


// --- slider null ---------------------------------------------------------

test("an ordinary integer accepts null but a slider rejects it", () => {
    const ordinary = new IntWidget();
    ordinary.setValue(5);
    ordinary.setValue(null);
    assert.equal(ordinary.value(), null);
    assert.equal(ordinary.isEmpty(), true);

    const slider = new IntWidget({ slider: true, min: 0, max: 10 });
    assert.throws(() => slider.setValue(null),
                  /slider value must be a safe integer/);
});


test("a slider rejects setValue(null) the same way inside a Field", () => {
    const field = new Field(
        { name: "level" },
        new IntWidget({ slider: true, min: 0, max: 10 }));

    // The Field wrapper does not intercept the inner widget's rejection.
    assert.throws(() => field.widget.setValue(null),
                  /slider value must be a safe integer/);
});


test("a rejected slider null leaves the widget unchanged and emits nothing", () => {
    const slider = new IntWidget({ slider: true, min: 0, max: 10 });
    slider.setValue(7);

    const changes = counting(slider);

    // _check throws before _apply, so nothing is applied and no event fires.
    assert.throws(() => slider.setValue(null),
                  /slider value must be a safe integer/);
    assert.equal(slider.value(), 7);
    assert.equal(changes.count, 0);
});


// --- Field.setEnabled (the optional toggle) ------------------------------

test("setEnabled(true) turns on a disabled optional field and emits once", () => {
    const field = optionalField(false);
    const changes = counting(field);

    assert.equal(field.enabled(), false);
    assert.equal(field.widget.el.hidden, true);

    field.setEnabled(true);

    assert.equal(field.enabled(), true);
    assert.equal(field.widget.el.hidden, false);
    assert.equal(changes.count, 1);

    // The two-step prefill: enable, then assign the inner scalar widget.
    field.widget.setValue("Ada");
    assert.equal(field.value(), "Ada");
});


test("setEnabled(false) switches an optional field off, reading as null", () => {
    const field = optionalField(true);
    field.widget.setValue("Ada");

    field.setEnabled(false);

    assert.equal(field.enabled(), false);
    assert.equal(field.value(), null);
});


test("setEnabled to the current state emits nothing", () => {
    const field = optionalField(true);
    const changes = counting(field);

    field.setEnabled(true);

    assert.equal(changes.count, 0);
});


test("setEnabled rejects disabling a required field and non-booleans", () => {
    const required = new Field({ name: "value" }, new StrWidget());

    assert.throws(() => required.setEnabled(false),
                  /required field cannot be disabled/);
    assert.doesNotThrow(() => required.setEnabled(true));   // already on: no-op

    assert.throws(() => optionalField(false).setEnabled("yes"),
                  /expects a boolean/);
});
