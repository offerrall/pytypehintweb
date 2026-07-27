import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { walk } from "./dom.mjs";
import { compileForm } from "./harness.mjs";


function mount(fields) {
    const form = compileForm({ v: 1, kind: "form", name: "css", fields },
                             { prefix: "css" });
    const host = document.createElement("div");

    for (const field of form.fields) {
        host.append(field.widget.el);
    }

    return { form, host };
}


function classes(host) {
    return new Set(walk(host).flatMap((node) => node.className
        ? node.className.split(/\s+/)
        : []));
}


test("string, int and choice widgets keep the classes the stylesheet targets", () => {
    const { host } = mount([
        { name: "text", node: { kind: "str" } },
        { name: "area", node: { kind: "str", options: { rows: 3 } } },
        { name: "secret", node: { kind: "str", options: { password: true } } },
        { name: "count", node: { kind: "int" } },
        { name: "level", node: {
            kind: "int",
            options: { slider: true, showValue: true, min: 0, max: 10 } } },
        { name: "size", node: {
            kind: "str", options: { choices: ["S", "M"] } } },
    ]);

    const present = classes(host);

    for (const name of ["pth-field", "pth-field-header", "pth-label",
                        "pth-str", "pth-str-message", "pth-int",
                        "pth-int-message", "pth-int-value",
                        "pth-choice-input"]) {
        assert.ok(present.has(name), `missing class ${name}`);
    }
});


test("password and textarea are native inputs with no obsolete wrapper", () => {
    const { form } = mount([
        { name: "secret", node: { kind: "str", options: { password: true } } },
        { name: "area", node: { kind: "str", options: { rows: 4 } } },
    ]);

    const secret = form.fields[0].widget.widget.input;
    const area = form.fields[1].widget.widget.input;

    assert.equal(secret.tagName, "INPUT");
    assert.equal(secret.type, "password");
    assert.equal(area.tagName, "TEXTAREA");
});


test("the integer widget is a filtered text input wrapped in a custom stepper", () => {
    const { form } = mount([{ name: "count", node: { kind: "int" } }]);
    const widget = form.fields[0].widget.widget;

    assert.equal(widget.input.tagName, "INPUT");
    assert.equal(widget.input.type, "text");
    assert.equal(widget.input.getAttribute("inputmode"), "numeric");

    const wrapper = widget.el.children[0];
    const controls = wrapper.children[1];
    const buttons = controls.children;

    assert.equal(wrapper.className, "pth-number");
    assert.equal(controls.className, "pth-number-controls");
    assert.equal(buttons.length, 2);
    assert.deepEqual(buttons.map((b) => b.className),
                     ["pth-number-btn", "pth-number-btn"]);
    assert.deepEqual(buttons.map((b) => b.type), ["button", "button"]);
    assert.deepEqual(buttons.map((b) => b.getAttribute("aria-label")),
                     ["Increase", "Decrease"]);
});


test("the stepper buttons step the value and respect min and max", () => {
    const { form } = mount([{
        name: "count",
        node: { kind: "int", options: { min: 0, max: 6, step: 2 } },
    }]);

    const widget = form.fields[0].widget.widget;
    const [up, down] = widget.el.children[0].children[1].children;

    up.dispatch("click");
    assert.equal(widget.value(), 2);

    up.dispatch("click");
    up.dispatch("click");
    up.dispatch("click");
    assert.equal(widget.value(), 6);

    down.dispatch("click");
    assert.equal(widget.value(), 4);

    for (let i = 0; i < 5; i += 1) {
        down.dispatch("click");
    }
    assert.equal(widget.value(), 0);
});


test("stepping notifies subscribers and shows the message once touched", () => {
    const { form } = mount([{
        name: "count",
        node: { kind: "int", options: { multipleOf: 3, step: 1 } },
    }]);

    const widget = form.fields[0].widget.widget;
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    // A freshly mounted field shows nothing, even though empty.
    assert.equal(widget.message.hidden, true);

    const up = widget.el.children[0].children[1].children[0];
    up.dispatch("click");

    // Stepped to 1 by the step of 1, which is not a multiple of 3.
    assert.equal(changes, 1);
    assert.equal(widget.value(), 1);
    assert.equal(widget.hasError(), true);
    assert.equal(widget.input.getAttribute("aria-invalid"), "true");
    assert.equal(widget.message.hidden, false);
});


