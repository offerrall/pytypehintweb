import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { checkPlan, compileForm } from "./harness.mjs";
import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { FileWidget, asciiSlug } from "../../src/pytypehintweb/static/inputs.js";


// A reference is an optional ASCII slug of the file's name, then the hash, then
// the matched extension. Anchored at the start so a leading anything-else fails.
const HASH = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const REFERENCE = new RegExp(`^(?:[a-z0-9]+(?:-[a-z0-9]+)*-)?${HASH}`, "i");
const BARE_REFERENCE = new RegExp(`^${HASH}`, "i");


function plan(fields) {
    return { v: 1, kind: "form", name: "example", fields };
}


function rejects(input, fragment) {
    assert.throws(() => checkPlan(input), (error) => {
        assert.ok(error instanceof TypeError, `expected a TypeError, got ${error}`);
        assert.ok(error.message.includes(fragment),
                  `expected ${JSON.stringify(error.message)} to mention `
                  + JSON.stringify(fragment));
        return true;
    });
}


// Simulate the browser handing files to the input: set its files and fire the
// native change event the widget listens for. Names alone are enough here.
function choose(widget, ...names) {
    widget.input.files = names.map((name) => ({ name }));
    widget.input.dispatch("change");
}


// The + button appends through _ingest(files, true); the throwaway picker it
// opens is not reachable through the abstract DOM, so drive that path directly.
function addMore(widget, ...names) {
    widget._ingest(names.map((name) => ({ name })), true);
}


// --- node normalization -----------------------------------------------------

test("a single file node normalizes its full option set", () => {
    const options = {
        extensions: [], invalidMessage: "Not an accepted file type",
        multiple: false, minFiles: null, maxFiles: null,
        minSize: null, maxSize: null,
        minMessage: "Add at least {value} files",
        maxMessage: "Keep at most {value} files",
        minSizeMessage: "File is too small; minimum {value}",
        maxSizeMessage: "File is too large; maximum {value}",
        currentLabel: "Current file: {value}", currentRemoveLabel: "Remove current file",
        currentReplaceLabel: "Replace file", currentRestoreLabel: "Restore current file",
    };

    assert.deepEqual(normalizeNode({ kind: "file", options }),
                     { kind: "file", options });
});


test("a file node requires each of its options", () => {
    assert.throws(() => normalizeNode({ kind: "file", options: {} }),
                  /node\.options\.extensions: is required/);
});


test("a file node rejects a malformed extension", () => {
    rejects(plan([{ name: "a", node: {
        kind: "file", options: { extensions: [".PDF"] } } }]),
            "extensions[0]: expected a lowercase extension");
});


test("a file node rejects the old pending option name", () => {
    rejects(plan([{ name: "a", node: {
        kind: "file", options: { pendingMessage: "x" } } }]),
            "plan.fields[0].node.options.pendingMessage: unknown property");
});


test("file messages and labels are checked for their placeholders", () => {
    rejects(plan([{ name: "a", node: {
        kind: "file", options: { invalidMessage: "Bad {value}" } } }]),
            "must not contain placeholders");

    rejects(plan([{ name: "b", node: {
        kind: "file", options: { minMessage: "too few" } } }]),
            "must contain exactly one {value} placeholder");

    rejects(plan([{ name: "c", node: {
        kind: "file", options: { currentLabel: "Current file" } } }]),
            "must contain exactly one {value} placeholder");
});


test("file count bounds are validated and belong to multiple only", () => {
    rejects(plan([{ name: "a", node: {
        kind: "file", options: { multiple: true, minFiles: 3, maxFiles: 1 } } }]),
            "must not exceed maxFiles");

    rejects(plan([{ name: "b", node: {
        kind: "file", options: { multiple: false, minFiles: 1 } } }]),
            "minFiles and maxFiles require a multiple file node");
});


// --- a file default is an existing reference --------------------------------
//
// It is the same thing FileWidget.setValue() takes: a string the host declares,
// shown as the current file. The plan checks its shape; the widget applies it.

test("a single file field accepts a reference as its default", () => {
    const accepted = plan([{
        name: "a", hasDefault: true, default: "stored/report.pdf",
        node: { kind: "file", options: { extensions: [".pdf"] } },
    }]);

    assert.equal(checkPlan(accepted).fields[0].default, "stored/report.pdf");
});


