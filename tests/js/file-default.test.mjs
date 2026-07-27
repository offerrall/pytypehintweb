import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { texts } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { FileWidget } from "../../src/pytypehintweb/static/inputs.js";


// A file default is an existing reference the host declares. It reaches the
// widget through its public setValue(), so the compiled state is the state a
// host would get by calling setValue() itself: a current file, no local File,
// nothing to upload.


function mount(fields) {
    return compileForm({ v: 1, kind: "form", name: "files", fields },
                       { prefix: "fd" });
}


function single(name, options = {}, extra = {}) {
    return { name, node: { kind: "file", options }, ...extra };
}


// Simulate the browser handing a file to the input.
function choose(widget, ...names) {
    widget.input.files = names.map((file) => ({ name: file }));
    widget.input.dispatch("change");
}


// --- single file ------------------------------------------------------------

test("a single file default reaches the widget as its current reference", () => {
    const form = mount([single("doc", { extensions: [".pdf"] },
                               { hasDefault: true, default: "stored/report.pdf" })]);
    const widget = form.fields[0].widget.widget;

    assert.equal(widget.value(), "stored/report.pdf");
    assert.equal(widget.file(), null);
    assert.deepEqual(widget.files(), []);
});


test("a defaulted file field is ready and carries nothing to upload", () => {
    const form = mount([single("doc", {}, { hasDefault: true,
                                            default: "stored/report.pdf" })]);
    const widget = form.fields[0].widget.widget;

    assert.equal(form.isReady(), true);
    assert.equal(form.hasError(), false);
    assert.equal(widget.isEmpty(), false);
    assert.deepEqual(form.uploads(), []);
    assert.deepEqual(form.read(), { doc: "stored/report.pdf" });
});


test("a default is not a local selection", () => {
    // The distinction is the widget's state, never the shape of the string: a
    // host must be able to tell "already stored" from "just picked" without
    // parsing the reference.
    const form = mount([single("doc", {}, { hasDefault: true,
                                            default: "stored/report.pdf" })]);
    const widget = form.fields[0].widget.widget;

    assert.deepEqual(widget.uploads(), []);

    choose(widget, "new.pdf");

    const pending = widget.uploads();

    assert.equal(pending.length, 1);
    assert.equal(pending[0].file.name, "new.pdf");
    assert.equal(pending[0].reference, widget.value());
    assert.notEqual(widget.value(), "stored/report.pdf");
    assert.equal(widget.files().length, 1);
});


test("a defaulted file can be replaced and then restored", () => {
    const form = mount([single("doc", {}, { hasDefault: true,
                                            default: "stored/report.pdf" })]);
    const widget = form.fields[0].widget.widget;

    choose(widget, "new.pdf");
    assert.notEqual(widget.value(), "stored/report.pdf");

    widget.setValue("stored/report.pdf");

    assert.equal(widget.value(), "stored/report.pdf");
    assert.deepEqual(widget.files(), []);
    assert.deepEqual(widget.uploads(), []);
});


test("clearing a defaulted file empties it", () => {
    const form = mount([single("doc", {}, { hasDefault: true,
                                            default: "stored/report.pdf" })]);
    const widget = form.fields[0].widget.widget;

    widget.setValue(null);

    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
    assert.deepEqual(widget.files(), []);
});


test("recompiling the same plan restores the default", () => {
    const field = single("doc", {}, { hasDefault: true,
                                      default: "stored/report.pdf" });

    const first = mount([field]).fields[0].widget.widget;
    choose(first, "new.pdf");
    assert.notEqual(first.value(), "stored/report.pdf");

    const second = mount([field]).fields[0].widget.widget;

    assert.equal(second.value(), "stored/report.pdf");
});


// --- multiple files ---------------------------------------------------------

const TWO = ["stored/one.pdf", "stored/two.pdf"];


test("a multiple file default keeps its references in order", () => {
    const form = mount([single("docs", { multiple: true },
                               { hasDefault: true, default: TWO })]);
    const widget = form.fields[0].widget.widget;

    assert.deepEqual(widget.value(), TWO);
    assert.deepEqual(form.read(), { docs: TWO });
    assert.deepEqual(widget.files(), []);
    assert.equal(widget.file(), null);
    assert.deepEqual(form.uploads(), []);
});


test("a multiple file value is a copy, not the widget's own array", () => {
    const form = mount([single("docs", { multiple: true },
                               { hasDefault: true, default: TWO })]);
    const widget = form.fields[0].widget.widget;

    const value = widget.value();
    value.push("mutated");

    assert.deepEqual(widget.value(), TWO);
});


test("a multiple file default satisfies its minimum", () => {
    const form = mount([single("docs", { multiple: true, minFiles: 2 },
                               { hasDefault: true, default: TWO })]);

    assert.equal(form.isReady(), true);
    assert.equal(form.hasError(), false);
});


test("choosing files replaces the whole defaulted selection", () => {
    const form = mount([single("docs", { multiple: true },
                               { hasDefault: true, default: TWO })]);
    const widget = form.fields[0].widget.widget;

    choose(widget, "a.pdf", "b.pdf");

    const value = widget.value();

    assert.equal(value.length, 2);
    assert.equal(value.some((reference) => TWO.includes(reference)), false);
    assert.equal(widget.files().length, 2);
    assert.equal(widget.uploads().length, 2);
});


