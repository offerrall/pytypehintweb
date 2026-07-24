import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type, walk } from "./dom.mjs";
import { INT_DEFAULTS, LIST_DEFAULTS } from "../../src/pytypehintweb/static/defaults.js";
import { compileForm as rawCompileForm } from "../../src/pytypehintweb/static/form.js";
import { IntWidget } from "../../src/pytypehintweb/static/inputs.js";
import { compileForm } from "./harness.mjs";


// A single, compact-authored plan; the harness expands it to the one true
// representation the product accepts.
const PLAN = {
    kind: "form",
    name: "login",
    fields: [
        {
            name: "username",
            label: "Usuario",
            node: { kind: "str", options: { minLength: 3 } },
        },
        {
            name: "password",
            node: { kind: "str", options: { minLength: 8, password: true } },
        },
        {
            name: "attempts",
            hasDefault: true,
            default: 3,
            node: { kind: "int", options: { min: 1, max: 5 } },
        },
        {
            name: "tags",
            node: { kind: "list", minItems: 1, item: { kind: "str" } },
        },
        {
            name: "nickname",
            optional: true,
            enabled: false,
            hasDefault: true,
            default: null,
            node: { kind: "str" },
        },
    ],
};


function state(form) {
    return {
        names: form.fields.map((field) => field.name),
        labels: form.fields.map((field) => field.widget.el.children[0].children[0]
            .textContent),
        isReady: form.isReady(),
        hasError: form.hasError(),
        value: form.fields.map((field) => field.widget.value()),
        read: form.read(),
    };
}


function widgetOf(form, name) {
    return form.fields.find((field) => field.name === name).widget.widget;
}


test("the whole plan builds a ready-to-use form", () => {
    const form = compileForm(PLAN, { prefix: "a" });

    type(widgetOf(form, "username"), "ana");
    type(widgetOf(form, "password"), "hunter22");
    widgetOf(form, "tags").add();
    type(widgetOf(form, "tags").widgets()[0], "web");

    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), {
        username: "ana",
        password: "hunter22",
        attempts: 3,
        tags: ["web"],
        nickname: null,
    });
});


test("a field default initialises its widget", () => {
    const form = compileForm(PLAN, { prefix: "a" });

    assert.equal(widgetOf(form, "attempts").value(), 3);
});


test("a field label defaults to the field name", () => {
    const form = compileForm(PLAN, { prefix: "a" });
    const header = form.fields[1].widget.el.children[0].children[0];

    assert.equal(header.textContent, "password");
});


test("the plan's message reaches the widget", () => {
    const form = compileForm(PLAN, { prefix: "a" });
    const username = widgetOf(form, "username");

    type(username, "ab");

    assert.equal(username.error(), "Must contain at least 3 characters");
});


test("a custom message in the plan reaches the widget", () => {
    const plan = {
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: {
                kind: "str",
                options: { minLength: 3, minMessage: "Al menos {value}" },
            },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });

    type(widgetOf(form, "value"), "ab");

    assert.equal(widgetOf(form, "value").error(), "Al menos 3");
});


test("the plan's list labels reach the widget", () => {
    const form = compileForm(PLAN, { prefix: "a" });
    const tags = widgetOf(form, "tags");

    assert.equal(tags.addButton.textContent, LIST_DEFAULTS.addLabel);
    assert.equal(tags.error(), "Add at least 1 items");
});


test("compileForm rejects an unsupported version before building anything", () => {
    assert.throws(
        () => rawCompileForm({
            v: 3,
            kind: "form",
            name: "example",
            description: null,
            fields: [],
        }),
        /unsupported plan version: 3/,
    );

    assert.throws(
        () => rawCompileForm({
            kind: "form",
            name: "example",
            description: null,
            fields: [],
        }),
        /plan\.v: is required/,
    );
});


test("compileForm rejects an unknown property before building anything", () => {
    assert.throws(
        () => compileForm({
            kind: "form",
            name: "example",
            fields: [{ name: "value", node: { kind: "str", options: { rows: 2 } },
                       hidden: true }],
        }),
        /unknown property/,
    );
});