test("a multiple file field accepts an array of references", () => {
    const accepted = plan([{
        name: "a", hasDefault: true,
        default: ["stored/one.pdf", "stored/two.pdf"],
        node: { kind: "file", options: { multiple: true, extensions: [".pdf"] } },
    }]);

    assert.deepEqual(checkPlan(accepted).fields[0].default,
                     ["stored/one.pdf", "stored/two.pdf"]);
});


test("an optional file accepts a null default", () => {
    const accepted = plan([{
        name: "a", optional: true, enabled: false, hasDefault: true,
        default: null, node: { kind: "file" },
    }]);

    assert.equal(checkPlan(accepted).fields[0].default, null);
});


test("a file default must match the arity of its node", () => {
    rejects(plan([{ name: "a", hasDefault: true, default: ["a.pdf"],
                    node: { kind: "file", options: { extensions: [".pdf"] } } }]),
            "plan.fields[0].default: expected a string file reference");

    rejects(plan([{ name: "b", hasDefault: true, default: "a.pdf",
                    node: { kind: "file",
                            options: { multiple: true, extensions: [".pdf"] } } }]),
            "plan.fields[0].default: expected an array of file references");
});


test("a file default must be a non-empty string", () => {
    rejects(plan([{ name: "a", hasDefault: true, default: 7,
                    node: { kind: "file" } }]),
            "plan.fields[0].default: expected a string file reference");

    rejects(plan([{ name: "b", hasDefault: true, default: "",
                    node: { kind: "file" } }]),
            "plan.fields[0].default: expected a non-empty file reference");

    rejects(plan([{ name: "c", hasDefault: true, default: ["a.pdf", ""],
                    node: { kind: "file",
                            options: { multiple: true, extensions: [".pdf"] } } }]),
            "plan.fields[0].default[1]: expected a non-empty file reference");
});


test("a file default is filtered by the declared extensions", () => {
    rejects(plan([{ name: "a", hasDefault: true, default: "note.txt",
                    node: { kind: "file", options: { extensions: [".pdf"] } } }]),
            "plan.fields[0].default: is not an accepted file type");

    rejects(plan([{ name: "b", hasDefault: true, default: ["a.pdf", "b.txt"],
                    node: { kind: "file",
                            options: { multiple: true, extensions: [".pdf"] } } }]),
            "plan.fields[0].default[1]: is not an accepted file type");
});


test("a node with no extensions accepts any reference as a default", () => {
    const accepted = plan([{ name: "a", hasDefault: true, default: "anything",
                             node: { kind: "file" } }]);

    assert.equal(checkPlan(accepted).fields[0].default, "anything");
});


test("a multiple file default obeys the file count bounds", () => {
    const bounded = { multiple: true, minFiles: 2, maxFiles: 3 };

    rejects(plan([{ name: "a", hasDefault: true, default: ["one.pdf"],
                    node: { kind: "file", options: bounded } }]),
            "plan.fields[0].default: expected at least 2 file references");

    rejects(plan([{
        name: "b", hasDefault: true,
        default: ["1.pdf", "2.pdf", "3.pdf", "4.pdf"],
        node: { kind: "file", options: bounded },
    }]), "plan.fields[0].default: expected at most 3 file references");
});


// --- single FileWidget: empty <-> chosen ------------------------------------

test("an empty single file field has no value and is not ready", () => {
    const widget = new FileWidget();

    assert.equal(widget.value(), null);
    assert.equal(widget.file(), null);
    assert.equal(widget.isEmpty(), true);
    assert.equal(widget.isReady(), false);
    assert.equal(widget.hasError(), false);
    assert.equal(widget.control(), widget.input);
    assert.equal(widget.input.type, "file");
    assert.equal(widget.input.multiple, undefined);   // no multiple attribute
});


test("choosing a file mints a reference locally and turns the field ready", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    choose(widget, "Report.PDF");

    assert.equal(changes, 1);
    assert.equal(widget.file().name, "Report.PDF");
    assert.match(widget.value(), REFERENCE);
    assert.ok(widget.value().endsWith(".pdf"));       // lowered, matched extension
    assert.equal(widget.isReady(), true);
});


