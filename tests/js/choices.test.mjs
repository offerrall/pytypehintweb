import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { select } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import {
    IntChoiceWidget, StrChoiceWidget,
} from "../../src/pytypehintweb/static/inputs.js";


function build(node, extra = {}) {
    return compileForm({
        v: 1,
        kind: "form",
        name: "example",
        fields: [{ name: "value", node, ...extra }],
    }, { prefix: "c" });
}


test("a direct str choice starts on the first choice and is ready", () => {
    const widget = new StrChoiceWidget(["red", "green", "blue"]);

    assert.equal(widget.value(), "red");
    assert.equal(widget.isEmpty(), false);
    assert.equal(widget.isReady(), true);
});


test("an explicit initial value wins over the first choice", () => {
    const widget = new StrChoiceWidget(["red", "green", "blue"], "green");

    assert.equal(widget.value(), "green");
    assert.equal(widget.isReady(), true);
});


test("an int choice preserves the integer type", () => {
    const widget = new IntChoiceWidget([10, 20, 50]);

    assert.equal(widget.value(), 10);
    assert.equal(typeof widget.value(), "number");

    select(widget, 1);

    assert.equal(widget.value(), 20);
    assert.equal(typeof widget.value(), "number");
});


test("empty choices are rejected by the widget", () => {
    assert.throws(() => new StrChoiceWidget([]), /non-empty array of choices/);
    assert.throws(() => new IntChoiceWidget([]), /non-empty array of choices/);
});


test("a no-default choice reads its first value through the form", () => {
    const form = build({ kind: "str", options: { choices: ["red", "green"] } });

    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), { value: "red" });
});


test("an explicit choice default reaches form.read()", () => {
    const form = build(
        { kind: "str", options: { choices: ["red", "green", "blue"] } },
        { hasDefault: true, default: "green" });

    assert.deepEqual(form.read(), { value: "green" });
});


test("an int choice reads back as an integer through the form", () => {
    const form = build({ kind: "int", options: { choices: [10, 20, 50] } });

    assert.deepEqual(form.read(), { value: 10 });
    assert.equal(typeof form.read().value, "number");
});


test("an optional choice still supports None through its toggle", () => {
    const form = build(
        { kind: "str", options: { choices: ["red", "green"] } },
        { optional: true });

    assert.deepEqual(form.read(), { value: "red" });

    const toggle = form.fields[0].widget.toggle;
    toggle.checked = false;
    toggle.dispatch("change");

    assert.deepEqual(form.read(), { value: null });
});
