import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { compileForm, checkPlan } from "./harness.mjs";


// A file node composes like any other. These drive the four shapes that used to
// be refused by the Python adapter — a list of optionals, a list of choices, a
// nested list and a list of groups — entirely through the public API, to show
// the recursion needs nothing special for them.


function mount(field) {
    return compileForm({ v: 1, kind: "form", name: "nest", fields: [field] },
                       { prefix: "nest" });
}


const FILE = (options = {}) => ({ kind: "file", options });


// Simulate the browser handing files to a file input.
function choose(widget, ...names) {
    widget.input.files = names.map((name) => ({ name }));
    widget.input.dispatch("change");
}


// A group exposes its children as { name, widget }; the widget is the Field
// wrapping the control, so one more hop reaches the control itself.
function childOf(group, name) {
    return group.children.find((child) => child.name === name).widget.widget;
}


// A list row is removed the way a user removes it.
function removeRow(list, index) {
    list.items[index].removeButton.dispatch("click");
}


// A choice moves branch through its own navigation buttons.
function nextBranch(choice) {
    choice.next.dispatch("click");
}


// --- list[File | None] ------------------------------------------------------

const OPTIONAL_ITEMS = {
    name: "docs",
    node: { kind: "list", item: { kind: "optional", node: FILE() } },
};


test("a list of optional files adds rows that read null while off", () => {
    const form = mount(OPTIONAL_ITEMS);
    const list = form.fields[0].widget.widget;

    list.add();
    list.add();

    assert.deepEqual(form.read(), { docs: [null, null] });
});


test("each row of a list of optional files toggles on its own", () => {
    const form = mount(OPTIONAL_ITEMS);
    const list = form.fields[0].widget.widget;

    list.add();
    list.add();

    const [first, second] = list.widgets();

    first.setEnabled(true);
    first.widget.setValue("stored/one.pdf");

    assert.deepEqual(form.read(), { docs: ["stored/one.pdf", null] });

    second.setEnabled(true);
    choose(second.widget, "picked.pdf");

    const read = form.read();

    assert.equal(read.docs[0], "stored/one.pdf");
    assert.notEqual(read.docs[1], null);
    assert.equal(form.uploads().length, 1);            // only the local pick
    assert.equal(form.uploads()[0].file.name, "picked.pdf");
});


test("a list of optional files takes a default with a hole in it", () => {
    const form = mount({ ...OPTIONAL_ITEMS,
                         hasDefault: true,
                         default: ["stored/one.pdf", null] });

    assert.deepEqual(form.read(), { docs: ["stored/one.pdf", null] });
    assert.deepEqual(form.uploads(), []);
    assert.equal(form.fields[0].widget.widget.widgets().length, 2);
});


test("removing a row of a list of optional files shortens the read", () => {
    const form = mount({ ...OPTIONAL_ITEMS,
                         hasDefault: true,
                         default: ["stored/one.pdf", "stored/two.pdf"] });
    const list = form.fields[0].widget.widget;

    removeRow(list, 0);

    assert.deepEqual(form.read(), { docs: ["stored/two.pdf"] });
});


// --- list[File | int] -------------------------------------------------------

const UNION_ITEMS = {
    name: "mixed",
    node: { kind: "list", item: { kind: "choice", branches: [
        { value: "str", mode: "plain", node: FILE({ extensions: [".pdf"] }) },
        { value: "int", mode: "plain", node: { kind: "int" } },
    ] } },
};


test("a list of file-or-int rows carries a mixed default", () => {
    const form = mount({ ...UNION_ITEMS,
                         hasDefault: true,
                         default: [{ branch: 0, value: "stored/one.pdf" },
                                   { branch: 1, value: 7 }] });

    assert.deepEqual(form.read(), { mixed: ["stored/one.pdf", 7] });
    assert.deepEqual(form.uploads(), []);
});


test("a row can switch branch and the transport follows", () => {
    const form = mount({ ...UNION_ITEMS,
                         hasDefault: true,
                         default: [{ branch: 0, value: "stored/one.pdf" }] });
    const row = form.fields[0].widget.widget.widgets()[0];

    assert.equal(row.activeIndex(), 0);

    nextBranch(row);
    row.active().setValue(42);

    assert.deepEqual(form.read(), { mixed: [42] });
    assert.deepEqual(form.uploads(), []);              // the int branch uploads nothing
});


test("only the file branch of a mixed list reports an upload", () => {
    const form = mount({ ...UNION_ITEMS,
                         hasDefault: true,
                         default: [{ branch: 1, value: 1 },
                                   { branch: 0, value: "stored/one.pdf" }] });
    const [intRow, fileRow] = form.fields[0].widget.widget.widgets();

    assert.deepEqual(form.uploads(), []);

    choose(fileRow.active(), "picked.pdf");

    assert.equal(form.uploads().length, 1);
    assert.equal(intRow.activeIndex(), 1);
});


