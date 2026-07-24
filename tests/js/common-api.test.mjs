import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { compileForm } from "./harness.mjs";


const PLAN = {
    v: 1,
    kind: "form",
    name: "everything",
    fields: [
        { name: "s", node: { kind: "str" } },
        { name: "i", node: { kind: "int" } },
        { name: "sc", node: { kind: "str", options: { choices: ["a", "b"] } } },
        { name: "ic", node: { kind: "int", options: { choices: [1, 2] } } },
        {
            name: "sl",
            node: { kind: "int", options: { slider: true, min: 0, max: 10 } },
        },
        { name: "lst", node: { kind: "list", item: { kind: "str" } } },
        {
            name: "obj",
            node: {
                kind: "object",
                fields: [{ name: "x", node: { kind: "str" } }],
            },
        },
        {
            name: "un",
            node: {
                kind: "choice",
                branches: [
                    { value: "str", mode: "plain", node: { kind: "str" } },
                    { value: "int", mode: "plain", node: { kind: "int" } },
                ],
            },
        },
        { name: "opt", optional: true, node: { kind: "str" } },
    ],
};

const MEMBERS = ["value", "setValue", "isReady", "hasError", "onChange"];


function everyWidget() {
    const form = compileForm(PLAN, { prefix: "api" });
    const widgets = [];

    for (const field of form.fields) {
        widgets.push(field.widget);
        widgets.push(field.widget.widget);
    }

    return widgets;
}


test("every public widget exposes the common contract", () => {
    for (const widget of everyWidget()) {
        const label = widget.constructor.name;

        assert.ok(widget.el, `${label}.el is missing`);

        for (const member of MEMBERS) {
            assert.equal(typeof widget[member], "function",
                         `${label}.${member}() is missing`);
        }
    }
});


test("the common contract covers every widget class once", () => {
    const classes = new Set(everyWidget().map((w) => w.constructor.name));

    for (const name of [
        "Field", "GroupWidget", "ListWidget", "ChoiceWidget",
        "StrWidget", "IntWidget", "StrChoiceWidget", "IntChoiceWidget",
    ]) {
        assert.ok(classes.has(name), `no ${name} instance was covered`);
    }
});


// setValue() is a scalar-widget operation. A container exposes the method so the
// contract is uniform, but calling it fails deliberately with a clear TypeError
// instead of leaking the abstract "must implement _check" message from the base.
const CONTAINERS = new Set(["Field", "GroupWidget", "ListWidget", "ChoiceWidget"]);


test("a container's setValue throws a clear, deliberate TypeError", () => {
    const seen = new Set();

    for (const widget of everyWidget()) {
        const label = widget.constructor.name;

        if (!CONTAINERS.has(label)) {
            continue;
        }

        seen.add(label);
        assert.throws(
            () => widget.setValue("anything"),
            (error) => error instanceof TypeError
                && /does not support setValue\(\)/.test(error.message)
                && !/_check/.test(error.message),
            `${label}.setValue should reject clearly`);
    }

    for (const name of CONTAINERS) {
        assert.ok(seen.has(name), `no ${name} instance was exercised`);
    }
});


test("a scalar widget's setValue still assigns", () => {
    const form = compileForm(PLAN, { prefix: "api" });
    const str = form.fields[0].widget.widget;

    str.setValue("hello");
    assert.equal(str.value(), "hello");
});