test("the integer input keeps the raw text and never rewrites it", () => {
    const { form } = mount([{ name: "count", node: { kind: "int" } }]);
    const widget = form.fields[0].widget.widget;

    const typeRaw = (raw) => {
        widget.input.value = raw;
        widget.input.dispatch("input");
        return widget.input.value;
    };

    // Malformed text is preserved exactly and makes the widget invalid.
    assert.equal(typeRaw("1.5"), "1.5");
    assert.equal(widget.value(), null);
    assert.equal(widget.hasError(), true);

    assert.equal(typeRaw("1-2"), "1-2");
    assert.equal(widget.value(), null);
    assert.equal(widget.hasError(), true);

    assert.equal(typeRaw("abc"), "abc");
    assert.equal(widget.value(), null);
    assert.equal(widget.hasError(), true);

    // Well-formed text parses to the exact integer.
    assert.equal(typeRaw("12"), "12");
    assert.equal(widget.value(), 12);
    assert.equal(widget.hasError(), false);

    assert.equal(typeRaw("-12"), "-12");
    assert.equal(widget.value(), -12);

    // Empty is not invalid, just incomplete.
    assert.equal(typeRaw(""), "");
    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
    assert.equal(widget.hasError(), false);
});


test("choice and group containers keep their stylesheet classes", () => {
    const { host } = mount([
        { name: "ref", node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
            ],
        } },
        { name: "addr", node: {
            kind: "object",
            fields: [{ name: "city", node: { kind: "str" } }],
        } },
    ]);

    const present = classes(host);

    for (const name of ["pth-choice", "pth-mode-navigation", "pth-mode-previous",
                        "pth-mode-position", "pth-mode-next", "pth-mode-content",
                        "pth-group"]) {
        assert.ok(present.has(name), `missing class ${name}`);
    }
});


test("list controls expose the classes the redesigned stylesheet targets", () => {
    const { form, host } = mount([
        { name: "tags", node: { kind: "list", item: { kind: "str" } } },
    ]);

    const list = form.fields[0].widget.widget;
    list.add();

    const present = classes(host);

    for (const name of ["pth-list", "pth-list-items", "pth-list-item",
                        "pth-list-item-content", "pth-list-add",
                        "pth-list-remove", "pth-list-message"]) {
        assert.ok(present.has(name), `missing class ${name}`);
    }

    assert.equal(list.addButton.className, "pth-list-add");
    assert.equal(list.items[0].removeButton.className, "pth-list-remove");
});


test("the remove button is an icon with an accessible name, not text", () => {
    const { form } = mount([{
        name: "guests",
        node: { kind: "list", removeLabel: "Remove", item: { kind: "str" } },
    }]);

    const list = form.fields[0].widget.widget;
    list.add();

    const remove = list.items[0].removeButton;

    // The glyph is an empty span the stylesheet masks with icons/trash.svg, so
    // the runtime mints no SVG of its own and the icon still takes the button's
    // colour. To a screen reader it does not exist: the name is the button's.
    const icon = remove.children.find(
        (child) => child.className === "pth-list-remove-icon");

    assert.ok(icon, "the remove button should carry the masked icon span");
    assert.equal(icon.tagName, "SPAN");
    assert.equal(icon.getAttribute("aria-hidden"), "true");
    assert.equal(icon.textContent, "");
    assert.equal(remove.textContent, "");
    assert.equal(remove.getAttribute("aria-label"), "Remove 1");
});


test("the runtime builds no svg of its own", () => {
    // Every icon the library draws is a file under static/icons/, referenced
    // from the stylesheet. Nothing constructs one at runtime.
    const { form } = mount([
        { name: "guests", node: { kind: "list", item: { kind: "str" } } },
        { name: "doc", node: { kind: "file" } },
    ]);

    form.fields[0].widget.widget.add();

    for (const field of form.fields) {
        const host = document.createElement("div");
        host.append(field.widget.el);

        for (const node of walk(host)) {
            assert.notEqual(node.tagName, "SVG");
        }
    }
});


test("the add button keeps its visible text label", () => {
    const { form } = mount([{
        name: "guests",
        node: { kind: "list", addLabel: "Add guest", item: { kind: "str" } },
    }]);

    assert.equal(form.fields[0].widget.widget.addButton.textContent, "Add guest");
});


test("the optional toggle is a native checkbox with the styling class", () => {
    const { form } = mount([
        { name: "nickname", optional: true, node: { kind: "str" } },
    ]);

    const toggle = form.fields[0].widget.toggle;

    assert.equal(toggle.tagName, "INPUT");
    assert.equal(toggle.type, "checkbox");
    assert.equal(toggle.className, "pth-toggle");
});


test("no widget introduces a positive tabindex", () => {
    const { host } = mount([
        { name: "a", node: { kind: "str" } },
        { name: "b", optional: true, node: { kind: "int" } },
        { name: "c", node: { kind: "list", item: { kind: "str" } } },
    ]);

    for (const node of walk(host)) {
        assert.equal(node.hasAttribute("tabindex"), false);
    }
});
