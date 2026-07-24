import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type, walk } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { Field } from "../../src/pytypehintweb/static/fields.js";
import { StrWidget } from "../../src/pytypehintweb/static/inputs.js";


function build(fields, options = {}) {
    const form = compileForm({ v: 1, kind: "form", name: "a11y", fields },
                             { prefix: "a11y", ...options });
    const host = document.createElement("div");

    for (const field of form.fields) {
        host.append(field.widget.el);
    }

    return { form, host };
}


function widgetOf(form, name) {
    return form.fields.find((field) => field.name === name).widget;
}


function find(host, predicate) {
    return walk(host).filter(predicate);
}


function byId(host, id) {
    return walk(host).find((node) => node.id === id) ?? null;
}


function describedIds(control) {
    const value = control.getAttribute("aria-describedby");

    return value === null ? [] : value.split(" ");
}


test("a visible label is associated with its control", () => {
    const { form, host } = build([
        { name: "email", label: "Email", node: { kind: "str" } },
    ]);

    const label = find(host, (node) => node.tagName === "LABEL")[0];
    const input = widgetOf(form, "email").widget.input;

    assert.equal(label.textContent, "Email");
    assert.notEqual(input.id, "");
    assert.equal(label.htmlFor, input.id);
});


test("a description is referenced through aria-describedby", () => {
    const { form, host } = build([{
        name: "email",
        label: "Email",
        description: "Where we send the receipt.",
        node: { kind: "str" },
    }]);

    const input = widgetOf(form, "email").widget.input;
    const ids = describedIds(input);

    assert.equal(ids.length, 1);
    assert.equal(byId(host, ids[0]).textContent, "Where we send the receipt.");
});


