import "./dom.mjs";

import { readFileSync } from "node:fs";

import { compileForm } from "../../src/pytypehintweb/static/form.js";


// The star round trip for a struct with a file field, the create/edit form in
// one. `ops.set` plants an existing record on the fields (a str value, or a file
// widget's current reference — its own past truth). `ops.choose` then picks new
// File(s) on a file field, as a user replacing an upload would: a plain name, or
// `{ name, size }` where the test needs the browser to know a byte size. What
// read() reports is printed so a Python test can carry it across JSON, decode()
// and build(): an untouched reference must come back byte-identical, a replaced
// one as a fresh minted reference. Each widget's error() goes out beside it,
// because a local pick the widget refuses — a wrong extension, a size outside
// the node's bounds — mints nothing, and the refusal is the only thing left to
// observe.
const plan = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const ops = JSON.parse(readFileSync(process.argv[3], "utf-8"));

const form = compileForm(plan, { prefix: "star" });

const byName = {};
for (const field of form.fields) {
    byName[field.name] = field.widget.widget;
}

for (const [name, value] of Object.entries(ops.set ?? {})) {
    byName[name].setValue(value);
}

for (const [name, files] of Object.entries(ops.choose ?? {})) {
    const input = byName[name].input;
    input.files = files.map(
        (file) => (typeof file === "string" ? { name: file } : { ...file }));
    input.dispatch("change");
}

const errors = {};

for (const [name, widget] of Object.entries(byName)) {
    errors[name] = typeof widget.error === "function" ? widget.error() : null;
}

process.stdout.write(JSON.stringify({ read: form.read(), errors }));
