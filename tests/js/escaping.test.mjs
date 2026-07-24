import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { tagsIn, type, walk } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { Field } from "../../src/pytypehintweb/static/fields.js";
import { StrWidget } from "../../src/pytypehintweb/static/inputs.js";

const ATTACK = '<img src=x onerror="globalThis.hacked = true">';
const SCRIPT = "<script>globalThis.hacked = true</script>";
const ATTACK_TEMPLATE = `${ATTACK} {value}`;


function mount(plan) {
    const form = compileForm(plan, { prefix: "xss" });
    const host = document.createElement("div");

    for (const field of form.fields) {
        host.append(field.widget.el);
    }

    return { form, host };
}


function nodesWithText(host, text) {
    return walk(host).filter((node) => node.textContent === text);
}


test("a hostile label is rendered as text, not as markup", () => {
    const { host } = mount({
        v: 1,
        kind: "form",
        name: "test",
        description: ATTACK,
        fields: [{
            name: "value",
            label: ATTACK,
            description: ATTACK,
            node: {
                kind: "str",
                options: {
                    placeholder: ATTACK,
                    minLength: 2,
                    minMessage: ATTACK_TEMPLATE,
                },
            },
        }],
    });

    const label = walk(host).find((node) => node.tagName === "LABEL");

    assert.equal(label.textContent, ATTACK);
    assert.equal(globalThis.hacked, undefined);
});


test("a hostile placeholder reaches the input as an attribute value", () => {
    const { form } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            node: { kind: "str", options: { placeholder: ATTACK } },
        }],
    });

    const input = form.fields[0].widget.widget.input;

    assert.equal(input.getAttribute("placeholder"), ATTACK);
    assert.equal(globalThis.hacked, undefined);
});


test("a hostile validation message is rendered as text", () => {
    const { form, host } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            node: {
                kind: "str",
                options: { minLength: 5, minMessage: ATTACK_TEMPLATE },
            },
        }],
    });

    const widget = form.fields[0].widget.widget;

    type(widget, "ab");

    const expected = `${ATTACK} 5`;

    assert.equal(widget.error(), expected);
    assert.equal(widget.message.textContent, expected);
    assert.ok(nodesWithText(host, expected).length > 0);
    assert.equal(globalThis.hacked, undefined);
});


test("hostile stepper aria labels reach the buttons as text, not markup", () => {
    const { host } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            node: {
                kind: "int",
                options: { increaseLabel: ATTACK, decreaseLabel: SCRIPT },
            },
        }],
    });

    const buttons = walk(host).filter(
        (node) => node.className === "pth-number-btn");
    const labels = buttons.map((button) => button.getAttribute("aria-label"));

    assert.deepEqual(labels, [ATTACK, SCRIPT]);
    assert.equal(tagsIn(host).includes("IMG"), false);
    assert.equal(globalThis.hacked, undefined);
});


test("hostile text creates no element nodes of its own", () => {
    const { host } = mount({
        v: 1,
        kind: "form",
        name: "test",
        description: SCRIPT,
        fields: [{
            name: "value",
            label: SCRIPT,
            description: ATTACK,
            node: {
                kind: "str",
                options: { placeholder: ATTACK, rows: 3 },
            },
        }],
    });

    const tags = tagsIn(host);

    assert.equal(tags.includes("IMG"), false);
    assert.equal(tags.includes("SCRIPT"), false);
    assert.deepEqual([...new Set(tags)].sort(),
                     ["DIV", "LABEL", "SMALL", "TEXTAREA"]);
});


test("hostile list labels stay on the buttons as text", () => {
    const { form } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "tags",
            node: {
                kind: "list",
                addLabel: ATTACK,
                removeLabel: SCRIPT,
                minItems: 2,
                minMessage: ATTACK_TEMPLATE,
                item: { kind: "str" },
            },
        }],
    });

    const list = form.fields[0].widget.widget;

    list.add();

    const remove = list.items[0].removeButton;

    assert.equal(list.addButton.textContent, ATTACK);
    // The remove button shows a fixed icon; its hostile label survives only
    // as an accessible name, set through setAttribute (a text sink).
    assert.equal(remove.getAttribute("aria-label"), `${SCRIPT} 1`);
    assert.equal(tagsIn(remove).includes("IMG"), false);
    assert.equal(tagsIn(remove).includes("SCRIPT"), false);
    assert.equal(list.error(), `${ATTACK} 2`);
    assert.equal(globalThis.hacked, undefined);
});