test("choosing a new file mints a fresh reference", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    choose(widget, "first.pdf");
    const first = widget.value();
    choose(widget, "second.pdf");

    assert.notEqual(first, widget.value());
});


// --- the name that leads a reference ----------------------------------------

test("asciiSlug compresses a name to bare lowercase ASCII", () => {
    assert.equal(asciiSlug("Informe Añual"), "informe-anual");
    assert.equal(asciiSlug("Ficha_Técnica (v2)"), "ficha-tecnica-v");
    assert.equal(asciiSlug("Größe"), "grosse");
    assert.equal(asciiSlug("--a  b--"), "a-b");
});


test("asciiSlug keeps at most the first 15 characters", () => {
    assert.equal(asciiSlug("presupuesto general 2026"), "presupuesto-gen");
    assert.equal(asciiSlug("presupuesto general".slice(0, 12)), "presupuesto");
    assert.equal(asciiSlug("corto"), "corto");
});


test("asciiSlug keeps nothing from a name with no ASCII to keep", () => {
    assert.equal(asciiSlug("日本語"), "");
    assert.equal(asciiSlug("   "), "");
    assert.equal(asciiSlug(""), "");
});


test("the minted reference leads with the file's normalized name", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    choose(widget, "Informe Añual.PDF");

    assert.match(widget.value(), REFERENCE);
    assert.ok(widget.value().startsWith("informe-anual-"));
    assert.ok(widget.value().endsWith(".pdf"));
    assert.equal(widget.value().split(".").length, 2);   // the extension, once
});


test("a name longer than 15 characters is cut to its first 15", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    choose(widget, "presupuesto general 2026.pdf");

    assert.ok(widget.value().startsWith("presupuesto-gen-"));
});


test("a name that normalizes to nothing mints a bare hash", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    choose(widget, "日本語.pdf");

    assert.match(widget.value(), BARE_REFERENCE);
    assert.ok(widget.value().endsWith(".pdf"));
});


test("the name in a reference never repeats the extension", () => {
    const widget = new FileWidget();

    choose(widget, "archive.tar.gz");

    assert.ok(widget.value().startsWith("archive-tar-"));
    assert.ok(widget.value().endsWith(".gz"));
});


test("two picks of the same name still mint distinct references", () => {
    const widget = new FileWidget({ extensions: [".pdf"], multiple: true });

    choose(widget, "informe.pdf", "informe.pdf");

    const [first, second] = widget.value();

    assert.ok(first.startsWith("informe-"));
    assert.ok(second.startsWith("informe-"));
    assert.notEqual(first, second);
});


test("removing the file returns to empty", () => {
    const widget = new FileWidget();
    choose(widget, "a.pdf");
    choose(widget);                                   // no files selected

    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
});


test("a file whose extension is not accepted mints no reference and is invalid", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    choose(widget, "notes.txt");

    assert.equal(widget.value(), null);
    assert.equal(widget.file().name, "notes.txt");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.isReady(), false);
    assert.equal(widget.message.textContent, "Not an accepted file type");
    assert.equal(widget.input.getAttribute("aria-invalid"), "true");
});


test("with no declared extensions any file is accepted", () => {
    const widget = new FileWidget();

    choose(widget, "archive.tar.gz");
    assert.ok(widget.value().endsWith(".gz"));

    choose(widget, "README");
    assert.ok(!widget.value().includes("."));         // bare uuid
});


test("the accept attribute is generated from the extensions", () => {
    assert.equal(new FileWidget({ extensions: [".pdf", ".docx"] })
                 .input.getAttribute("accept"), ".pdf,.docx");
    assert.equal(new FileWidget().input.getAttribute("accept"), null);
});


// --- multiple FileWidget: list[File] ----------------------------------------

test("a multiple file field mints one distinct reference per file", () => {
    const widget = new FileWidget({ extensions: [".pdf"], multiple: true });

    assert.equal(widget.input.multiple, true);

    choose(widget, "a.pdf", "b.PDF", "c.pdf");

    const references = widget.value();
    assert.ok(Array.isArray(references));
    assert.equal(references.length, 3);
    assert.equal(new Set(references).size, 3);        // all distinct
    assert.ok(references.every((r) => r.endsWith(".pdf")));
    assert.equal(widget.files().length, 3);
    assert.equal(widget.isReady(), true);
});


