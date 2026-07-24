import test from "node:test";
import assert from "node:assert/strict";

import { checkPlan } from "./harness.mjs";


function planWith(node, extra = {}) {
    return {
        v: 1,
        kind: "form",
        name: "example",
        fields: [{ name: "value", node, ...extra }],
    };
}


function rejects(plan, fragment) {
    assert.throws(() => checkPlan(plan), (error) => {
        assert.ok(error instanceof TypeError, `expected a TypeError, got ${error}`);
        assert.ok(error.message.includes(fragment),
                  `expected ${JSON.stringify(error.message)} to mention `
                  + JSON.stringify(fragment));
        return true;
    });
}


test("checkPlan returns the normalized plan", () => {
    const normalized = checkPlan(planWith({ kind: "str" }));

    assert.equal(normalized.fields[0].node.options.patternMessage,
                 "Invalid format");
    assert.equal(normalized.description, null);
});


test("minLength above maxLength is rejected on a compact node", () => {
    rejects(planWith({ kind: "str", options: { minLength: 5, maxLength: 2 } }),
            "must not exceed maxLength");
});


test("min above max is rejected on a compact node", () => {
    rejects(planWith({ kind: "int", options: { min: 5, max: 2 } }),
            "must not exceed max");
});


test("a choice shorter than minLength is rejected", () => {
    rejects(planWith({
        kind: "str",
        options: { minLength: 3, choices: ["ab", "abc"] },
    }), "is shorter than minLength 3");
});


test("a choice longer than maxLength is rejected", () => {
    rejects(planWith({
        kind: "str",
        options: { maxLength: 2, choices: ["ab", "abc"] },
    }), "is longer than maxLength 2");
});


test("string length counts code points, not UTF-16 units", () => {
    checkPlan(planWith({
        kind: "str",
        options: { maxLength: 1, choices: ["\u{1F600}"] },
    }));
});


test("a choice failing the pattern is rejected", () => {
    rejects(planWith({
        kind: "str",
        options: { pattern: "[a-z]+", choices: ["ok", "N0"] },
    }), "does not match the declared pattern");
});


test("an int choice below min is rejected", () => {
    rejects(planWith({ kind: "int", options: { min: 10, choices: [5, 20] } }),
            "is below min 10");
});


test("an int choice above max is rejected", () => {
    rejects(planWith({ kind: "int", options: { max: 10, choices: [5, 20] } }),
            "is above max 10");
});


test("an int choice breaking multipleOf is rejected", () => {
    rejects(planWith({ kind: "int", options: { multipleOf: 5, choices: [5, 7] } }),
            "is not a multiple of 5");
});


test("duplicated choices are rejected", () => {
    rejects(planWith({ kind: "str", options: { choices: ["a", "a"] } }),
            "duplicated choice");
});


test("an empty choices array is rejected", () => {
    rejects(planWith({ kind: "str", options: { choices: [] } }),
            "expected a non-empty array");
});


test("a slider without min or max is rejected", () => {
    rejects(planWith({ kind: "int", options: { slider: true, min: 0 } }),
            "slider needs both min and max");
});


test("a slider with no reachable multiple is rejected", () => {
    rejects(planWith({
        kind: "int",
        options: { slider: true, min: 1, max: 9, step: 4, multipleOf: 10 },
    }), "is a multiple of 10");
});


test("a slider with a reachable multiple is accepted", () => {
    checkPlan(planWith({
        kind: "int",
        options: { slider: true, min: 0, max: 100, step: 5, multipleOf: 25 },
    }));
});


test("choices and password ask for different controls", () => {
    rejects(planWith({
        kind: "str",
        options: { choices: ["a"], password: true },
    }), "choices and password ask for different controls");
});


test("choices and slider ask for different controls", () => {
    rejects(planWith({
        kind: "int",
        options: { choices: [1], slider: true, min: 0, max: 10 },
    }), "choices and slider ask for different controls");
});


test("str choices and a placeholder ask for different controls", () => {
    rejects(planWith({
        kind: "str",
        options: { choices: ["a"], placeholder: "Pick" },
    }), "choices and placeholder ask for different controls");
});


test("int choices and a placeholder ask for different controls", () => {
    rejects(planWith({
        kind: "int",
        options: { choices: [1], placeholder: "Pick" },
    }), "choices and placeholder ask for different controls");
});


