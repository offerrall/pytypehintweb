import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { texts } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { FileWidget } from "../../src/pytypehintweb/static/inputs.js";


// A current file is shown compacted: its own name when the reference carries
// one, and at most 32 trailing characters otherwise. What the host reads is
// never compacted — value(), read() and uploads() carry the reference whole.


const ELLIPSIS = "\u2026";
const SMILEY = "\u{1F642}";


function mount(fields) {
    return compileForm({ v: 1, kind: "form", name: "files", fields },
                       { prefix: "fl" });
}


function single(name, options = {}, extra = {}) {
    return { name, node: { kind: "file", options }, ...extra };
}


function planted(reference, options = {}) {
    const widget = new FileWidget(options);

    widget.setValue(reference);

    return widget;
}


function shown(widget) {
    return texts(widget.el, "pth-file-current-label");
}


function label(reference, options = {}) {
    return shown(planted(reference, options))[0];
}


function choose(widget, ...names) {
    widget.input.files = names.map((file) => ({ name: file }));
    widget.input.dispatch("change");
}


// --- what the label shows ---------------------------------------------------

test("a short name is shown whole", () => {
    assert.equal(label("report.pdf"), "Current file: report.pdf");
});


test("a name of exactly the limit is shown whole", () => {
    const name = `${"a".repeat(28)}.pdf`;

    assert.equal(name.length, 32);
    assert.equal(label(name), `Current file: ${name}`);
});


test("one character past the limit is compacted", () => {
    const name = `${"a".repeat(29)}.pdf`;

    assert.equal(name.length, 33);
    assert.equal(label(name), `Current file: ${ELLIPSIS}${name.slice(-32)}`);
});


test("a long POSIX path is shown as its file name", () => {
    assert.equal(
        label("/var/lib/func_to_web/uploads/photo-123456789.png"),
        "Current file: photo-123456789.png");
});


test("a long Windows path is shown as its file name", () => {
    assert.equal(
        label("C:\\Users\\pcmain\\AppData\\uploads\\photo-123456789.png"),
        "Current file: photo-123456789.png");
});


test("a long URL is shown as its last segment", () => {
    assert.equal(
        label("https://example.com/uploads/very-long-ref/photo-123456789.png"),
        "Current file: photo-123456789.png");
});


test("a reference with no separator falls back to its last characters", () => {
    const reference = `${"reference-".repeat(6)}tail.bin`;

    assert.equal(label(reference),
                 `Current file: ${ELLIPSIS}${reference.slice(-32)}`);
});


test("a file name longer than the limit is compacted too", () => {
    const name = `${"n".repeat(60)}.pdf`;

    assert.equal(label(`/uploads/${name}`),
                 `Current file: ${ELLIPSIS}${name.slice(-32)}`);
});


test("a path ending in a separator keeps its trailing characters", () => {
    const reference = `/uploads/${"deep/".repeat(12)}`;

    assert.equal(label(reference),
                 `Current file: ${ELLIPSIS}${reference.slice(-32)}`);
});


test("a query string belongs to the name it hangs from", () => {
    const name = "photo.png?token=abcdefghijklmnopqrstuvwxyz012345";

    assert.equal(name.length, 48);
    assert.equal(label(`/uploads/${name}`),
                 `Current file: ${ELLIPSIS}abcdefghijklmnopqrstuvwxyz012345`);
});


test("a fragment stays inside the name as well", () => {
    assert.equal(label("/uploads/photo.png#page=2"),
                 "Current file: photo.png#page=2");
});


test("a unicode name is cut by characters, never mid pair", () => {
    const name = `${SMILEY.repeat(40)}.png`;
    const visible = label(`/uploads/${name}`).slice("Current file: ".length);
    const characters = Array.from(visible);

    assert.equal(characters[0], ELLIPSIS);
    assert.equal(characters.length, 33);
    assert.equal(characters[1], SMILEY);
    assert.equal(visible.endsWith(".png"), true);
});


test("html characters are shown as text, not as markup", () => {
    const widget = planted("/uploads/<b>&\"'x.png");
    const item = widget.current.children[0];

    assert.equal(item.textContent, "Current file: <b>&\"'x.png");
    assert.deepEqual(item.children, []);
});


test("a closing tag is cut like the path separator it contains", () => {
    assert.equal(label("/uploads/<b>x</b>.png"), "Current file: b>.png");
});


// --- what the host reads ----------------------------------------------------

test("the whole reference survives the compacted label", () => {
    const reference = "https://example.com/uploads/very-long-ref/photo-1234.png";
    const widget = planted(reference);

    assert.equal(shown(widget)[0], "Current file: photo-1234.png");
    assert.equal(widget.value(), reference);
});


test("read() carries the reference whole", () => {
    const reference = "/var/lib/func_to_web/uploads/photo-123456789.png";
    const form = mount([single("photo", { extensions: [".png"] },
                               { hasDefault: true, default: reference })]);
    const widget = form.fields[0].widget.widget;

    assert.equal(shown(widget)[0], "Current file: photo-123456789.png");
    assert.deepEqual(form.read(), { photo: reference });
    assert.deepEqual(form.uploads(), []);
});


test("every reference of a multiple field is compacted on its own", () => {
    const references = ["/uploads/one.png", "/uploads/two.png"];
    const widget = planted(references, { multiple: true });

    assert.deepEqual(shown(widget),
                     ["Current file: one.png", "Current file: two.png"]);
    assert.deepEqual(widget.value(), references);
});


test("the plan node is not read for anything new", () => {
    const reference = "/var/lib/func_to_web/uploads/photo-123456789.png";
    const node = { kind: "file", options: { extensions: [".png"] } };
    const before = JSON.stringify(node);

    mount([{ name: "photo", node, hasDefault: true, default: reference }]);

    assert.equal(JSON.stringify(node), before);
});


// --- replacing a planted reference ------------------------------------------

test("replacing the current file leaves the local pick untouched", () => {
    const widget = planted("/var/lib/uploads/photo-123456789.png",
                           { extensions: [".png"] });

    widget.setValue(null);
    choose(widget, "local-picture.png");

    assert.deepEqual(shown(widget), []);
    assert.equal(widget.file().name, "local-picture.png");
    assert.equal(widget.uploads().length, 1);
    assert.equal(widget.value().endsWith(".png"), true);
});


test("a local pick keeps the name the browser gave it", () => {
    const widget = new FileWidget({ extensions: [".png"] });

    choose(widget, `${"local-".repeat(10)}picture.png`);

    assert.deepEqual(shown(widget), []);
    assert.equal(widget.file().name, `${"local-".repeat(10)}picture.png`);
});