test("the native input replaces the multiple selection", () => {
    const widget = new FileWidget({ multiple: true });

    choose(widget, "a.txt", "b.txt");
    choose(widget, "c.txt");                          // native pick resets the list

    assert.equal(widget.value().length, 1);
    assert.deepEqual(widget.files().map((f) => f.name), ["c.txt"]);
});


test("the + button appends to the multiple selection", () => {
    const widget = new FileWidget({ multiple: true });

    choose(widget, "a.txt", "b.txt");
    addMore(widget, "c.txt");                          // + adds to the list

    assert.equal(widget.value().length, 3);
    assert.deepEqual(widget.files().map((f) => f.name), ["a.txt", "b.txt", "c.txt"]);
});


test("appending keeps the earlier references stable", () => {
    const widget = new FileWidget({ multiple: true });

    choose(widget, "a.pdf", "b.pdf");
    const firstTwo = widget.value().slice();
    addMore(widget, "c.pdf");

    assert.deepEqual(widget.value().slice(0, 2), firstTwo);   // untouched
    assert.equal(widget.value().length, 3);
});


test("the per-file ✕ removes just that file and remints nothing", () => {
    const widget = new FileWidget({ multiple: true });

    choose(widget, "a.pdf", "b.pdf", "c.pdf");
    const refs = widget.value().slice();

    // One card per file, each with its own remove control.
    assert.equal(widget.list.children.length, 3);
    const removeB = widget.list.children[1].children[1];
    removeB.dispatch("click");

    assert.deepEqual(widget.files().map((f) => f.name), ["a.pdf", "c.pdf"]);
    assert.deepEqual(widget.value(), [refs[0], refs[2]]);     // a and c kept as-is
    assert.equal(widget.list.children.length, 2);
});


test("removing the last file of a multiple selection leaves an empty value", () => {
    const widget = new FileWidget({ multiple: true });

    choose(widget, "only.pdf");
    widget.list.children[0].children[1].dispatch("click");

    assert.deepEqual(widget.value(), []);
    assert.equal(widget.list.hidden, true);
});


test("a multiple selection is all-or-nothing on the extension filter", () => {
    const widget = new FileWidget({ extensions: [".pdf"], multiple: true });

    choose(widget, "a.pdf", "b.txt");                 // one bad extension

    assert.deepEqual(widget.value(), []);             // no references at all
    assert.equal(widget.hasError(), true);
    assert.equal(widget.message.textContent, "Not an accepted file type");
});


test("minFiles and maxFiles validate the count", () => {
    const widget = new FileWidget({
        multiple: true, minFiles: 2, maxFiles: 3,
        minMessage: "Add at least {value} files",
        maxMessage: "Keep at most {value} files",
    });

    choose(widget, "a.pdf");                          // 1 file → too few
    assert.equal(widget.isReady(), false);
    assert.equal(widget.message.textContent, "Add at least 2 files");

    addMore(widget, "b.pdf", "c.pdf", "d.pdf");       // + grows the list to 4 → too many
    assert.equal(widget.value().length, 4);
    assert.equal(widget.isReady(), false);
    assert.equal(widget.message.textContent, "Keep at most 3 files");

    widget.list.children[3].children[1].dispatch("click");   // ✕ back down to 3
    assert.equal(widget.value().length, 3);
    assert.equal(widget.isReady(), true);
});


test("an untouched file field holds its message back, like the other widgets", () => {
    const widget = new FileWidget({
        multiple: true, minFiles: 2,
        minMessage: "Add at least {value} files",
    });

    // Freshly mounted and unmet: not ready, but not shown as an error yet — a
    // required field is not born red.
    assert.equal(widget.isReady(), false);
    assert.equal(widget.message.hidden, true);
    assert.equal(widget.input.getAttribute("aria-invalid"), null);

    // showErrors() reveals it with no user interaction.
    widget.showErrors();
    assert.equal(widget.message.hidden, false);
    assert.equal(widget.message.textContent, "Add at least 2 files");
    assert.equal(widget.input.getAttribute("aria-invalid"), "true");
});


