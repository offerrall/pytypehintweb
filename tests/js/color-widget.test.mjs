import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { compileForm } from "./harness.mjs";
import { COLOR_PATTERN, StrWidget } from "../../src/pytypehintweb/static/inputs.js";


function colorWidget(overrides = {}) {
    return new StrWidget({
        pattern: COLOR_PATTERN,
        patternMessage: "Hex color like #ff5733",
        ...overrides,
    });
}


// --- the opt-in is by the published constant, nothing else ------------------

test("a StrWidget whose pattern is COLOR_PATTERN mounts a colour picker", () => {
    const widget = colorWidget();

    assert.notEqual(widget.picker, null);
    assert.equal(widget.picker.type, "color");
    assert.equal(widget.picker.getAttribute("aria-label"), "Color picker");
});


test("an equivalent pattern written differently gets no picker", () => {
    // Same language, different string: the opt-in is string equality with the
    // published constant, not regex equivalence.
    const widget = new StrWidget({ pattern: "#[0-9A-Fa-f]{6}" });

    assert.equal(widget.picker, null);
});


test("a str node with no pattern mounts nothing extra", () => {
    const widget = new StrWidget();

    assert.equal(widget.picker, null);
});


test("a colour pattern on a textarea gets no picker", () => {
    // A picker beside a multi-line box makes no sense; the assistant is for the
    // single-line input only.
    const widget = colorWidget({ rows: 3 });

    assert.equal(widget.picker, null);
});


// --- the text field stays the source of truth -------------------------------

test("the picker writes its value into the text and emits one change", () => {
    const widget = colorWidget();
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    widget.picker.value = "#ff5733";
    widget.picker.dispatch("input");

    assert.equal(widget.value(), "#ff5733");
    assert.equal(changes, 1);
    // The user acted, so the field is touched and its message logic runs.
    assert.equal(widget.touched, true);
    assert.equal(widget.hasError(), false);
});


test("typing a valid colour syncs the picker, lowercased like a real input", () => {
    const widget = colorWidget();

    widget.input.value = "#00FF00";
    widget.input.dispatch("input");

    assert.equal(widget.picker.value, "#00ff00");
});


test("invalid or empty text leaves the picker as it was", () => {
    const widget = colorWidget();

    widget.input.value = "#123456";
    widget.input.dispatch("input");
    assert.equal(widget.picker.value, "#123456");

    // A picker cannot represent an invalid or empty value, so it stays put while
    // the text — the source of truth — is flagged invalid.
    widget.input.value = "not-a-color";
    widget.input.dispatch("input");
    assert.equal(widget.picker.value, "#123456");
    assert.equal(widget.error(), "Hex color like #ff5733");

    widget.input.value = "";
    widget.input.dispatch("input");
    assert.equal(widget.picker.value, "#123456");
});


test("setValue applies the string and re-syncs the picker", () => {
    const widget = colorWidget();

    widget.setValue("#ABCDEF");

    assert.equal(widget.value(), "#ABCDEF");
    assert.equal(widget.picker.value, "#abcdef");
});


// --- mounted from a plan ----------------------------------------------------

test("a colour field mounted from a plan carries the picker and reads the text", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "bg",
            node: {
                kind: "str",
                options: { pattern: COLOR_PATTERN,
                           patternMessage: "Hex color like #ff5733" },
            },
        }],
    });

    const widget = form.fields[0].widget.widget;

    assert.notEqual(widget.picker, null);

    widget.picker.value = "#0a0b0c";
    widget.picker.dispatch("input");

    assert.equal(form.read().bg, "#0a0b0c");
});
