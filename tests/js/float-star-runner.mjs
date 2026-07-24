import "./dom.mjs";

import { readFileSync } from "node:fs";

import { compileForm } from "../../src/pytypehintweb/static/form.js";


// The star round trip: type raw keystrokes into the single float field a plan
// mounts and print what read() reports, so a Python test can carry it across
// JSON, decode() and build().
const plan = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const raw = process.argv[3];

const form = compileForm(plan, { prefix: "star" });
const widget = form.fields[0].widget.widget;

widget.input.value = raw;
widget.input.dispatch("input");

process.stdout.write(JSON.stringify({ read: form.read() }));
