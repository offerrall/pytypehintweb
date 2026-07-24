import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type } from "./dom.mjs";
import { ListWidget } from "../../src/pytypehintweb/static/fields.js";
import { StrWidget } from "../../src/pytypehintweb/static/inputs.js";


function stringList() {
    return new ListWidget(() => new StrWidget(), []);
}


test("adding one row emits exactly one change event", () => {
    const list = stringList();

    let changes = 0;
    list.onChange(() => { changes += 1; });

    list.add();

    assert.equal(changes, 1);
});


test("removing a row releases the item's subscription", () => {
    const list = stringList();
    const widget = list.add();

    let changes = 0;
    list.onChange(() => { changes += 1; });

    list.remove(list.items[0]);

    const afterRemoval = changes;

    type(widget, "orphaned");

    assert.equal(changes, afterRemoval);
});


test("onChange still rejects a non-function on a container and a scalar", () => {
    assert.throws(() => stringList().onChange("nope"), /must be a function/);
    assert.throws(() => new StrWidget().onChange(null), /must be a function/);
});


test("the unsubscribe function is idempotent", () => {
    const list = stringList();

    let changes = 0;
    const off = list.onChange(() => { changes += 1; });

    off();
    off();

    list.add();

    assert.equal(changes, 0);
});


test("the constructor rejects more initial values than maxItems allows", () => {
    // Silent truncation would drop "c" and "d": constructing by hand is normal
    // use, so an unhonourable argument throws rather than losing data.
    assert.throws(
        () => new ListWidget(() => new StrWidget(), ["a", "b", "c", "d"],
                             { maxItems: 2 }),
        /ListWidget initial values must not exceed maxItems/);
});


test("the constructor accepts exactly maxItems initial values", () => {
    const list = new ListWidget(() => new StrWidget(), ["a", "b"],
                                { maxItems: 2 });

    assert.equal(list.items.length, 2);
    assert.equal(list.canAdd(), false);            // born full
});


test("interactive add() on a full list still returns null without throwing", () => {
    const list = new ListWidget(() => new StrWidget(), ["a", "b"],
                                { maxItems: 2 });

    // An impossible UI action (the add button is disabled) is ignored, not an
    // error: silence is only wrong when it swallows data it was handed.
    assert.equal(list.add(), null);
    assert.equal(list.items.length, 2);
});
