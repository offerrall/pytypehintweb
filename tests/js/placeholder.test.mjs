import test from "node:test";
import assert from "node:assert/strict";

import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { expandNode } from "./plan-fixture.mjs";


function placeholderOf(node) {
    return normalizeNode(expandNode(node)).options.placeholder;
}


test("an omitted placeholder on a plain str input normalizes to null", () => {
    assert.equal(placeholderOf({ kind: "str" }), null);
    assert.equal(placeholderOf({ kind: "str", options: { minLength: 2 } }), null);
});


test("an omitted placeholder on a plain int input normalizes to null", () => {
    assert.equal(placeholderOf({ kind: "int" }), null);
    assert.equal(placeholderOf({ kind: "int", options: { min: 0 } }), null);
});


test("choices carry no placeholder of their own", () => {
    assert.equal(placeholderOf({ kind: "str", options: { choices: ["a", "b"] } }),
                 null);
    assert.equal(placeholderOf({ kind: "int", options: { choices: [1, 2] } }),
                 null);
});


test("a custom placeholder survives on a plain input", () => {
    assert.equal(placeholderOf({ kind: "str", options: { placeholder: "Name" } }),
                 "Name");
});


test("an empty placeholder is an override, not an absence", () => {
    assert.equal(placeholderOf({ kind: "str", options: { placeholder: "" } }), "");
});
