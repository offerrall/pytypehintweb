import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type, walk } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { ChoiceWidget } from "../../src/pytypehintweb/static/fields.js";
import { StrWidget, IntWidget } from "../../src/pytypehintweb/static/inputs.js";


function build(fields, options = {}) {
    const form = compileForm({ v: 1, kind: "form", name: "modes", fields },
                             { prefix: "m", ...options });
    const host = document.createElement("div");

    for (const field of form.fields) {
        host.append(field.widget.el);
    }

    return { form, host };
}


function twoBranch(extra = {}) {
    return {
        kind: "choice",
        ...extra,
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    };
}


function choiceOf(form, name = "value") {
    return form.fields.find((f) => f.name === name).widget.widget;
}


test("a union renders no branch select", () => {
    const { host } = build([{ name: "value", node: twoBranch() }]);

    assert.equal(walk(host).some((node) => node.tagName === "SELECT"), false);
});


test("previous and next are native buttons", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    assert.equal(choice.previous.tagName, "BUTTON");
    assert.equal(choice.previous.type, "button");
    assert.equal(choice.next.tagName, "BUTTON");
    assert.equal(choice.next.type, "button");
});


test("the position begins at Mode 1 of N", () => {
    const { form } = build([{
        name: "value",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "plain", node: { kind: "str" } },
                { value: "int", mode: "plain", node: { kind: "int" } },
                { value: "list", mode: "plain",
                  node: { kind: "list", item: { kind: "str" } } },
            ],
        },
    }]);

    assert.equal(choiceOf(form).position.textContent, "Mode 1 of 3");
});


test("previous is disabled on the first branch, next on the last", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    assert.equal(choice.previous.disabled, true);
    assert.equal(choice.next.disabled, false);

    choice.next.dispatch("click");

    assert.equal(choice.previous.disabled, false);
    assert.equal(choice.next.disabled, true);
});


test("navigation does not wrap past either end", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    choice.previous.dispatch("click");
    assert.equal(choice.activeIndex(), 0);

    choice.next.dispatch("click");
    choice.next.dispatch("click");
    assert.equal(choice.activeIndex(), 1);
});


test("next and previous change the branch and the position", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    choice.next.dispatch("click");
    assert.equal(choice.activeIndex(), 1);
    assert.equal(choice.position.textContent, "Mode 2 of 2");

    choice.previous.dispatch("click");
    assert.equal(choice.activeIndex(), 0);
    assert.equal(choice.position.textContent, "Mode 1 of 2");
});


test("one navigation emits exactly one change event", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    let changes = 0;
    choice.onChange(() => { changes += 1; });

    choice.next.dispatch("click");

    assert.equal(changes, 1);
});


test("branch values are preserved across navigation", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    type(choice.active(), "hello");

    choice.next.dispatch("click");
    type(choice.active(), "42");

    choice.previous.dispatch("click");
    assert.equal(choice.value(), "hello");

    choice.next.dispatch("click");
    assert.equal(choice.value(), 42);
});


test("a default opens the navigator on the matching branch position", () => {
    const { form } = build([{
        name: "value",
        hasDefault: true,
        default: { branch: 1, value: 7 },
        node: twoBranch(),
    }]);

    const choice = choiceOf(form);

    assert.equal(choice.activeIndex(), 1);
    assert.equal(choice.position.textContent, "Mode 2 of 2");
    assert.equal(choice.value(), 7);
});


test("plain transport is unchanged", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    type(choice.active(), "text");
    assert.deepEqual(form.read(), { value: "text" });
});


test("wrapped transport is unchanged", () => {
    const { form } = build([{
        name: "value",
        node: {
            kind: "choice",
            branches: [
                { value: "str", mode: "wrapped", node: { kind: "str" } },
                { value: "int", mode: "wrapped", node: { kind: "int" } },
            ],
        },
    }]);

    const choice = choiceOf(form);

    choice.next.dispatch("click");
    type(choice.active(), "9");

    assert.deepEqual(form.read(), { value: { $type: "int", $value: 9 } });
});


