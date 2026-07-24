import test from "node:test";
import assert from "node:assert/strict";

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
    DATE_DEFAULTS, ENUM_DEFAULTS, FILE_DEFAULTS, FLOAT_DEFAULTS, INT_DEFAULTS,
    LIST_DEFAULTS, OPTIONAL_DEFAULTS, STR_DEFAULTS, TIME_DEFAULTS,
} from "../../src/pytypehintweb/static/defaults.js";
import {
    normalizeField, normalizeNode, normalizePlan,
} from "../../src/pytypehintweb/static/normalize.js";

// Field and form default values are no longer a plan-filling concern (a plan
// carries every property), so they live here purely as the documented
// reference for the plan.md tables.
const FIELD_REFERENCE = {
    description: null, optional: false, enabled: true, hasDefault: false,
};
const FORM_REFERENCE = { description: null };

const DOCS = fileURLToPath(new URL("../../docs/", import.meta.url));

const NODE_KINDS = new Set(
    ["str", "int", "float", "date", "time", "enum", "file", "list", "object",
     "choice", "optional"]);

// Every documented JSON example is a complete, valid plan example — there is no
// abbreviated form and no marker convention. A partial illustration is written
// as plain text, not a ```json block.
const BLOCK = /```json\n([\s\S]*?)```/g;


function jsonBlocks(name) {
    const text = readFileSync(DOCS + name, "utf-8");

    return [...text.matchAll(BLOCK)].map((match) => JSON.parse(match[1]));
}


function tableKeys(name, heading) {
    const text = readFileSync(DOCS + name, "utf-8");
    const start = text.indexOf(`\n${heading}\n`);

    assert.notEqual(start, -1, `heading not found: ${heading}`);

    const rest = text.slice(start + heading.length + 2);
    const end = rest.indexOf("\n#");
    const section = end === -1 ? rest : rest.slice(0, end);

    return section
        .split("\n")
        .filter((line) => line.startsWith("|") && line.includes("`"))
        .flatMap((line) => [...line.split("|")[1].matchAll(/`([^`]+)`/g)]
            .map((match) => match[1]));
}


// Validate a plan example exactly as written — no default filling. Returns false
// for a JSON block that is not a plan/node/field example (so it is ignored).
function isPlanExample(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return false;
    }

    return value.kind === "form"
        || NODE_KINDS.has(value.kind)
        || (typeof value.name === "string" && value.node !== undefined);
}


function validateAsWritten(value) {
    if (value.kind === "form") {
        normalizePlan(value);
    } else if (NODE_KINDS.has(value.kind)) {
        // Optional nodes are only valid as list items; allow one at the top
        // level so a standalone optional example can still be checked.
        normalizeNode(value, "node", value.kind === "optional");
    } else {
        normalizeField(value);
    }
}


test("every documented json example is a complete, valid plan example", () => {
    let checked = 0;

    for (const name of ["plan.md", "javascript.md", "getting-started.md"]) {
        for (const value of jsonBlocks(name)) {
            if (!isPlanExample(value)) {
                continue;
            }

            checked += 1;

            try {
                validateAsWritten(value);
            } catch (caught) {
                assert.fail(
                    `${name}: this JSON example is not a complete, valid plan `
                    + `example (a partial illustration must be plain text, not a `
                    + `\`\`\`json block):\n${JSON.stringify(value)}\n${caught.message}`);
            }
        }
    }

    assert.ok(checked > 0, "no documented plan examples were found");
});


const TABLES = [
    ["### String options", STR_DEFAULTS, []],
    ["### Integer options", INT_DEFAULTS, []],
    ["### Float options", FLOAT_DEFAULTS, []],
    ["### Date options", DATE_DEFAULTS, []],
    ["### Time options", TIME_DEFAULTS, []],
    ["### Enum options", ENUM_DEFAULTS, []],
    ["### File options", FILE_DEFAULTS, []],
    ["### List options", LIST_DEFAULTS, []],
    ["### Form", FORM_REFERENCE, []],
    ["### Field", FIELD_REFERENCE, ["label"]],
    ["### Optional item nodes", OPTIONAL_DEFAULTS, []],
];


for (const [heading, defaults, extra] of TABLES) {
    test(`the plan contract documents every default under "${heading}"`, () => {
        const documented = tableKeys("plan.md", heading);
        const expected = [...Object.keys(defaults), ...extra];

        assert.deepEqual(documented.slice().sort(), expected.slice().sort());
    });
}
