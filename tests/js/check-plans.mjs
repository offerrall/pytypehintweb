import "./dom.mjs";

import { readFileSync } from "node:fs";

import { checkPlan } from "../../src/pytypehintweb/static/contract.js";
import { compileForm } from "../../src/pytypehintweb/static/form.js";


const plans = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const failed = [];
let checked = 0;
let mounted = 0;

for (const [id, plan] of Object.entries(plans)) {
    try {
        checkPlan(plan);
        checked += 1;
    } catch (error) {
        failed.push({ id, stage: "checkPlan", error: error.message });
        continue;
    }

    try {
        const form = compileForm(plan, { prefix: id });

        form.isReady();
        form.hasError();
        form.read();

        for (const field of form.fields) {
            field.widget.value();
        }

        mounted += 1;
    } catch (error) {
        failed.push({ id, stage: "compileForm", error: error.message });
    }
}

process.stdout.write(JSON.stringify({ checked, mounted, failed }));