// --- list[list[File]] -------------------------------------------------------

const NESTED = {
    name: "groups",
    node: { kind: "list", item: { kind: "list", item: FILE() } },
};


test("a nested list keeps both levels", () => {
    const form = mount({ ...NESTED,
                         hasDefault: true,
                         default: [["a.pdf"], ["b.pdf", "c.pdf"]] });

    assert.deepEqual(form.read(), { groups: [["a.pdf"], ["b.pdf", "c.pdf"]] });
    assert.deepEqual(form.uploads(), []);
});


test("an empty outer list and an empty inner list are both fine", () => {
    assert.deepEqual(mount({ ...NESTED, hasDefault: true, default: [] }).read(),
                     { groups: [] });
    assert.deepEqual(mount({ ...NESTED, hasDefault: true, default: [[]] }).read(),
                     { groups: [[]] });
});


test("a pick two levels down is found as an upload", () => {
    const form = mount({ ...NESTED, hasDefault: true, default: [["a.pdf"]] });
    const inner = form.fields[0].widget.widget.widgets()[0];

    inner.add();
    choose(inner.widgets()[1], "deep.pdf");

    assert.equal(form.uploads().length, 1);
    assert.equal(form.uploads()[0].file.name, "deep.pdf");
});


// --- list[Dataclass with a file] --------------------------------------------

const ROWS = {
    name: "items",
    node: { kind: "list", item: { kind: "object", fields: [
        { name: "title", node: { kind: "str" } },
        { name: "document", node: FILE() },
    ] } },
};


test("a list of groups carries a file per row", () => {
    const form = mount({ ...ROWS,
                         hasDefault: true,
                         default: [{ title: "one", document: "stored/one.pdf" },
                                   { title: "two", document: "stored/two.pdf" }] });

    assert.deepEqual(form.read(), {
        items: [{ title: "one", document: "stored/one.pdf" },
                { title: "two", document: "stored/two.pdf" }],
    });
    assert.deepEqual(form.uploads(), []);
});


test("a pick inside one row of a list of groups is the only upload", () => {
    const form = mount({ ...ROWS,
                         hasDefault: true,
                         default: [{ title: "one", document: "stored/one.pdf" },
                                   { title: "two", document: "stored/two.pdf" }] });
    const second = form.fields[0].widget.widget.widgets()[1];

    choose(childOf(second, "document"), "picked.pdf");

    assert.equal(form.uploads().length, 1);
    assert.equal(form.read().items[0].document, "stored/one.pdf");
    assert.notEqual(form.read().items[1].document, "stored/two.pdf");
});


// --- structural validation --------------------------------------------------

function rejects(field, fragment) {
    assert.throws(
        () => checkPlan({ v: 1, kind: "form", name: "nest", fields: [field] }),
        (error) => {
            assert.ok(error instanceof TypeError);
            assert.ok(error.message.includes(fragment),
                      `expected ${JSON.stringify(error.message)} to mention `
                      + JSON.stringify(fragment));
            return true;
        });
}


test("a bad file default deep inside a list is reported with its full path", () => {
    rejects({ ...NESTED, hasDefault: true, default: [["a.pdf"], ["b.pdf", ""]] },
            "plan.fields[0].default[1][1]: expected a non-empty file reference");

    rejects({ ...ROWS, hasDefault: true,
              default: [{ title: "one", document: 7 }] },
            "plan.fields[0].default[0].document: expected a string file reference");

    rejects({ ...OPTIONAL_ITEMS, hasDefault: true, default: ["a.pdf", 7] },
            "plan.fields[0].default[1]: expected a string file reference");
});


test("an extension filter applies at any depth", () => {
    const pdfOnly = {
        name: "docs",
        node: { kind: "list", item: { kind: "list",
                                      item: FILE({ extensions: [".pdf"] }) } },
        hasDefault: true,
        default: [["fine.pdf"], ["wrong.txt"]],
    };

    rejects(pdfOnly, "plan.fields[0].default[1][0]: is not an accepted file type");
});


// --- equivalence ------------------------------------------------------------

test("a deep default equals the same values applied afterwards", () => {
    // The recursion applies a default through each widget's own public API, so
    // there is nothing a default can reach that a host could not.
    const observe = (form) => ({
        read: form.read(),
        ready: form.isReady(),
        error: form.hasError(),
        uploads: form.uploads(),
    });

    const withDefault = mount({ ...ROWS,
                               hasDefault: true,
                               default: [{ title: "one",
                                           document: "stored/one.pdf" }] });

    const applied = mount(ROWS);
    const list = applied.fields[0].widget.widget;
    list.add();
    childOf(list.widgets()[0], "title").setValue("one");
    childOf(list.widgets()[0], "document").setValue("stored/one.pdf");

    assert.deepEqual(observe(withDefault), observe(applied));
});