test("an empty multiple selection is a value, not empty", () => {
    const widget = new FileWidget({ multiple: true });

    assert.deepEqual(widget.value(), []);
    assert.equal(widget.isEmpty(), false);
    assert.equal(widget.isReady(), true);             // no minFiles
});


// --- setValue: current-file mode transports the existing reference ----------

test("setValue(string) shows the current file and transports it verbatim", () => {
    const widget = new FileWidget({
        extensions: [".pdf"],
        currentLabel: "Current file: {value}",
        currentRemoveLabel: "Remove current file",
    });
    let changes = 0;
    widget.onChange(() => { changes += 1; });

    widget.setValue("uploads/old-report.pdf");

    assert.equal(changes, 1);
    assert.equal(widget.value(), "uploads/old-report.pdf");   // carried verbatim
    assert.equal(widget.isEmpty(), false);
    assert.equal(widget.isReady(), true);
    assert.equal(widget.current.hidden, false);
    assert.equal(widget.current.children[0].textContent,
                 "Current file: old-report.pdf");
    // The DOM shows the current-file display, not a selected File.
    assert.equal(widget.files().length, 0);
});


test("a held current file hides the choose control until it is cleared", () => {
    const widget = new FileWidget();
    assert.equal(widget.row.hidden, false);           // choose control shown

    widget.setValue("uploads/old.pdf");
    assert.equal(widget.row.hidden, true);            // hidden while a file is held

    widget.setValue(null);                            // host clears it
    assert.equal(widget.row.hidden, false);           // choose control back
});


test("the Replace control drops the current file and brings back the native control", () => {
    const widget = new FileWidget({ currentReplaceLabel: "Replace file" });
    widget.setValue("old.pdf");
    assert.equal(widget.row.hidden, true);                // native control hidden

    const button = widget.current.children[widget.current.children.length - 1];
    assert.equal(button.tagName, "BUTTON");
    assert.equal(button.textContent, "Replace file");     // replace, not an ✕

    button.dispatch("click");
    assert.equal(widget.value(), null);                   // current dropped
    assert.equal(widget.current.hidden, true);
    assert.equal(widget.row.hidden, false);               // native control back
});


test("Replace works the same for a multiple field, revealing input and +", () => {
    const widget = new FileWidget({ multiple: true, currentReplaceLabel: "Replace file" });
    widget.setValue(["a.pdf", "b.pdf"]);
    assert.equal(widget.row.hidden, true);

    const button = widget.current.children[widget.current.children.length - 1];
    button.dispatch("click");

    assert.deepEqual(widget.value(), []);                 // list emptied, ready to rebuild
    assert.equal(widget.row.hidden, false);               // native input + the + button back
});


test("Replace stashes the current file so ↺ restores it", () => {
    const widget = new FileWidget({
        currentReplaceLabel: "Replace file",
        currentRestoreLabel: "Restore current file",
    });
    widget.setValue("uploads/old.pdf");
    assert.equal(widget.restore.hidden, true);            // nothing stashed yet

    // Replace drops the current file, reveals the native control, and offers ↺.
    widget.current.children[widget.current.children.length - 1].dispatch("click");
    assert.equal(widget.value(), null);
    assert.equal(widget.row.hidden, false);
    assert.equal(widget.restore.hidden, false);
    assert.equal(widget.restore.getAttribute("aria-label"), "Restore current file");

    // ↺ brings the current file back and hides itself.
    widget.restore.dispatch("click");
    assert.equal(widget.value(), "uploads/old.pdf");
    assert.equal(widget.current.hidden, false);
    assert.equal(widget.row.hidden, true);
    assert.equal(widget.restore.hidden, true);
});


test("↺ undoes the whole replace, even after a fresh pick", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });
    widget.setValue("uploads/old.pdf");
    widget.current.children[widget.current.children.length - 1].dispatch("click");   // Replace

    choose(widget, "new.pdf");                            // a fresh local choice
    assert.match(widget.value(), REFERENCE);
    assert.equal(widget.restore.hidden, false);           // ↺ still offered

    widget.restore.dispatch("click");
    assert.equal(widget.value(), "uploads/old.pdf");      // back to the current file
    assert.equal(widget.files().length, 0);               // the pick is forgotten
});


