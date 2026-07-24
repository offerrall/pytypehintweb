import "./dom.mjs";

import { readFileSync } from "node:fs";

import {
    ChoiceWidget, Field, GroupWidget, ListWidget,
} from "../../src/pytypehintweb/static/fields.js";
import {
    BoolWidget, FloatWidget, IntWidget, StrWidget,
} from "../../src/pytypehintweb/static/inputs.js";
import { compileForm } from "../../src/pytypehintweb/static/form.js";


let counter = 0;


function fill(widget) {
    if (widget instanceof Field) {
        fill(widget.widget);
        return;
    }

    if (widget instanceof GroupWidget) {
        for (const child of widget.children) {
            fill(child.widget);
        }
        return;
    }

    if (widget instanceof ListWidget) {
        widget.add();

        for (const item of widget.widgets()) {
            fill(item);
        }
        return;
    }

    if (widget instanceof ChoiceWidget) {
        fill(widget.active());
        return;
    }

    counter += 1;

    if (widget instanceof StrWidget) {
        widget.input.value = `text${counter}`;
        widget.input.dispatch("input");
        return;
    }

    if (widget instanceof IntWidget) {
        widget.input.value = String(counter);
        widget.input.dispatch("input");
        return;
    }

    if (widget instanceof FloatWidget) {
        widget.input.value = String(counter);
        widget.input.dispatch("input");
        return;
    }

    if (widget instanceof BoolWidget) {
        widget.input.checked = true;
        widget.input.dispatch("change");
    }
}


const plan = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const form = compileForm(plan, { prefix: "roundtrip" });

for (const field of form.fields) {
    fill(field.widget);
}

process.stdout.write(JSON.stringify({
    name: form.name,
    isReady: form.isReady(),
    hasError: form.hasError(),
    read: form.read(),
}));