test("a slider and a placeholder ask for different controls", () => {
    rejects(planWith({
        kind: "int",
        options: { slider: true, min: 0, max: 10, placeholder: "Pick" },
    }), "slider and placeholder ask for different controls");
});


test("a choice default with an unknown key is rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    }, { hasDefault: true, default: { branch: 0, value: "x", junk: true } }),
            "unknown property");
});


test("a non-string branch value is rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: 1, mode: "plain", node: { kind: "str" } },
            { value: 2, mode: "plain", node: { kind: "int" } },
        ],
    }), "expected a string");
});


test("duplicate branch values are rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: "same", mode: "plain", node: { kind: "str" } },
            { value: "same", mode: "plain", node: { kind: "int" } },
        ],
    }), "duplicated branch value");
});


test("a default outside the declared choices is rejected", () => {
    rejects(planWith({ kind: "str", options: { choices: ["a", "b"] } },
                     { hasDefault: true, default: "c" }),
            "expected one of the declared choices");
});


test("a default of the wrong type is rejected", () => {
    rejects(planWith({ kind: "int" }, { hasDefault: true, default: "seven" }),
            "expected a safe integer for int node");
});


test("a default with too few list items is rejected", () => {
    rejects(planWith({ kind: "list", minItems: 2, item: { kind: "str" } },
                     { hasDefault: true, default: ["only"] }),
            "expected at least 2 items");
});


// --- scalar defaults must satisfy the node constraints ----------------------

test("a string default shorter than minLength is rejected", () => {
    rejects(planWith({ kind: "str", options: { minLength: 3 } },
                     { hasDefault: true, default: "ab" }),
            "plan.fields[0].default: is shorter than minLength 3");
});


test("a string default longer than maxLength is rejected", () => {
    rejects(planWith({ kind: "str", options: { maxLength: 2 } },
                     { hasDefault: true, default: "abc" }),
            "plan.fields[0].default: is longer than maxLength 2");
});


test("a string default that fails the pattern is rejected", () => {
    rejects(planWith({ kind: "str", options: { pattern: "[a-z]+" } },
                     { hasDefault: true, default: "AB1" }),
            "plan.fields[0].default: does not match the declared pattern");
});


test("an integer default below min is rejected", () => {
    rejects(planWith({ kind: "int", options: { min: 10 } },
                     { hasDefault: true, default: 6 }),
            "plan.fields[0].default: is below min 10");
});


test("an integer default above max is rejected", () => {
    rejects(planWith({ kind: "int", options: { max: 5 } },
                     { hasDefault: true, default: 9 }),
            "plan.fields[0].default: is above max 5");
});


test("an integer default that breaks multipleOf is rejected", () => {
    rejects(planWith({ kind: "int", options: { multipleOf: 5 } },
                     { hasDefault: true, default: 7 }),
            "plan.fields[0].default: is not a multiple of 5");
});


test("an integer default outside the declared choices is rejected", () => {
    rejects(planWith({ kind: "int", options: { choices: [1, 2, 3] } },
                     { hasDefault: true, default: 4 }),
            "expected one of the declared choices");
});


test("a slider default off the step grid is rejected", () => {
    rejects(planWith({
        kind: "int",
        options: { slider: true, min: 0, max: 20, step: 5 },
    }, { hasDefault: true, default: 7 }),
            "plan.fields[0].default: is not on the slider grid stepping by 5");
});


test("a slider default on the grid but off multipleOf is rejected", () => {
    rejects(planWith({
        kind: "int",
        options: { slider: true, min: 0, max: 30, step: 2, multipleOf: 6 },
    }, { hasDefault: true, default: 2 }),
            "is not a multiple of 6");
});


test("valid scalar and slider defaults are accepted", () => {
    assert.doesNotThrow(() => checkPlan(planWith(
        { kind: "str", options: { minLength: 2, maxLength: 5, pattern: "[a-z]+" } },
        { hasDefault: true, default: "abc" })));

    assert.doesNotThrow(() => checkPlan(planWith(
        { kind: "int", options: { min: 0, max: 100, multipleOf: 5 } },
        { hasDefault: true, default: 25 })));

    assert.doesNotThrow(() => checkPlan(planWith(
        { kind: "int", options: { slider: true, min: 0, max: 20, step: 5 } },
        { hasDefault: true, default: 15 })));
});