test("setValue drops a pending restore", () => {
    const widget = new FileWidget();
    widget.setValue("a.pdf");
    widget.current.children[widget.current.children.length - 1].dispatch("click");   // Replace
    assert.equal(widget.restore.hidden, false);

    widget.setValue("b.pdf");                             // a fresh host value
    assert.equal(widget.value(), "b.pdf");
    assert.equal(widget.restore.hidden, true);            // the old stash is gone
});


test("a current reference must clear the extension filter", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });

    assert.throws(() => widget.setValue("old.txt"),
                  /extension is not accepted/);
    assert.throws(() => widget.setValue(""),
                  /non-empty reference/);
});


test("each chosen-file card carries a distinguishable remove label on its ✕", () => {
    const widget = new FileWidget({
        multiple: true, currentRemoveLabel: "Remove current file",
    });
    choose(widget, "a.pdf", "b.pdf");

    // Same glyph on every card, so the accessible names must differ: the
    // configured label plus a one-based index in visible order.
    const labels = [...widget.list.children].map(
        (card) => card.children[1].getAttribute("aria-label"));
    assert.deepEqual(labels, ["Remove current file 1", "Remove current file 2"]);

    // Removing the first card reindexes the rest, so no stale "2" survives.
    widget.list.children[0].children[1].dispatch("click");
    const after = [...widget.list.children].map(
        (card) => card.children[1].getAttribute("aria-label"));
    assert.deepEqual(after, ["Remove current file 1"]);
});


test("the add (+) button has a descriptive accessible name", () => {
    const widget = new FileWidget({ multiple: true });

    assert.equal(widget.addBtn.textContent, "+");
    assert.equal(widget.addBtn.getAttribute("aria-label"), "Add file");
});


test("choosing a file overrides the current-file mode with a fresh reference", () => {
    const widget = new FileWidget({ extensions: [".pdf"] });
    widget.setValue("uploads/old.pdf");

    choose(widget, "new.pdf");

    // A local choice mints a new reference, distinct from the one that was set.
    assert.match(widget.value(), REFERENCE);
    assert.notEqual(widget.value(), "uploads/old.pdf");
    assert.equal(widget.current.hidden, true);
});


test("a multiple widget takes a string or an array of current references", () => {
    const widget = new FileWidget({ multiple: true, currentLabel: "Current file: {value}" });

    widget.setValue(["a.pdf", "b.pdf"]);
    assert.deepEqual(widget.value(), ["a.pdf", "b.pdf"]);   // the whole array carried
    assert.equal(widget.current.children.length, 3);        // two labels + the ✕

    widget.setValue("just-one.pdf");
    assert.deepEqual(widget.value(), ["just-one.pdf"]);
    assert.equal(widget.current.children.length, 2);        // one label + the ✕
});


test("setValue rejects a non-string, non-null (and an array on a single)", () => {
    assert.throws(() => new FileWidget().setValue(42),
                  /expects a string or null/);
    assert.throws(() => new FileWidget().setValue(["x"]),
                  /expects a string or null/);
    assert.throws(() => new FileWidget({ multiple: true }).setValue([1, 2]),
                  /expects a string, an array of strings, or null/);
});


test("setValue(null) clears a selection and a current-file mode alike", () => {
    const chosen = new FileWidget();
    choose(chosen, "a.pdf");
    chosen.setValue(null);
    assert.equal(chosen.value(), null);
    assert.equal(chosen.isEmpty(), true);
    assert.equal(chosen.input.value, "");

    const current = new FileWidget();
    current.setValue("old.pdf");
    current.setValue(null);
    assert.equal(current.value(), null);
    assert.equal(current.current.hidden, true);
});


// --- through a compiled form ------------------------------------------------

test("a single file field reads the minted reference", () => {
    const form = compileForm(plan([{ name: "doc", node: { kind: "file" } }]));
    const widget = form.fields[0].widget.widget;

    choose(widget, "cv.pdf");

    assert.match(form.read().doc, REFERENCE);
    assert.equal(form.isReady(), true);
});


