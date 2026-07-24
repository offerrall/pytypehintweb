import "./dom.mjs";

import { readFileSync } from "node:fs";

import { compileForm } from "../../src/pytypehintweb/static/form.js";


// The star round trip for an enum: pick a member by name in the single enum
// field a plan mounts and print what read() reports, so a Python test can carry
// it across JSON, decode() and build(). Unlike a text field, the enum widget is
// a select, so the member is chosen with setValue rather than typed.
const plan = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const name = process.argv[3];

const form = compileForm(plan, { prefix: "star" });
const widget = form.fields[0].widget.widget;

widget.setValue(name);

process.stdout.write(JSON.stringify({ read: form.read() }));
