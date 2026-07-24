import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type } from "./dom.mjs";
import { compileForm } from "./harness.mjs";


function build(fields) {
    return compileForm({ v: 1, kind: "form", name: "example", fields },
                       { prefix: "read" });
}


function widgetOf(form, name) {
    return form.fields.find((field) => field.name === name).widget.widget;
}


test("read() is callable while the form is not ready", () => {
    const form = build([
        { name: "value", node: { kind: "str", options: { minLength: 5 } } },
    ]);

    assert.equal(form.isReady(), false);
    assert.doesNotThrow(() => form.read());
});


test("an untouched integer reads as null", () => {
    const form = build([{ name: "value", node: { kind: "int" } }]);

    assert.equal(form.isReady(), false);
    assert.deepEqual(form.read(), { value: null });
});


test("an unparsable integer reads as null", () => {
    const form = build([{ name: "value", node: { kind: "int" } }]);

    type(widgetOf(form, "value"), "abc");

    assert.deepEqual(form.read(), { value: null });
});


test("an invalid but representable integer travels unchanged", () => {
    const form = build([
        { name: "value", node: { kind: "int", options: { min: 10 } } },
    ]);

    type(widgetOf(form, "value"), "3");

    assert.equal(form.hasError(), true);
    assert.deepEqual(form.read(), { value: 3 });
});


test("a syntactically valid but unsafe integer reads as null, not rounded", () => {
    const form = build([{ name: "value", node: { kind: "int" } }]);
    const widget = widgetOf(form, "value");

    type(widget, "9007199254740993");

    // The raw text stays visible, the form is not ready, and read() reports the
    // honest null instead of the rounded 9007199254740992.
    assert.equal(widget.input.value, "9007199254740993");
    assert.equal(form.isReady(), false);
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be a safe integer");
    assert.deepEqual(form.read(), { value: null });
});


test("an invalid but representable string travels unchanged", () => {
    const form = build([
        { name: "value", node: { kind: "str", options: { minLength: 5 } } },
    ]);

    type(widgetOf(form, "value"), "ab");

    assert.equal(form.hasError(), true);
    assert.deepEqual(form.read(), { value: "ab" });
});


test("an untouched string reads as the empty string, not null", () => {
    const form = build([{ name: "value", node: { kind: "str" } }]);

    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), { value: "" });
});


test("a list with no rows reads as an empty array", () => {
    const form = build([
        { name: "tags", node: { kind: "list", item: { kind: "str" } } },
    ]);

    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), { tags: [] });
});


test("a list below minItems reads its rows and is not ready", () => {
    const form = build([{
        name: "tags",
        node: { kind: "list", minItems: 2, item: { kind: "str" } },
    }]);

    widgetOf(form, "tags").add();

    assert.equal(form.isReady(), false);
    assert.deepEqual(form.read(), { tags: [""] });
});


test("an incomplete inline union keeps its discriminator", () => {
    const form = build([{
        name: "item",
        node: {
            kind: "choice",
            branches: [
                {
                    value: "Shirt",
                    mode: "inline",
                    node: {
                        kind: "object",
                        fields: [{ name: "size", node: { kind: "str" } }],
                    },
                },
                {
                    value: "Mug",
                    mode: "inline",
                    node: {
                        kind: "object",
                        fields: [{ name: "litres", node: { kind: "int" } }],
                    },
                },
            ],
        },
    }]);

    assert.deepEqual(form.read(), { item: { $type: "Shirt", size: "" } });
});


test("an incomplete nested object reads field by field", () => {
    const form = build([{
        name: "address",
        node: {
            kind: "object",
            fields: [
                { name: "street", node: { kind: "str" } },
                { name: "number", node: { kind: "int" } },
            ],
        },
    }]);

    assert.equal(form.isReady(), false);
    assert.deepEqual(form.read(), { address: { street: "", number: null } });
});


test("a list with an invalid item keeps the item in the transport", () => {
    const form = build([{
        name: "sizes",
        node: {
            kind: "list",
            minItems: 1,
            item: { kind: "int", options: { min: 5 } },
        },
    }]);

    const list = widgetOf(form, "sizes");
    list.add();
    type(list.widgets()[0], "1");

    assert.equal(form.hasError(), true);
    assert.deepEqual(form.read(), { sizes: [1] });
});


test("an enabled optional with an incomplete child reads as null", () => {
    const form = build([
        { name: "age", optional: true, node: { kind: "int" } },
    ]);

    assert.equal(form.isReady(), false);
    assert.deepEqual(form.read(), { age: null });
});


test("a disabled optional reads as null and is ready", () => {
    const form = build([
        {
            name: "age",
            optional: true,
            enabled: false,
            node: { kind: "int" },
        },
    ]);

    assert.equal(form.isReady(), true);
    assert.equal(form.hasError(), false);
    assert.deepEqual(form.read(), { age: null });
});


test("an incomplete choice branch still carries its transport wrapper", () => {
    const form = build([{
        name: "reference",
        node: {
            kind: "choice",
            branches: [
                {
                    value: "str",
                    mode: "wrapped",
                    node: { kind: "str", options: { minLength: 4 } },
                },
                { value: "int", mode: "wrapped", node: { kind: "int" } },
            ],
        },
    }]);

    assert.equal(form.isReady(), false);
    assert.deepEqual(form.read(),
                     { reference: { $type: "str", $value: "" } });
});


test("readiness stays accurate while read() reports incomplete values", () => {
    const form = build([
        { name: "name", node: { kind: "str", options: { minLength: 2 } } },
        { name: "age", node: { kind: "int" } },
    ]);

    assert.equal(form.isReady(), false);

    type(widgetOf(form, "name"), "ada");

    assert.equal(form.isReady(), false);

    type(widgetOf(form, "age"), "36");

    assert.equal(form.isReady(), true);
    assert.equal(form.hasError(), false);
    assert.deepEqual(form.read(), { name: "ada", age: 36 });
});