test("a multiple file field reads the array of references", () => {
    const form = compileForm(plan([{
        name: "docs", node: { kind: "file", options: { multiple: true } },
    }]));
    const widget = form.fields[0].widget.widget;

    choose(widget, "a.pdf", "b.pdf");

    const references = form.read().docs;
    assert.equal(references.length, 2);
    assert.match(references[0], REFERENCE);
});


test("a current-file mode transports the existing reference through the form", () => {
    const form = compileForm(plan([{ name: "doc", node: { kind: "file" } }]));
    const widget = form.fields[0].widget.widget;

    widget.setValue("uploads/existing.pdf");

    assert.deepEqual(form.read(), { doc: "uploads/existing.pdf" });   // carried back
    assert.equal(form.isReady(), true);

    // Clearing to null is the host's own call now, through setValue(null) —
    // "keep vs remove" is then its to decide.
    widget.setValue(null);
    assert.deepEqual(form.read(), { doc: null });
});


test("an optional file switched off reads null", () => {
    const form = compileForm(plan([{
        name: "doc", optional: true, enabled: false, node: { kind: "file" },
    }]));

    assert.equal(form.fields[0].widget.enabled(), false);
    assert.deepEqual(form.read(), { doc: null });
    assert.equal(form.isReady(), true);
});


// --- byte-size bounds -------------------------------------------------------

// The size of a chosen file is the one thing about it the browser can weigh, so
// the widget refuses a File that already breaks a bound instead of letting the
// upload happen and the core refuse it afterwards. A reference carries no bytes,
// so it is never weighed here.

function sized(widget, ...pairs) {
    widget.input.files = pairs.map(([name, size]) => ({ name, size }));
    widget.input.dispatch("change");
}


function bounded(extra = {}) {
    return new FileWidget({
        extensions: [".pdf"], minSize: 100, maxSize: 1000, ...extra,
    });
}


test("a file inside the bounds is accepted", () => {
    const widget = bounded();

    sized(widget, ["report.pdf", 500]);

    assert.equal(widget.hasError(), false);
    assert.equal(widget.isReady(), true);
    assert.match(widget.value(), REFERENCE);
});


test("exactly the minimum and exactly the maximum are both inside", () => {
    for (const size of [100, 1000]) {
        const widget = bounded();

        sized(widget, ["report.pdf", size]);

        assert.equal(widget.hasError(), false, `size ${size}`);
        assert.equal(widget.isReady(), true, `size ${size}`);
    }
});


test("one byte below the minimum is refused", () => {
    const widget = bounded();

    sized(widget, ["report.pdf", 99]);

    assert.equal(widget.hasError(), true);
    assert.equal(widget.isReady(), false);
    assert.match(widget.error(), /too small/);
});


test("one byte above the maximum is refused", () => {
    const widget = bounded();

    sized(widget, ["report.pdf", 1001]);

    assert.equal(widget.hasError(), true);
    assert.equal(widget.isReady(), false);
    assert.match(widget.error(), /too large/);
});


test("a refused file mints no reference and no upload", () => {
    const widget = bounded();

    sized(widget, ["report.pdf", 5000]);

    assert.equal(widget.value(), null);
    assert.deepEqual(widget.uploads(), []);
});


test("the message names the bound the way the widget names a size", () => {
    const widget = new FileWidget({ minSize: 2048 });

    sized(widget, ["report.pdf", 1]);

    assert.equal(widget.error(), "File is too small; minimum 2 KB");
});


test("the size messages are configurable", () => {
    const widget = new FileWidget({
        maxSize: 10, maxSizeMessage: "Over {value}",
    });

    sized(widget, ["report.pdf", 11]);

    assert.equal(widget.error(), "Over 10 B");
});


test("without a bound nothing is weighed", () => {
    const widget = new FileWidget();

    sized(widget, ["report.pdf", 0]);

    assert.equal(widget.hasError(), false);
    assert.equal(widget.isReady(), true);
});


test("choosing a valid file clears a size error", () => {
    const widget = bounded();

    sized(widget, ["report.pdf", 5000]);
    assert.equal(widget.hasError(), true);

    sized(widget, ["report.pdf", 500]);

    assert.equal(widget.hasError(), false);
    assert.equal(widget.error(), null);
    assert.match(widget.value(), REFERENCE);
});


