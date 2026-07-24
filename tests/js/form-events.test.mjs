import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type } from "./dom.mjs";
import { compileForm } from "./harness.mjs";


function build(fields) {
    return compileForm({ v: 1, kind: "form", name: "events", fields },
                       { prefix: "e" });
}


function counted(form) {
    const state = { count: 0 };
    state.off = form.onChange(() => { state.count += 1; });
    return state;
}


test("a scalar change reaches form.onChange once", () => {
    const form = build([{ name: "a", node: { kind: "str" } }]);
    const state = counted(form);

    type(form.fields[0].widget.widget, "hi");

    assert.equal(state.count, 1);
});


test("a nested struct change reaches form.onChange once", () => {
    const form = build([{
        name: "profile",
        node: {
            kind: "object",
            fields: [{ name: "name", node: { kind: "str" } }],
        },
    }]);
    const state = counted(form);

    const group = form.fields[0].widget.widget;
    type(group.children[0].widget.widget, "Ana");

    assert.equal(state.count, 1);
});


test("adding a list row reaches form.onChange once", () => {
    const form = build([{
        name: "tags",
        node: { kind: "list", item: { kind: "str" } },
    }]);
    const state = counted(form);

    form.fields[0].widget.widget.add();

    assert.equal(state.count, 1);
});


test("a union mode change reaches form.onChange once", () => {
    const form = build([{
        name: "value",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
            ],
        },
    }]);
    const state = counted(form);

    form.fields[0].widget.widget.next.dispatch("click");

    assert.equal(state.count, 1);
});


test("unsubscribing from form.onChange stops the callbacks", () => {
    const form = build([{ name: "a", node: { kind: "str" } }]);
    const state = counted(form);

    state.off();
    type(form.fields[0].widget.widget, "hi");

    assert.equal(state.count, 0);
});