test("inline transport is unchanged", () => {
    const { form } = build([{
        name: "value",
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

    const choice = choiceOf(form);

    assert.deepEqual(form.read(), { value: { $type: "Shirt", size: "" } });
});


test("optional None stays outside the navigator", () => {
    const { form } = build([{
        name: "value",
        optional: true,
        node: twoBranch(),
    }]);

    const field = form.fields[0].widget;

    // The union has two modes; None is the field's optional toggle, not a mode.
    assert.equal(field.widget.branches.length, 2);
    assert.equal(field.widget.position.textContent, "Mode 1 of 2");
    assert.notEqual(field.toggle, null);

    field.toggle.checked = false;
    field.toggle.dispatch("change");

    assert.deepEqual(form.read(), { value: null });
});


test("nested unions have independent navigators", () => {
    const { form } = build([{
        name: "rows",
        node: {
            kind: "list",
            item: {
                kind: "choice",
                branches: [
                    { value: "str", mode: "wrapped", node: { kind: "str" } },
                    { value: "int", mode: "wrapped", node: { kind: "int" } },
                ],
            },
        },
    }]);

    const list = form.fields[0].widget.widget;
    list.add();
    list.add();

    const first = list.widgets()[0];
    const second = list.widgets()[1];

    first.next.dispatch("click");

    assert.equal(first.activeIndex(), 1);
    assert.equal(second.activeIndex(), 0);
    assert.equal(first.position.textContent, "Mode 2 of 2");
    assert.equal(second.position.textContent, "Mode 1 of 2");
});


test("only the active branch is mounted; inactive ones are detached", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);
    const choice = choiceOf(form);

    assert.equal(choice.content.children.length, 1);
    assert.equal(choice.content.children[0], choice.active().el);

    // The inactive branch's element is not in the content tree.
    const inactive = choice.branches[1].widget.el;
    assert.equal(walk(choice.content).includes(inactive), false);
});


test("technical branch ids are never rendered as text", () => {
    const { host } = build([{
        name: "value",
        node: {
            kind: "choice",
            branches: [
                { value: "list[str]", mode: "wrapped",
                  node: { kind: "list", item: { kind: "str" } } },
                { value: "list[int]", mode: "wrapped",
                  node: { kind: "list", item: { kind: "int" } } },
            ],
        },
    }]);

    const texts = walk(host).map((node) => node.textContent);

    assert.equal(texts.includes("list[str]"), false);
    assert.equal(texts.includes("list[int]"), false);
});


test("custom mode labels are applied", () => {
    const { form } = build([{
        name: "value",
        node: twoBranch({
            previousLabel: "Modo anterior",
            nextLabel: "Modo siguiente",
            positionLabel: "Modo {current} de {total}",
        }),
    }]);

    const choice = choiceOf(form);

    assert.equal(choice.previous.getAttribute("aria-label"), "Modo anterior");
    assert.equal(choice.next.getAttribute("aria-label"), "Modo siguiente");
    assert.equal(choice.position.textContent, "Modo 1 de 2");

    choice.next.dispatch("click");
    assert.equal(choice.position.textContent, "Modo 2 de 2");
});


test("the position has a polite live region", () => {
    const { form } = build([{ name: "value", node: twoBranch() }]);

    assert.equal(choiceOf(form).position.getAttribute("aria-live"), "polite");
});


test("a directly constructed ChoiceWidget defaults its mode labels", () => {
    const widget = new ChoiceWidget([
        { value: "a", widget: new StrWidget() },
        { value: "b", widget: new IntWidget() },
    ]);

    assert.equal(widget.previous.getAttribute("aria-label"), "Previous mode");
    assert.equal(widget.next.getAttribute("aria-label"), "Next mode");
    assert.equal(widget.position.textContent, "Mode 1 of 2");
});


// --- focus stays reachable at the extremes ----------------------------------
//
// A disabled control cannot hold focus. When a move disables the button that was
// just activated (the extremes), focus must land on the still-enabled sibling
// rather than fall back to the body. The fake DOM has no focus(), so record it.
function trackFocus(choice) {
    const focused = [];
    for (const [name, button] of [["previous", choice.previous],
                                  ["next", choice.next]]) {
        button.focus = () => focused.push(name);
    }
    return focused;
}


function threeBranch() {
    return {
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
            { value: "flt", mode: "plain", node: { kind: "float" } },
        ],
    };
}


test("reaching the last branch moves focus off the disabled next button", () => {
    const { form } = build([{ name: "value", node: threeBranch() }]);
    const choice = choiceOf(form);
    const focused = trackFocus(choice);

    choice.next.dispatch("click");   // to the middle: next still enabled
    assert.equal(choice.next.disabled, false);
    assert.deepEqual(focused, []);

    choice.next.dispatch("click");   // to the last: next disables itself
    assert.equal(choice.next.disabled, true);
    assert.deepEqual(focused, ["previous"]);
});


test("reaching the first branch moves focus off the disabled previous button", () => {
    const { form } = build([{ name: "value", node: threeBranch() }]);
    const choice = choiceOf(form);

    choice.next.dispatch("click");
    choice.next.dispatch("click");   // now at the last branch

    const focused = trackFocus(choice);

    choice.previous.dispatch("click");  // to the middle: previous still enabled
    assert.deepEqual(focused, []);

    choice.previous.dispatch("click");  // to the first: previous disables itself
    assert.equal(choice.previous.disabled, true);
    assert.deepEqual(focused, ["next"]);
});
