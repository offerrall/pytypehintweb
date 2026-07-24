import "./dom.mjs";

import { readFileSync } from "node:fs";

import { compileForm } from "../../src/pytypehintweb/static/form.js";


// The star round trip for a struct with a file field, the create/edit form in
// one. `ops.set` plants an existing record on the fields (a str value, or a file
// widget's current reference — its own past truth). `ops.choose` then picks new
// File(s) on a file field, as a user replacing an upload would. What read()
// reports is printed so a Python test can carry it across JSON, decode() and
// build(): an untouched reference must come back byte-identical, a replaced one
// as a fresh minted reference.
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
    input.files = files.map((fileName) => ({ name: fileName }));
    input.dispatch("change");
}

process.stdout.write(JSON.stringify({ read: form.read() }));