test("a hostile branch value is never rendered by the mode navigator", () => {
    const { form } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            node: {
                kind: "choice",
                branches: [
                    { value: ATTACK, mode: "wrapped", node: { kind: "str" } },
                    { value: SCRIPT, mode: "wrapped", node: { kind: "int" } },
                ],
            },
        }],
    });

    const choice = form.fields[0].widget.widget;

    // The hostile value stays the transport discriminator, but it is never
    // shown: the navigator only renders "Mode N of M".
    assert.equal(choice.selectedValue(), ATTACK);
    assert.equal(tagsIn(choice.el).includes("IMG"), false);
    assert.equal(tagsIn(choice.el).includes("SCRIPT"), false);
    assert.deepEqual(nodesWithText(choice.el, ATTACK), []);
    assert.equal(globalThis.hacked, undefined);
});


test("hostile closed choices stay text in the select", () => {
    const { form } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            node: {
                kind: "str",
                options: { choices: [ATTACK, SCRIPT] },
            },
        }],
    });

    const select = form.fields[0].widget.widget.el;

    assert.deepEqual(select.children.map((option) => option.text),
                     [ATTACK, SCRIPT]);
    assert.equal(globalThis.hacked, undefined);
});


test("a hostile default value reaches the control as a value", () => {
    const { form } = mount({
        v: 1,
        kind: "form",
        name: "test",
        fields: [{
            name: "value",
            hasDefault: true,
            default: ATTACK,
            node: { kind: "str" },
        }],
    });

    const widget = form.fields[0].widget.widget;

    assert.equal(widget.value(), ATTACK);
    assert.equal(widget.input.value, ATTACK);
    assert.equal(globalThis.hacked, undefined);
});


test("a directly constructed widget is just as safe", () => {
    const widget = new StrWidget({ placeholder: ATTACK, minLength: 5,
                                   minMessage: `${SCRIPT} {value}` });
    const field = new Field({ id: "x", name: ATTACK, description: SCRIPT },
                            widget);

    type(widget, "ab");

    const tags = tagsIn(field.el);

    assert.equal(tags.includes("IMG"), false);
    assert.equal(tags.includes("SCRIPT"), false);
    assert.equal(widget.message.textContent, `${SCRIPT} 5`);
    assert.equal(globalThis.hacked, undefined);
});


test("the test DOM refuses innerHTML, so an unsafe sink would fail here", () => {
    const element = document.createElement("div");

    assert.throws(() => { element.innerHTML = "<b>x</b>"; }, /innerHTML/);
    assert.throws(() => element.insertAdjacentHTML("beforeend", "<b>x</b>"),
                  /insertAdjacentHTML/);
    assert.throws(() => element.setAttribute("onclick", "boom()"),
                  /not allowed from plan text/);
});


test("dangerous attributes can never be written from plan text", () => {
    const element = document.createElement("div");

    for (const name of ["onclick", "onerror", "href", "src", "srcdoc",
                        "style", "formaction"]) {
        assert.throws(() => element.setAttribute(name, "x"),
                      /not allowed from plan text/,
                      `${name} should be refused`);
    }
});


const SAFE = new Set([
    "min", "max", "step", "rows", "pattern", "placeholder", "title", "type",
    "role", "aria-label", "aria-labelledby", "aria-describedby",
    "aria-invalid", "aria-controls",
]);


test("a widget only ever writes attributes from the safe set", () => {
    const widget = new StrWidget({
        placeholder: ATTACK,
        pattern: "[a-z]+",
        minLength: 2,
    });

    const written = Object.keys(widget.input.attributes);

    assert.ok(written.length > 0);
    assert.deepEqual(written.filter((name) => !SAFE.has(name)), []);
});