test("the transport of a compact choice keeps its mode", () => {
    const plan = {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: {
                kind: "choice",
                branches: [
                    { value: "str", mode: "wrapped", node: { kind: "str" } },
                    { value: "int", mode: "wrapped", node: { kind: "int" } },
                ],
            },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });

    type(form.fields[0].widget.widget.active(), "hola");

    assert.deepEqual(form.read(), { value: { $type: "str", $value: "hola" } });
});


test("a compact choice never shows its branch values as visible text", () => {
    const plan = {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: {
                kind: "choice",
                branches: [
                    { value: "str", mode: "plain", node: { kind: "str" } },
                    { value: "int", mode: "plain", node: { kind: "int" } },
                ],
            },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });
    const choice = form.fields[0].widget.widget;

    // The technical branch id is still the transport discriminator...
    assert.equal(choice.selectedValue(), "str");

    // ...but it appears nowhere in the visible text.
    const texts = walk(choice.el).map((node) => node.textContent);
    assert.equal(texts.includes("str"), false);
    assert.equal(texts.includes("int"), false);
    assert.equal(choice.position.textContent, "Mode 1 of 2");
});


test("a directly constructed slider shows its value by default", () => {
    const widget = new IntWidget({ slider: true, min: 0, max: 10 });

    assert.notEqual(widget.readout, null);
});


test("a plan-created slider follows the plan default instead", () => {
    const plan = {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: { kind: "int", options: { slider: true, min: 0, max: 10 } },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });

    assert.equal(INT_DEFAULTS.showValue, false);
    assert.equal(widgetOf(form, "value").readout, null);
});


test("a plan-created slider shows its value when the plan says so", () => {
    const plan = {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: {
                kind: "int",
                options: { slider: true, min: 0, max: 10, showValue: true },
            },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });

    assert.notEqual(widgetOf(form, "value").readout, null);
});


test("form.onChange fires once per user action and unsubscribes cleanly", () => {
    const form = compileForm(PLAN, { prefix: "a" });

    let changes = 0;
    const off = form.onChange(() => { changes += 1; });

    type(widgetOf(form, "username"), "ana");
    assert.equal(changes, 1);

    type(widgetOf(form, "password"), "hunter22");
    assert.equal(changes, 2);

    off();
    off();

    type(widgetOf(form, "username"), "another");

    assert.equal(changes, 2);
});


test("form.onChange rejects a non-function", () => {
    const form = compileForm(PLAN, { prefix: "a" });

    assert.throws(() => form.onChange(null), /must be a function/);
});


test("a compact optional list item uses the official item label", () => {
    const plan = {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{
            name: "value",
            node: {
                kind: "list",
                item: { kind: "optional", node: { kind: "str" } },
            },
        }],
    };

    const form = compileForm(plan, { prefix: "a" });
    const list = form.fields[0].widget.widget;

    list.add();

    const label = list.widgets()[0].el.children[0].children[0];

    assert.equal(label.textContent, "Item");
});


test("form.showErrors reveals held-back messages across fields, sparing a disabled one", () => {
    const form = compileForm({
        kind: "form",
        name: "signup",
        fields: [
            { name: "user", node: { kind: "str", options: {
                minLength: 3, minMessage: "Must contain at least {value} characters" } } },
            { name: "docs", node: { kind: "file", options: {
                multiple: true, minFiles: 1, minMessage: "Add at least {value} files" } } },
            { name: "note", optional: true, enabled: false, node: {
                kind: "str", options: { minLength: 5 } } },
        ],
    });

    const user = form.fields[0].widget.widget;
    const docs = form.fields[1].widget.widget;
    const note = form.fields[2].widget.widget;

    // Untouched: the form is not ready, yet no message is shown anywhere.
    assert.equal(form.isReady(), false);
    assert.equal(user.message.hidden, true);
    assert.equal(docs.message.hidden, true);
    assert.equal(note.message.hidden, true);

    form.showErrors();

    // Every enabled field reveals its held-back message.
    assert.equal(user.message.hidden, false);
    assert.equal(user.message.textContent, "Must contain at least 3 characters");
    assert.equal(docs.message.hidden, false);
    assert.equal(docs.message.textContent, "Add at least 1 files");

    // The switched-off optional stays clean — it reads null and is never in error.
    assert.equal(note.message.hidden, true);

    // showErrors only reveals; it changes neither value nor readiness.
    assert.equal(form.isReady(), false);
});