// --- optional ---------------------------------------------------------------

test("an optional file with no default starts empty", () => {
    const form = mount([single("doc", {}, { optional: true, enabled: true })]);

    assert.equal(form.fields[0].widget.widget.value(), null);
    assert.deepEqual(form.read(), { doc: null });
});


test("an optional file with a null default is off and reads null", () => {
    const form = mount([single("doc", {}, {
        optional: true, enabled: false, hasDefault: true, default: null,
    })]);

    assert.equal(form.fields[0].widget.enabled(), false);
    assert.deepEqual(form.read(), { doc: null });
    assert.equal(form.isReady(), true);
});


test("an optional file with a reference is on and carries it", () => {
    const form = mount([single("doc", {}, {
        optional: true, enabled: true, hasDefault: true,
        default: "stored/report.pdf",
    })]);

    const field = form.fields[0].widget;

    assert.equal(field.enabled(), true);
    assert.equal(field.widget.value(), "stored/report.pdf");
    assert.deepEqual(form.read(), { doc: "stored/report.pdf" });

    field.setEnabled(false);

    assert.deepEqual(form.read(), { doc: null });
    assert.equal(field.widget.value(), "stored/report.pdf");   // kept inside

    field.setEnabled(true);

    assert.deepEqual(form.read(), { doc: "stored/report.pdf" });
});


// --- nesting ----------------------------------------------------------------

test("a file default inside an object reaches the nested widget", () => {
    const form = mount([{
        name: "profile",
        hasDefault: true,
        default: { name: "Ada", avatar: "stored/ada.jpg" },
        node: {
            kind: "object",
            fields: [
                { name: "name", node: { kind: "str" } },
                { name: "avatar", node: {
                    kind: "file", options: { extensions: [".jpg"] } } },
            ],
        },
    }]);

    assert.deepEqual(form.read(),
                     { profile: { name: "Ada", avatar: "stored/ada.jpg" } });
    assert.deepEqual(form.uploads(), []);
});


test("a multiple file default inside an object survives too", () => {
    const form = mount([{
        name: "album",
        hasDefault: true,
        default: { photos: TWO },
        node: {
            kind: "object",
            fields: [{ name: "photos", node: {
                kind: "file", options: { multiple: true, extensions: [".pdf"] } } }],
        },
    }]);

    assert.deepEqual(form.read(), { album: { photos: TWO } });
});


test("a file default inside a union branch reaches its widget", () => {
    const form = mount([{
        name: "attachment",
        hasDefault: true,
        default: { branch: 1, value: "stored/report.pdf" },
        node: {
            kind: "choice",
            branches: [
                { value: "int", mode: "plain", node: { kind: "int" } },
                { value: "str", mode: "plain", node: {
                    kind: "file", options: { extensions: [".pdf"] } } },
            ],
        },
    }]);

    assert.deepEqual(form.read(), { attachment: "stored/report.pdf" });
    assert.deepEqual(form.uploads(), []);
});


// --- equivalence ------------------------------------------------------------

// Everything a host can see through the public API, plus what the field shows.
function observe(field) {
    const widget = field.widget;

    return {
        value: widget.value(),
        file: widget.file(),
        files: widget.files(),
        isEmpty: widget.isEmpty(),
        hasError: widget.hasError(),
        isReady: widget.isReady(),
        error: widget.error(),
        uploads: widget.uploads(),
        enabled: field.enabled(),
        shown: texts(widget.el, "pth-file-current-label"),
    };
}


test("compiling with a default equals compiling then calling setValue", () => {
    // The whole point of routing the default through setValue(): there is one
    // implementation, so the two paths cannot drift.
    for (const [options, reference, extra] of [
        [{ extensions: [".pdf"] }, "stored/report.pdf", {}],
        [{ multiple: true, extensions: [".pdf"] }, TWO, {}],
        [{ multiple: true, minFiles: 1 }, ["stored/one.pdf"], {}],
        [{ extensions: [".pdf"] }, "stored/report.pdf",
         { optional: true, enabled: true }],
    ]) {
        const withDefault = mount([single("doc", options, {
            ...extra, hasDefault: true, default: reference,
        })]).fields[0].widget;

        const applied = mount([single("doc", options, extra)]).fields[0].widget;
        applied.widget.setValue(reference);

        assert.deepEqual(observe(withDefault), observe(applied));
    }
});


test("the current file is on screen either way", () => {
    // The equivalence covers what the user sees, not only what read() returns.
    const shown = mount([single("doc", {}, {
        hasDefault: true, default: "stored/report.pdf",
    })]).fields[0].widget.widget;

    assert.deepEqual(texts(shown.el, "pth-file-current-label"),
                     ["Current file: stored/report.pdf"]);
});


test("a default applies through the same public API a host would use", () => {
    // Constructed directly, with no plan in sight, the widget lands in the same
    // observable state.
    const direct = new FileWidget({ extensions: [".pdf"] });
    direct.setValue("stored/report.pdf");

    const compiled = mount([single("doc", { extensions: [".pdf"] },
                                   { hasDefault: true,
                                     default: "stored/report.pdf" })])
        .fields[0].widget.widget;

    assert.equal(direct.value(), compiled.value());
    assert.equal(direct.isEmpty(), compiled.isEmpty());
    assert.deepEqual(direct.uploads(), compiled.uploads());
});
