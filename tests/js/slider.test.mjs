import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { sliderReaches as sliderReachesFromContract }
    from "../../src/pytypehintweb/static/contract.js";
import { firstSliderValue, sliderReaches }
    from "../../src/pytypehintweb/static/slider.js";
import { IntWidget } from "../../src/pytypehintweb/static/inputs.js";

const CASES = JSON.parse(readFileSync(
    fileURLToPath(new URL("../fixtures/slider_cases.json", import.meta.url)),
    "utf-8"));


function bruteForce(min, max, step, multipleOf) {
    for (let v = min; v <= max; v += step) {
        if (((v % multipleOf) + multipleOf) % multipleOf === 0) {
            return true;
        }
    }

    return false;
}


function bruteFirst(min, max, step, multipleOf) {
    for (let v = min; v <= max; v += step) {
        if (((v % multipleOf) + multipleOf) % multipleOf === 0) {
            return v;
        }
    }

    return null;
}


test("contract.js re-exports the shared sliderReaches solver", () => {
    assert.equal(sliderReachesFromContract, sliderReaches);
});


test("firstSliderValue matches the shared parity vectors", () => {
    for (const c of CASES) {
        assert.equal(
            firstSliderValue(c.minimum, c.maximum, c.step, c.multipleOf),
            c.first, c.name);
    }
});


test("sliderReaches agrees with firstSliderValue on every vector", () => {
    for (const c of CASES) {
        const first = firstSliderValue(c.minimum, c.maximum, c.step, c.multipleOf);

        assert.equal(sliderReaches(c.minimum, c.maximum, c.step, c.multipleOf),
                     first !== null, c.name);
        assert.equal(first !== null, c.reachable, c.name);
    }
});


test("the huge-range case is solved by arithmetic, not by scanning", () => {
    // min 1, max 9007199254740991, step 1, multipleOf 9007199254740991: the
    // only valid position is the maximum. A linear scan would need ~9e15
    // iterations and hang; direct arithmetic returns at once.
    const max = 9007199254740991;

    assert.equal(firstSliderValue(1, max, 1, max), max);
    // max is odd, so an even stride from an even start never lands on it.
    assert.equal(firstSliderValue(2, max, 2, max), null);
    assert.equal(sliderReaches(1, max, 1, max), true);
});


test("firstSliderValue matches brute force on small bounded cases", () => {
    let checked = 0;

    for (let min = -6; min <= 6; min += 1) {
        for (let max = min; max <= min + 12; max += 1) {
            for (let step = 1; step <= 6; step += 1) {
                for (let mult = 1; mult <= 6; mult += 1) {
                    assert.equal(firstSliderValue(min, max, step, mult),
                                 bruteFirst(min, max, step, mult),
                                 `min=${min} max=${max} step=${step} mult=${mult}`);
                    checked += 1;
                }
            }
        }
    }

    assert.ok(checked > 5000);
});


test("sliderReaches equals brute force on small bounded cases", () => {
    let checked = 0;

    for (let min = -6; min <= 6; min += 1) {
        for (let max = min; max <= min + 12; max += 1) {
            for (let step = 1; step <= 6; step += 1) {
                for (let multipleOf = 1; multipleOf <= 6; multipleOf += 1) {
                    assert.equal(
                        sliderReaches(min, max, step, multipleOf),
                        bruteForce(min, max, step, multipleOf),
                        `min=${min} max=${max} step=${step} mult=${multipleOf}`);
                    checked += 1;
                }
            }
        }
    }

    assert.ok(checked > 5000);
});


test("a slider with no default starts on the first reachable value", () => {
    const widget = new IntWidget({
        slider: true, min: 1, max: 20, step: 1, multipleOf: 5,
    });

    assert.equal(widget.value(), 5);
});


test("an explicit slider default wins over the first reachable value", () => {
    const widget = new IntWidget({
        slider: true, min: 1, max: 20, step: 1, multipleOf: 5, value: 15,
    });

    assert.equal(widget.value(), 15);
});


test("a negative-range slider starts on a reachable, valid position", () => {
    const widget = new IntWidget({
        slider: true, min: -8, max: 8, step: 1, multipleOf: 3,
    });

    assert.equal(widget.value(), -6);
});


test("a non-coprime step and multiple start on a reachable position", () => {
    const widget = new IntWidget({
        slider: true, min: 2, max: 40, step: 4, multipleOf: 6,
    });

    const start = widget.value();

    assert.ok(start >= 2 && start <= 40);
    assert.equal((start - 2) % 4, 0);
    assert.equal(start % 6, 0);
});


test("a huge-range slider constructs at once on its only valid value", () => {
    const max = 9007199254740991;
    const widget = new IntWidget({
        slider: true, min: 1, max, step: 1, multipleOf: max,
    });

    assert.equal(widget.value(), max);
});


test("a slider with no reachable multiple is rejected at construction", () => {
    assert.throws(
        () => new IntWidget({
            slider: true, min: 1, max: 9, step: 4, multipleOf: 10,
        }),
        /no reachable position/);
});


// --- a slider refuses what a range input would silently adjust --------------
//
// A native <input type="range"> clamps a value outside min/max and snaps one
// off its step grid, so writing such a value leaves the control holding a
// number nobody asked for. setValue refuses before writing; the grid rule is
// onSliderGrid, shared with checkPlan rather than reimplemented here.

function slider(options) {
    return new IntWidget({ slider: true, ...options });
}


test("a slider accepts every value on its grid", () => {
    const widget = slider({ min: 0, max: 10, step: 2 });

    for (const good of [0, 2, 4, 6, 8, 10]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
    }
});


test("a slider refuses a value off its grid and keeps the previous one", () => {
    const widget = slider({ min: 0, max: 10, step: 2 });

    widget.setValue(4);

    for (const bad of [1, 3, 5, 9]) {
        assert.throws(() => widget.setValue(bad), /not on the grid/);
        assert.equal(widget.value(), 4);
    }
});


test("a slider refuses a value outside its bounds and keeps the previous one", () => {
    const widget = slider({ min: 0, max: 10, step: 2 });

    widget.setValue(4);

    for (const bad of [-2, 12, 100]) {
        assert.throws(() => widget.setValue(bad), /outside 0\.\.10/);
        assert.equal(widget.value(), 4);
    }
});


test("the grid starts at the minimum, negative bounds included", () => {
    const widget = slider({ min: -5, max: 10, step: 3 });

    for (const good of [-5, -2, 1, 4, 7, 10]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
    }

    widget.setValue(1);

    for (const bad of [-4, 0, 2, -3]) {
        assert.throws(() => widget.setValue(bad), /not on the grid/);
        assert.equal(widget.value(), 1);
    }
});


test("a slider with no explicit step steps by one", () => {
    const widget = slider({ min: 0, max: 5 });

    for (const good of [0, 1, 2, 3, 4, 5]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
    }

    assert.throws(() => widget.setValue(6), /outside 0\.\.5/);
});


test("an ordinary integer input keeps carrying an out-of-bounds value", () => {
    // The opposite contract, unchanged: a text input represents what was typed
    // or assigned and reports the breach through error().
    const widget = new IntWidget({ min: 0, max: 10 });

    widget.setValue(99);

    assert.equal(widget.value(), 99);
    assert.equal(widget.error(), "Must be at most 10");
});