test("removing the selection clears a size error", () => {
    const widget = bounded({ multiple: true });

    widget._ingest([{ name: "big.pdf", size: 5000 }], true);
    assert.equal(widget.hasError(), true);

    widget.setValue(null);

    assert.equal(widget.hasError(), false);
    assert.equal(widget.error(), null);
});


test("an extension failure is reported before a size failure", () => {
    const widget = bounded();

    sized(widget, ["notes.txt", 5000]);

    assert.equal(widget.error(), "Not an accepted file type");
});


test("in a multiple widget every file is weighed on its own", () => {
    const widget = bounded({ multiple: true });

    sized(widget, ["a.pdf", 900], ["b.pdf", 900], ["c.pdf", 900]);

    // 2700 bytes in total, over maxSize, but no file is: the bound is per file.
    assert.equal(widget.hasError(), false);
    assert.equal(widget.uploads().length, 3);
});


test("one oversized file refuses the whole batch it arrived in", () => {
    const widget = bounded({ multiple: true });

    sized(widget, ["a.pdf", 500], ["b.pdf", 5000]);

    assert.equal(widget.hasError(), true);
    assert.deepEqual(widget.value(), []);
    assert.deepEqual(widget.uploads(), []);
});


test("an appended oversized file leaves the accepted ones alone", () => {
    const widget = bounded({ multiple: true });

    sized(widget, ["a.pdf", 500]);
    widget._ingest([{ name: "big.pdf", size: 5000 }], true);

    assert.equal(widget.hasError(), true);
    assert.equal(widget.isReady(), false);
    assert.equal(widget.value().length, 1);
});


test("a planted reference is never weighed", () => {
    const widget = bounded();

    widget.setValue("uploads/whatever.pdf");

    assert.equal(widget.hasError(), false);
    assert.equal(widget.isReady(), true);
    assert.equal(widget.value(), "uploads/whatever.pdf");
    assert.deepEqual(widget.uploads(), []);
});


test("a default plants a reference without weighing it either", () => {
    const form = compileForm(plan([{
        name: "doc",
        hasDefault: true,
        default: "uploads/existing.pdf",
        node: { kind: "file", options: {
            extensions: [".pdf"], minSize: 100, maxSize: 1000 } },
    }]));

    assert.equal(form.hasError(), false);
    assert.equal(form.isReady(), true);
    assert.deepEqual(form.read(), { doc: "uploads/existing.pdf" });
    assert.deepEqual(form.uploads(), []);
});


test("the bounds reach a file node nested in a list of groups", () => {
    const file = { kind: "file", options: {
        extensions: [".pdf"], minSize: 100, maxSize: 1000 } };

    const form = compileForm(plan([{
        name: "reports",
        node: { kind: "list", item: { kind: "object", fields: [
            { name: "doc", node: file },
        ] } },
    }]));

    const list = form.fields[0].widget.widget;
    list.add();

    const widget = list.widgets()[0].children[0].widget.widget;

    sized(widget, ["deep.pdf", 5000]);

    assert.equal(widget.hasError(), true);
    assert.equal(form.isReady(), false);
    assert.deepEqual(form.uploads(), []);
});


test("a node whose minSize exceeds its maxSize is refused", () => {
    rejects(plan([{ name: "a", node: {
        kind: "file", options: { minSize: 10, maxSize: 5 } } }]),
            "minSize: must not exceed maxSize");
});


test("a size bound must be a non-negative integer", () => {
    for (const bad of [-1, 1.5, true, "10"]) {
        rejects(plan([{ name: "a", node: {
            kind: "file", options: { minSize: bad } } }]),
                "node.options.minSize");
    }
});


test("size bounds are legal on a single node, not only a multiple one", () => {
    // minFiles / maxFiles need a multiple node; the byte bounds are per file,
    // so they carry no such rule.
    const checked = checkPlan(plan([{ name: "a", node: {
        kind: "file", options: { multiple: false, minSize: 1, maxSize: 2 } } }]));

    assert.equal(checked.fields[0].node.options.minSize, 1);
    assert.equal(checked.fields[0].node.options.maxSize, 2);
});