test("a nested object default is validated against child constraints", () => {
    rejects(planWith({
        kind: "object",
        fields: [{ name: "n", node: { kind: "str", options: { minLength: 3 } } }],
    }, { hasDefault: true, default: { n: "ab" } }),
            "plan.fields[0].default.n: is shorter than minLength 3");
});


test("a default pointing at a missing branch is rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    }, { hasDefault: true, default: { branch: 2, value: "x" } }),
            "branch 2 is out of range");
});


test("ambiguous branch values are rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [
            { value: "str", mode: "wrapped", node: { kind: "str" } },
            { value: "str", mode: "wrapped", node: { kind: "str" } },
        ],
    }), "duplicated branch value");
});


test("a message template without {value} is rejected", () => {
    rejects(planWith({ kind: "str", options: { minMessage: "too short" } }),
            "must contain exactly one {value} placeholder");
});


test("a message template with an unexpected placeholder is rejected", () => {
    rejects(planWith({ kind: "str", options: { patternMessage: "bad {value}" } }),
            "must not contain placeholders");
});


test("a message template with unbalanced braces is rejected", () => {
    rejects(planWith({ kind: "str", options: { minMessage: "{value} }" } }),
            "has unbalanced braces");
});


test("list minItems above maxItems is rejected", () => {
    rejects(planWith({
        kind: "list",
        minItems: 3,
        maxItems: 1,
        item: { kind: "str" },
    }), "must not exceed maxItems");
});


test("an empty object node is rejected", () => {
    rejects(planWith({ kind: "object", fields: [] }),
            "expected a non-empty array");
});


test("an empty choice node is rejected", () => {
    rejects(planWith({ kind: "choice", branches: [] }),
            "expected at least two branches");
});


test("a single-branch choice node is rejected", () => {
    rejects(planWith({
        kind: "choice",
        branches: [{ value: "str", mode: "plain", node: { kind: "str" } }],
    }), "expected at least two branches");
});


test("a single-branch choice is not silently unwrapped", () => {
    assert.throws(() => checkPlan(planWith({
        kind: "choice",
        branches: [{ value: "str", mode: "plain", node: { kind: "str" } }],
    })));
});


test("a two-branch choice node is accepted", () => {
    const normalized = checkPlan(planWith({
        kind: "choice",
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    }));

    assert.equal(normalized.fields[0].node.branches.length, 2);
    assert.equal(normalized.fields[0].node.positionLabel, "Mode {current} of {total}");
});


function twoBranchChoice(extra) {
    return planWith({
        kind: "choice",
        ...extra,
        branches: [
            { value: "str", mode: "plain", node: { kind: "str" } },
            { value: "int", mode: "plain", node: { kind: "int" } },
        ],
    });
}


test("a position label without both placeholders is rejected", () => {
    rejects(twoBranchChoice({ positionLabel: "Mode {current}" }),
            "must contain exactly one {current} and one {total}");
});


test("a position label with a repeated placeholder is rejected", () => {
    rejects(twoBranchChoice({ positionLabel: "{current} {current} {total}" }),
            "must contain exactly one {current} and one {total}");
});


test("a previous label with a placeholder is rejected", () => {
    rejects(twoBranchChoice({ previousLabel: "Back {current}" }),
            "must not contain placeholders");
});


test("a custom mode configuration is accepted and normalized", () => {
    const normalized = checkPlan(twoBranchChoice({
        previousLabel: "Anterior",
        nextLabel: "Siguiente",
        positionLabel: "Modo {current} de {total}",
    }));

    const node = normalized.fields[0].node;
    assert.equal(node.previousLabel, "Anterior");
    assert.equal(node.nextLabel, "Siguiente");
    assert.equal(node.positionLabel, "Modo {current} de {total}");
});


test("an unknown property on a choice node is rejected", () => {
    rejects(twoBranchChoice({ heading: "Pick" }),
            "plan.fields[0].node.heading: unknown property");
});


test("semantics are checked inside nested compact nodes", () => {
    rejects(planWith({
        kind: "list",
        item: {
            kind: "object",
            fields: [{
                name: "size",
                node: { kind: "int", options: { min: 9, max: 1 } },
            }],
        },
    }), "plan.fields[0].node.item.fields[0].node.options.min: must not exceed max");
});