test("a visible error is referenced through aria-describedby", () => {
    const { form, host } = build([{
        name: "value",
        node: { kind: "str", options: { minLength: 5 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    assert.deepEqual(describedIds(widget.input), []);

    type(widget, "ab");

    const ids = describedIds(widget.input);

    assert.equal(ids.length, 1);
    assert.equal(byId(host, ids[0]).textContent, widget.error());
});


test("a description and an error are referenced together", () => {
    const { form, host } = build([{
        name: "value",
        description: "Help text.",
        node: { kind: "str", options: { minLength: 5 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    type(widget, "ab");

    const ids = describedIds(widget.input);

    assert.equal(ids.length, 2);
    assert.deepEqual(ids.map((id) => byId(host, id).textContent),
                     ["Help text.", widget.error()]);
});


test("no description and no error leaves no dangling reference", () => {
    const { form } = build([{ name: "value", node: { kind: "str" } }]);

    assert.equal(
        widgetOf(form, "value").widget.input.hasAttribute("aria-describedby"),
        false);
});


test("a directly built Field treats a null description as absence", () => {
    // The plan compiler maps null to undefined, but the direct API takes null.
    // Either way absence must mean no empty <small>, no minted id, and no
    // aria-describedby pointing at nothing.
    for (const description of [null, undefined]) {
        const inner = new StrWidget();
        const field = new Field({ id: "d", name: "D", description }, inner);

        assert.equal(inner.control().hasAttribute("aria-describedby"), false);
        assert.deepEqual(
            walk(field.el).filter(
                (node) => (node.className ?? "").split(" ").includes(
                    "pth-description")),
            [],
            `a ${description} description should mint no description element`);
    }
});


test("a directly built Field renders a real description", () => {
    const inner = new StrWidget();
    const field = new Field(
        { id: "d", name: "D", description: "Help." }, inner);

    const ids = describedIds(inner.control());
    assert.equal(ids.length, 1);
    assert.equal(byId(field.el, ids[0]).textContent, "Help.");
});


test("correcting a value drops the error reference again", () => {
    const { form } = build([{
        name: "value",
        description: "Help text.",
        node: { kind: "str", options: { minLength: 3 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    type(widget, "ab");
    assert.equal(describedIds(widget.input).length, 2);

    type(widget, "abcd");
    assert.equal(describedIds(widget.input).length, 1);
});


test("aria-invalid waits for interaction, then follows the error", () => {
    const { form } = build([{
        name: "value",
        node: { kind: "str", options: { minLength: 3 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    // Validity is known immediately, but an untouched field is never marked:
    // the red state is not shown before the user has interacted.
    assert.equal(widget.hasError(), true);
    assert.equal(widget.input.hasAttribute("aria-invalid"), false);

    type(widget, "ab");

    assert.equal(widget.input.getAttribute("aria-invalid"), "true");

    type(widget, "abc");

    assert.equal(widget.hasError(), false);
    assert.equal(widget.input.hasAttribute("aria-invalid"), false);
});


test("an untouched empty integer is incomplete but not invalid", () => {
    const { form } = build([{ name: "value", node: { kind: "int" } }]);

    const widget = widgetOf(form, "value").widget;

    assert.equal(widget.isReady(), false);
    assert.equal(widget.hasError(), false);
    assert.equal(widget.input.hasAttribute("aria-invalid"), false);
});


test("a malformed integer is marked invalid and then cleared", () => {
    const { form } = build([{
        name: "value",
        node: { kind: "int", options: { min: 10 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    type(widget, "3");
    assert.equal(widget.input.getAttribute("aria-invalid"), "true");

    type(widget, "12");
    assert.equal(widget.input.hasAttribute("aria-invalid"), false);
});


test("an invalid nested child is marked without marking its siblings", () => {
    const { form } = build([{
        name: "address",
        label: "Address",
        node: {
            kind: "object",
            fields: [
                { name: "street", node: { kind: "str" } },
                { name: "city",
                  node: { kind: "str", options: { minLength: 3 } } },
            ],
        },
    }]);

    const group = widgetOf(form, "address").widget;
    const [street, city] = group.children.map((child) => child.widget.widget);

    // Nothing is marked until touched.
    assert.equal(city.input.hasAttribute("aria-invalid"), false);

    type(city, "ab");

    assert.equal(city.input.getAttribute("aria-invalid"), "true");
    assert.equal(street.input.hasAttribute("aria-invalid"), false);
});


test("a touched list below its minimum is marked invalid on its container", () => {
    const { form } = build([{
        name: "tags",
        node: { kind: "list", minItems: 2, item: { kind: "str" } },
    }]);

    const list = widgetOf(form, "tags").widget;

    // Below the minimum, but untouched: no visual mark.
    assert.equal(list.hasError(), true);
    assert.equal(list.el.hasAttribute("aria-invalid"), false);

    list.addButton.dispatch("click");

    assert.equal(list.el.getAttribute("aria-invalid"), "true");

    list.addButton.dispatch("click");

    assert.equal(list.hasError(), false);
    assert.equal(list.el.hasAttribute("aria-invalid"), false);
});


test("the optional toggle takes its name from the visible label", () => {
    const { form, host } = build([{
        name: "nickname",
        label: "Nickname",
        optional: true,
        node: { kind: "str" },
    }]);

    const field = widgetOf(form, "nickname");
    const named = byId(host, field.toggle.getAttribute("aria-labelledby"));

    assert.equal(named.textContent, "Nickname");
    assert.equal(field.toggle.type, "checkbox");
});


test("the optional toggle points at the content it controls", () => {
    const { form, host } = build([{
        name: "nickname",
        optional: true,
        node: { kind: "str" },
    }]);

    const field = widgetOf(form, "nickname");
    const controlled = byId(host, field.toggle.getAttribute("aria-controls"));

    assert.equal(controlled, field.widget.input);
});


test("the toggle of an optional group points at the group element", () => {
    const { form, host } = build([{
        name: "address",
        optional: true,
        node: {
            kind: "object",
            fields: [{ name: "street", node: { kind: "str" } }],
        },
    }]);

    const field = widgetOf(form, "address");
    const controlled = byId(host, field.toggle.getAttribute("aria-controls"));

    assert.equal(controlled, field.widget.el);
});


test("a disabled optional hides its content from assistive technology", () => {
    const { form } = build([{
        name: "nickname",
        optional: true,
        enabled: false,
        node: { kind: "str" },
    }]);

    const field = widgetOf(form, "nickname");

    assert.equal(field.widget.el.hidden, true);
    assert.equal(field.toggle.checked, false);

    field.toggle.checked = true;
    field.toggle.dispatch("change");

    assert.equal(field.widget.el.hidden, false);
});


test("a union is a named group with mode-navigation buttons, not a select", () => {
    const { form, host } = build([{
        name: "reference",
        label: "Reference",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
            ],
        },
    }]);

    const choice = widgetOf(form, "reference").widget;
    const label = find(host, (node) => node.tagName === "LABEL")[0];

    // No select: the group is named through the field label.
    assert.equal(walk(host).some((n) => n.tagName === "SELECT"), false);
    assert.equal(choice.el.getAttribute("role"), "group");
    assert.equal(byId(host, choice.el.getAttribute("aria-labelledby")).textContent,
                 "Reference");

    // Native previous/next buttons with accessible names.
    assert.equal(choice.previous.tagName, "BUTTON");
    assert.equal(choice.next.tagName, "BUTTON");
    assert.equal(choice.previous.getAttribute("aria-label"), "Previous mode");
    assert.equal(choice.next.getAttribute("aria-label"), "Next mode");
    assert.equal(choice.position.textContent, "Mode 1 of 2");
});


test("a closed-choice select is labelled and starts on its first option", () => {
    const { form, host } = build([{
        name: "size",
        label: "Size",
        node: { kind: "str", options: { choices: ["S", "M"] } },
    }]);

    const widget = widgetOf(form, "size").widget;
    const select = widget.el;
    const label = find(host, (node) => node.tagName === "LABEL")[0];

    assert.equal(label.htmlFor, select.id);
    assert.equal(select.children.length, 2);
    assert.equal(select.children[0].text, "S");
    assert.equal(widget.value(), "S");
    assert.equal(widget.isReady(), true);
});


test("an inactive union branch is detached, not merely hidden", () => {
    const { form } = build([{
        name: "reference",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
            ],
        },
    }]);

    const choice = widgetOf(form, "reference").widget;

    assert.ok(walk(choice.content).length > 0);

    choice.next.dispatch("click");

    assert.equal(choice.activeIndex(), 1);
    assert.equal(choice.content.children.length, 1);
    assert.equal(choice.content.children[0], choice.active().el);
});


test("the list add button keeps its accessible name", () => {
    const { form } = build([
        { name: "tags", node: { kind: "list", item: { kind: "str" } } },
    ]);

    const list = widgetOf(form, "tags").widget;

    assert.equal(list.addButton.textContent, "Add");
    assert.equal(list.addButton.type, "button");
});


test("remove buttons are distinguishable and reindex after removal", () => {
    const { form } = build([
        { name: "tags", node: { kind: "list", item: { kind: "str" } } },
    ]);

    const list = widgetOf(form, "tags").widget;

    list.add();
    list.add();
    list.add();

    assert.deepEqual(
        list.items.map((item) => item.removeButton.getAttribute("aria-label")),
        ["Remove 1", "Remove 2", "Remove 3"]);

    list.remove(list.items[0]);

    assert.deepEqual(
        list.items.map((item) => item.removeButton.getAttribute("aria-label")),
        ["Remove 1", "Remove 2"]);
});


test("a custom remove label is used for the accessible name", () => {
    const { form } = build([{
        name: "guests",
        node: {
            kind: "list",
            removeLabel: "Quitar",
            item: { kind: "str" },
        },
    }]);

    const list = widgetOf(form, "guests").widget;

    list.add();

    assert.equal(list.items[0].removeButton.getAttribute("aria-label"),
                 "Quitar 1");
});


test("list limits use native disabled instead of aria tricks", () => {
    const { form } = build([{
        name: "tags",
        node: {
            kind: "list",
            minItems: 1,
            maxItems: 2,
            item: { kind: "str" },
        },
    }]);

    const list = widgetOf(form, "tags").widget;

    list.add();

    assert.equal(list.items[0].removeButton.disabled, true);

    list.add();

    assert.equal(list.addButton.disabled, true);
    assert.equal(list.items[0].removeButton.disabled, false);
});


test("a nested object exposes a named group", () => {
    const { form, host } = build([{
        name: "address",
        label: "Address",
        node: {
            kind: "object",
            fields: [{ name: "street", node: { kind: "str" } }],
        },
    }]);

    const group = widgetOf(form, "address").widget.el;

    assert.equal(group.getAttribute("role"), "group");
    assert.equal(byId(host, group.getAttribute("aria-labelledby")).textContent,
                 "Address");
});


test("a list exposes a named group too", () => {
    const { form, host } = build([
        { name: "tags", label: "Tags", node: { kind: "list", item: { kind: "str" } } },
    ]);

    const list = widgetOf(form, "tags").widget.el;

    assert.equal(list.getAttribute("role"), "group");
    assert.equal(byId(host, list.getAttribute("aria-labelledby")).textContent,
                 "Tags");
});


test("ids stay unique across nested and repeated widgets", () => {
    const { form, host } = build([{
        name: "lines",
        label: "Lines",
        node: {
            kind: "list",
            item: {
                kind: "object",
                fields: [
                    { name: "sku", node: { kind: "str" } },
                    { name: "units", node: { kind: "int" } },
                ],
            },
        },
    }]);

    const list = widgetOf(form, "lines").widget;

    list.add();
    list.add();

    const ids = walk(host)
        .map((node) => node.id)
        .filter((id) => id !== "");

    assert.equal(ids.length, new Set(ids).size);
    assert.ok(ids.length > 6);
});


test("optional list items get distinct label/control ids", () => {
    const { form, host } = build([{
        name: "aliases",
        label: "Aliases",
        node: {
            kind: "list",
            item: { kind: "optional", node: { kind: "str" } },
        },
    }]);

    const list = widgetOf(form, "aliases").widget;

    list.add();
    list.add();

    // Each optional row is a Field with its own control; a label's htmlFor must
    // point at exactly one control, never a reused id shared across rows.
    const labels = find(host, (node) => node.tagName === "LABEL");
    const forIds = labels.map((label) => label.htmlFor).filter((id) => Boolean(id));
    const controlIds = walk(host)
        .filter((node) => node.tagName === "INPUT")
        .map((node) => node.id)
        .filter((id) => id !== "");

    assert.equal(forIds.length, new Set(forIds).size);
    assert.equal(controlIds.length, new Set(controlIds).size);
    assert.ok(forIds.every((id) => controlIds.includes(id)));
});


test("two forms built with the same prefix do not collide", () => {
    const fields = [{ name: "value", label: "Value", node: { kind: "str" } }];
    const first = build(fields);
    const second = build(fields);

    const idsOf = (host) => walk(host).map((n) => n.id).filter((id) => id !== "");
    const all = [...idsOf(first.host), ...idsOf(second.host)];

    assert.equal(all.length, new Set(all).size);
});


test("no widget sets a positive tabindex", () => {
    const { host } = build([
        { name: "a", node: { kind: "str" } },
        { name: "b", optional: true, node: { kind: "int" } },
        { name: "c", node: { kind: "list", item: { kind: "str" } } },
        { name: "d", node: { kind: "str", options: { choices: ["x", "y"] } } },
    ]);

    for (const node of walk(host)) {
        assert.equal(node.hasAttribute("tabindex"), false);
        assert.equal(node.hasAttribute("tabIndex"), false);
    }
});


test("validation messages are polite status regions", () => {
    const { form } = build([{
        name: "value",
        node: { kind: "str", options: { minLength: 3 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    assert.equal(widget.message.getAttribute("role"), "status");
    assert.equal(widget.message.getAttribute("aria-live"), "polite");
});


test("an untouched field shows no message even while invalid", () => {
    const { form } = build([{
        name: "value",
        node: { kind: "str", options: { minLength: 3 } },
    }]);

    const widget = widgetOf(form, "value").widget;

    assert.equal(widget.hasError(), true);
    assert.equal(widget.message.textContent, "");
    assert.equal(widget.message.hidden, true);
});


test("a directly constructed field is labelled without a plan", () => {
    const widget = new StrWidget({ minLength: 2 });
    const field = new Field({ name: "Standalone" }, widget);
    const label = find(field.el, (node) => node.tagName === "LABEL")[0];

    assert.equal(label.textContent, "Standalone");
    assert.equal(label.htmlFor, widget.input.id);
    assert.notEqual(widget.input.id, "");
});
