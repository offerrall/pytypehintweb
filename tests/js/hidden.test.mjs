import "./dom.mjs";
import test from "node:test";
import assert from "node:assert/strict";
import { compileForm } from "./harness.mjs";
import { type } from "./dom.mjs";

const object = {
    kind: "object",
    fields: [
        { name: "token", hasDefault: true, default: "default", node: { kind: "str" } },
        { name: "name", hasDefault: true, default: "new", node: { kind: "str" } },
    ],
};

function nested(wrappers) {
    let spec = {
        node: object, initial: { token: "abc", name: "Demo" },
        read: { token: "abc", name: "Demo" }, path: "token", group: (widget) => widget,
    };
    for (const wrapper of wrappers) {
        const inner = spec;
        if (wrapper === "object") {
            spec = {
                node: { kind: "object", fields: [{ name: "child", node: inner.node }] },
                initial: { child: inner.initial }, read: { child: inner.read },
                path: `child.${inner.path}`,
                group: (widget) => inner.group(widget.children[0].widget.widget),
            };
        } else if (wrapper === "list") {
            spec = {
                node: { kind: "list", item: inner.node },
                initial: [inner.initial], read: [inner.read], path: `*.${inner.path}`,
                group: (widget) => inner.group(widget.widgets()[0]),
            };
        } else if (wrapper === "optional") {
            spec = {
                ...inner, node: { kind: "optional", node: inner.node },
                group: (widget) => inner.group(widget.widget),
            };
        } else if (wrapper === "choice") {
            spec = {
                ...inner,
                node: { kind: "choice", branches: [
                    { value: "object", mode: "wrapped", node: inner.node },
                    { value: "text", mode: "wrapped", node: { kind: "str" } },
                ] },
                initial: { branch: 0, value: inner.initial },
                read: { $type: "object", $value: inner.read },
                group: (widget) => inner.group(widget.branches[0].widget),
            };
        }
    }
    return spec;
}

for (const wrappers of [
    [], ["object", "object"], ["list"], ["list", "list"],
    ["optional", "list"], ["choice"], ["object", "choice", "optional", "list"],
]) {
    test(`prefill and hidden reach the same child through ${wrappers.join("/") || "object"}`, () => {
        const spec = nested(wrappers);
        const plan = { kind: "form", name: "edit", fields: [{
            name: "config", hasDefault: true, default: spec.initial, node: spec.node,
        }] };
        const form = compileForm(plan, { hidden: [`config.${spec.path}`] });
        const group = spec.group(form.fields[0].widget.widget);
        const [token, name] = group.children.map((child) => child.widget);
        assert.equal(form.fields[0].widget.el.hidden, false);
        assert.equal(token.el.hidden, true);
        assert.equal(token.value(), "abc");
        assert.equal(name.el.hidden, false);
        assert.equal(name.value(), "Demo");
        assert.equal(form.isReady(), true);
        assert.deepEqual(form.read(), { config: spec.read });
        assert.deepEqual(compileForm(plan).read(), form.read());
        assert.equal(spec.group(compileForm(plan).fields[0].widget.widget)
            .children[0].widget.el.hidden, false, "visibility belongs to each opening");
    });
}

test("wildcard visibility survives adding and removing list items", () => {
    const form = compileForm({ kind: "form", name: "edit", fields: [{
        name: "items", node: { kind: "list", item: object },
        hasDefault: true, default: [{ token: "abc", name: "Demo" }],
    }] }, { hidden: ["items.*.token"] });
    const list = form.fields[0].widget.widget;
    list.add();
    for (const group of list.widgets()) {
        assert.equal(group.children[0].widget.el.hidden, true);
        assert.equal(group.children[1].widget.el.hidden, false);
    }
    assert.deepEqual(form.read().items, [
        { token: "abc", name: "Demo" }, { token: "default", name: "new" },
    ]);
    list.remove(list.items[0]);
    assert.equal(list.widgets()[0].children[0].widget.el.hidden, true);
    assert.deepEqual(form.read().items, [{ token: "default", name: "new" }]);
});

test("hidden required fields still participate in readiness and validation", () => {
    const form = compileForm({ kind: "form", name: "edit", fields: [{
        name: "config", node: { kind: "object", fields: [{
            name: "token", node: { kind: "str", options: { minLength: 3 } },
        }] },
    }] }, { hidden: ["config.token"] });
    const token = form.fields[0].widget.widget.children[0].widget;
    assert.equal(token.el.hidden, true);
    assert.equal(form.isReady(), false);
    type(token.widget, "a");
    assert.equal(form.hasError(), true);
    type(token.widget, "abc");
    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), { config: { token: "abc" } });
});

test("root names, duplicate names and whole list items keep their values", () => {
    const plan = { kind: "form", name: "edit", fields: [{
        name: "items", node: { kind: "list", item: object },
        hasDefault: true, default: [{ token: "abc", name: "Demo" }],
    }] };
    const root = compileForm(plan, { hidden: ["items", "items"] });
    assert.equal(root.fields[0].widget.el.hidden, true);
    const items = compileForm(plan, { hidden: ["items.*"] });
    assert.equal(items.fields[0].widget.el.hidden, false);
    assert.equal(items.fields[0].widget.widget.widgets()[0].el.hidden, true);
    assert.equal(items.fields[0].widget.widget.items[0].row.hidden, true);
    assert.deepEqual(root.read(), items.read());
});

test("unknown and incomplete paths do not hide ancestors", () => {
    const form = compileForm({ kind: "form", name: "edit", fields: [{
        name: "config", node: object,
    }] }, { hidden: ["unknown", "token", "config.", "config..token", "config.nope"] });
    assert.equal(form.fields[0].widget.el.hidden, false);
    for (const child of form.fields[0].widget.widget.children) {
        assert.equal(child.widget.el.hidden, false);
    }
});

test("hidden options reject invalid types", () => {
    for (const hidden of [null, "config", {}, [1]]) {
        assert.throws(() => compileForm({ kind: "form", name: "edit", fields: [] },
            { hidden }), /hidden must be an array of strings/);
    }
});

test("visibility holds when optional fields toggle and union branches change", () => {
    const form = compileForm({ kind: "form", name: "edit", fields: [{
        name: "config", optional: true, enabled: false,
        node: { kind: "choice", branches: [
            { value: "a", mode: "wrapped", node: object },
            { value: "b", mode: "wrapped", node: object },
        ] },
    }] }, { hidden: ["config.token"] });
    const field = form.fields[0].widget;
    assert.deepEqual(form.read(), { config: null });
    field.setEnabled(true);
    const choice = field.widget;
    assert.equal(choice.active().children[0].widget.el.hidden, true);
    choice.next.dispatch("click");
    assert.equal(choice.activeIndex(), 1);
    assert.equal(choice.active().children[0].widget.el.hidden, true);
    type(choice.active().children[1].widget.widget, "changed");
    field.setEnabled(false);
    field.setEnabled(true);
    assert.equal(choice.active().children[0].widget.el.hidden, true);
    assert.deepEqual(form.read(), {
        config: { $type: "b", $value: { token: "default", name: "changed" } },
    });
});
