import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { compileForm } from "./harness.mjs";
import { checkPlan } from "../../src/pytypehintweb/static/contract.js";
import { normalizeNode } from "../../src/pytypehintweb/static/normalize.js";
import { expandNode } from "./plan-fixture.mjs";
import { isValidIsoDate } from "../../src/pytypehintweb/static/iso.js";
import { DateWidget, TimeWidget } from "../../src/pytypehintweb/static/inputs.js";


function typeInto(widget, raw) {
    widget.input.value = raw;
    widget.input.dispatch("input");
}


// --- native controls, ISO values --------------------------------------------

test("a date widget is a native date input reading its ISO value", () => {
    const widget = new DateWidget();

    assert.equal(widget.input.tagName, "INPUT");
    assert.equal(widget.input.type, "date");

    typeInto(widget, "2026-07-22");
    assert.equal(widget.value(), "2026-07-22");
    assert.equal(widget.hasError(), false);
});


test("a time widget is a native time input with the seconds field open", () => {
    const widget = new TimeWidget();

    assert.equal(widget.input.type, "time");
    assert.equal(widget.input.getAttribute("step"), "1");

    typeInto(widget, "14:30:05");
    assert.equal(widget.value(), "14:30:05");
});


test("an empty control is incomplete but not invalid, and reads null", () => {
    for (const widget of [new DateWidget(), new TimeWidget()]) {
        assert.equal(widget.value(), null);
        assert.equal(widget.isEmpty(), true);
        assert.equal(widget.hasError(), false);
        assert.equal(widget.error(), null);
    }
});


test("native min and max are set for the picker", () => {
    const widget = new DateWidget({ min: "2026-01-01", max: "2026-12-31" });

    assert.equal(widget.input.getAttribute("min"), "2026-01-01");
    assert.equal(widget.input.getAttribute("max"), "2026-12-31");
});


// --- date bounds (inclusive) ------------------------------------------------

test("a date within inclusive bounds is valid, outside is flagged", () => {
    const widget = new DateWidget({ min: "2026-01-01", max: "2026-12-31" });

    typeInto(widget, "2026-01-01");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "2026-12-31");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "2025-12-31");
    assert.equal(widget.error(), "Must be on or after 2026-01-01");

    typeInto(widget, "2027-01-01");
    assert.equal(widget.error(), "Must be on or before 2026-12-31");
});


// --- time bounds (exclusive flag) -------------------------------------------

test("an exclusive time minimum rejects the boundary, accepts just past it", () => {
    const widget = new TimeWidget({ min: "09:00:00", minExclusive: true });

    typeInto(widget, "09:00:00");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be at or after 09:00:00");

    typeInto(widget, "09:00:01");
    assert.equal(widget.hasError(), false);
});


test("an inclusive time minimum accepts its own boundary", () => {
    const widget = new TimeWidget({ min: "09:00:00" });

    typeInto(widget, "09:00:00");
    assert.equal(widget.hasError(), false);
});


test("times compare lexicographically over the padded ISO form", () => {
    const widget = new TimeWidget({ min: "09:05:00" });

    // "14:30:00" > "09:05:00" as strings because the fixed-width padding makes
    // the string order match the clock order.
    typeInto(widget, "14:30:00");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "08:59:59");
    assert.equal(widget.error(), "Must be at or after 09:05:00");
});


// --- setValue ---------------------------------------------------------------

test("setValue applies a valid ISO string and reads it back", () => {
    const date = new DateWidget();
    let changes = 0;
    date.onChange(() => { changes += 1; });

    date.setValue("2026-07-22");
    assert.equal(date.value(), "2026-07-22");
    assert.equal(changes, 1);

    const time = new TimeWidget();
    time.setValue("14:30:00");
    assert.equal(time.value(), "14:30:00");
});


test("setValue(null) empties the control", () => {
    const widget = new DateWidget();

    widget.setValue("2026-07-22");
    widget.setValue(null);

    assert.equal(widget.value(), null);
    assert.equal(widget.isEmpty(), true);
});


test("setValue rejects a non-ISO string, a number and a boolean", () => {
    const date = new DateWidget();

    for (const bad of ["nope", "2026-7-2", "22/07/2026", 20260722, true]) {
        assert.throws(() => date.setValue(bad), /canonical ISO string or null/);
    }
});


// A time is whole seconds only (the domain pytypehint 0.0.6 pins), and the shape
// bounds each field, so setValue rejects a sub-second fraction and an impossible
// clock value alongside the wrong-shape strings.
test("setValue rejects any time that is not a valid HH:MM:SS", () => {
    const widget = new TimeWidget();

    for (const bad of [
        "12:30",            // no seconds
        "12:30:00.1",       // sub-second fraction
        "12:30:00.500000",  // six-digit fraction
        "24:00:00",         // hour out of range
        "12:60:00",         // minute out of range
        "12:30:60",         // second out of range
        "9:00", "09:00", "14h30",
    ]) {
        assert.throws(() => widget.setValue(bad), /canonical ISO string or null/);
    }
});


test("setValue accepts every valid HH:MM:SS, including the endpoints", () => {
    const widget = new TimeWidget();

    for (const good of ["12:30:00", "00:00:00", "23:59:59"]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
    }
});


// --- a picker that offers no seconds ----------------------------------------

// The node asks for step=1, which opens the seconds field on a desktop picker.
// iOS ignores it: its wheel picker has hours and minutes only and reports
// "HH:MM". Whole minutes are inside the domain, so the widget completes them
// rather than reading a perfectly chosen time as invalid.
test("a control that reports only HH:MM reads as whole seconds", () => {
    const widget = new TimeWidget();

    for (const [raw, value] of [["12:30", "12:30:00"], ["00:00", "00:00:00"],
                                ["23:59", "23:59:00"], ["09:05", "09:05:00"]]) {
        typeInto(widget, raw);
        assert.equal(widget.value(), value, `${raw} should read as ${value}`);
        assert.equal(widget.hasError(), false, `${raw} should be valid`);
    }
});


test("completing the seconds never rewrites what the control shows", () => {
    const widget = new TimeWidget();

    typeInto(widget, "12:30");

    assert.equal(widget.input.value, "12:30");
    assert.equal(widget.isEmpty(), false);
});


test("a control that does report seconds is left exactly as it is", () => {
    const widget = new TimeWidget();

    typeInto(widget, "12:30:45");
    assert.equal(widget.value(), "12:30:45");

    typeInto(widget, "12:30:00");
    assert.equal(widget.value(), "12:30:00");
});


test("an HH:MM value is compared against its bounds once completed", () => {
    const widget = new TimeWidget({ min: "09:00:00", max: "17:00:00" });

    typeInto(widget, "08:59");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be at or after 09:00:00");

    typeInto(widget, "09:00");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "17:00");
    assert.equal(widget.hasError(), false);

    typeInto(widget, "17:01");
    assert.equal(widget.error(), "Must be at or before 17:00:00");
});


test("an exclusive bound still rejects the boundary reached as HH:MM", () => {
    const widget = new TimeWidget({ min: "09:00:00", minExclusive: true });

    typeInto(widget, "09:00");
    assert.equal(widget.hasError(), true);
    assert.equal(widget.error(), "Must be at or after 09:00:00");
});


test("only a whole, in-range HH:MM is completed; nothing else is", () => {
    const widget = new TimeWidget();

    for (const bad of ["12:3", "1:30", "24:00", "12:60", "12:30:", "12h30",
                       "12:30:00.5", "12:30:60"]) {
        typeInto(widget, bad);
        assert.equal(widget.value(), bad, `${bad} should read back unchanged`);
        assert.equal(widget.hasError(), true, `${bad} should stay invalid`);
        assert.equal(widget.error(), "Enter a valid time");
    }
});


test("an HH:MM time transports as whole seconds through a compiled form", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{ name: "start", node: { kind: "time" } }],
    });

    typeInto(form.fields[0].widget.widget, "12:30");

    assert.equal(form.isReady(), true);
    assert.equal(form.read().start, "12:30:00");
});


test("a date control is untouched by the time completion", () => {
    const widget = new DateWidget();

    typeInto(widget, "2026-07");
    assert.equal(widget.value(), "2026-07");
    assert.equal(widget.hasError(), true);
});


// --- in a compiled form -----------------------------------------------------

test("a date default mounts prefilled and ready", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "day",
            hasDefault: true,
            default: "2026-07-22",
            node: { kind: "date", options: { min: "2026-01-01" } },
        }],
    });

    assert.equal(form.fields[0].widget.widget.value(), "2026-07-22");
    assert.equal(form.isReady(), true);
    assert.equal(form.read().day, "2026-07-22");
});


test("an optional time switched off reads as null", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "at",
            optional: true,
            enabled: false,
            node: { kind: "time" },
        }],
    });

    assert.equal(form.read().at, null);
    assert.equal(form.isReady(), true);
});


test("a date choice node mounts a select over ISO strings", () => {
    const form = compileForm({
        kind: "form",
        name: "f",
        fields: [{
            name: "season",
            node: { kind: "date", options: { choices: ["2026-03-20", "2026-06-21"] } },
        }],
    });

    const widget = form.fields[0].widget.widget;

    assert.equal(widget.value(), "2026-03-20");
    widget.setValue("2026-06-21");
    assert.equal(form.read().season, "2026-06-21");
});


// --- node normalization -----------------------------------------------------

test("the date node fills every documented option", () => {
    assert.deepEqual(normalizeNode(expandNode({ kind: "date" })), {
        kind: "date",
        options: {
            min: null,
            max: null,
            placeholder: null,
            choices: null,
            invalidMessage: "Enter a valid date",
            minMessage: "Must be on or after {value}",
            maxMessage: "Must be on or before {value}",
        },
    });
});


test("the time node fills every documented option, exclusivity included", () => {
    const options = normalizeNode(expandNode({ kind: "time" })).options;

    assert.equal(options.minExclusive, false);
    assert.equal(options.maxExclusive, false);
    assert.equal(options.invalidMessage, "Enter a valid time");
});


test("a non-ISO date bound is rejected structurally", () => {
    assert.throws(
        () => normalizeNode(expandNode({ kind: "date", options: { min: "2026-7-2" } })),
        /options\.min: expected an ISO date/);
});


test("a time bound that is not a valid HH:MM:SS is rejected structurally", () => {
    // A manual plan is held to the same whole-seconds domain: a fraction and an
    // impossible clock value are as invalid as the wrong shape.
    for (const bad of ["09:00", "09:00:00.500000", "24:00:00", "09:60:00"]) {
        assert.throws(
            () => normalizeNode(expandNode({ kind: "time", options: { max: bad } })),
            /options\.max: expected an ISO time/);
    }
});


test("a time choice that is not a valid HH:MM:SS is rejected structurally", () => {
    for (const bad of ["09:00", "09:00:00.500000", "24:00:00"]) {
        assert.throws(
            () => normalizeNode(expandNode({
                kind: "time", options: { choices: ["09:00:00", bad] } })),
            /choices\[1\]: expected an ISO time/);
    }
});


test("an unknown option and a missing option are both rejected", () => {
    assert.throws(
        () => normalizeNode(expandNode({ kind: "date", options: { step: 1 } })),
        /options\.step: unknown property/);

    assert.throws(
        () => normalizeNode({ kind: "time", options: { min: "09:00:00" } }),
        /options\.max: is required/);
});


// --- semantic checks (checkPlan) --------------------------------------------

function planWith(node) {
    return { v: 1, kind: "form", name: "f", description: null,
             fields: [{ name: "value", label: "v", description: null,
                        optional: false, enabled: true, hasDefault: false,
                        node }] };
}


test("checkPlan rejects an empty date range (min after max)", () => {
    const node = expandNode({
        kind: "date", options: { min: "2026-12-31", max: "2026-01-01" } });

    assert.throws(() => checkPlan(planWith(node)),
                  /min and max leave no representable value/);
});


test("checkPlan rejects equal time bounds when a side is exclusive", () => {
    const node = expandNode({
        kind: "time",
        options: { min: "09:00:00", max: "09:00:00", minExclusive: true } });

    assert.throws(() => checkPlan(planWith(node)),
                  /min and max leave no representable value/);
});


test("checkPlan accepts equal inclusive time bounds", () => {
    const node = expandNode({
        kind: "time", options: { min: "09:00:00", max: "09:00:00" } });

    assert.doesNotThrow(() => checkPlan(planWith(node)));
});


test("checkPlan rejects a time choice outside an exclusive bound", () => {
    const node = expandNode({
        kind: "time",
        options: { min: "09:00:00", minExclusive: true,
                   choices: ["09:00:00", "10:00:00"] } });

    assert.throws(() => checkPlan(planWith(node)),
                  /choices\[0\]: is before min 09:00:00/);
});


// --- a canonical date is a real calendar date -------------------------------
//
// The shape YYYY-MM-DD is necessary but not sufficient: 2026-02-31 matches it
// and no calendar holds it. A native date input blanks itself when handed such a
// value, so it is refused before it reaches the control.

const VALID_DATES = [
    "2026-01-01", "2026-02-28", "2026-04-30",
    "2024-02-29", "2000-02-29",            // leap years
    "0001-01-01", "0099-12-31", "0100-01-01", "9999-12-31",
];

const INVALID_DATES = [
    "2026-2-01", "2026-02-1", "+2026-01-01", "10000-01-01",  // shape
    "2026-02-29", "1900-02-29", "2026-02-30", "2026-02-31",  // calendar
    "2026-04-31", "2026-00-10", "2026-13-01", "0000-01-01",
];


test("isValidIsoDate accepts exactly the real calendar dates", () => {
    for (const good of VALID_DATES) {
        assert.equal(isValidIsoDate(good), true, `${good} should be valid`);
    }

    for (const bad of INVALID_DATES) {
        assert.equal(isValidIsoDate(bad), false, `${bad} should be invalid`);
    }
});


test("a year below 100 keeps its own century", () => {
    // Date.UTC maps years 0..99 onto 1900 + year, so a naive round trip would
    // read 0001-01-01 back as 1901 and refuse a legitimate date.
    for (const good of ["0001-01-01", "0050-06-15", "0099-12-31"]) {
        assert.equal(isValidIsoDate(good), true, `${good} should be valid`);
    }
});


test("a non-string is never a canonical date", () => {
    for (const bad of [null, undefined, 20260101, true, {}, ["2026-01-01"]]) {
        assert.equal(isValidIsoDate(bad), false);
    }
});


test("an impossible date default is rejected before any widget exists", () => {
    const plan = {
        v: 1, kind: "form", name: "f", description: null,
        fields: [{
            name: "day", label: "d", description: null,
            optional: false, enabled: true, hasDefault: true,
            default: "2026-02-31", node: expandNode({ kind: "date" }),
        }],
    };

    assert.throws(() => checkPlan(plan), /expected an ISO date for date node/);
});


test("an impossible date bound is rejected structurally", () => {
    for (const bad of ["2026-13-01", "2026-04-31", "0000-01-01"]) {
        assert.throws(
            () => normalizeNode(expandNode({ kind: "date", options: { min: bad } })),
            /options\.min: expected an ISO date/);

        assert.throws(
            () => normalizeNode(expandNode({ kind: "date", options: { max: bad } })),
            /options\.max: expected an ISO date/);
    }
});


test("an impossible date choice is rejected structurally", () => {
    assert.throws(
        () => normalizeNode(expandNode({
            kind: "date", options: { choices: ["2026-01-01", "2026-02-30"] } })),
        /choices\[1\]: expected an ISO date/);
});


test("setValue refuses an impossible date and keeps the previous value", () => {
    const widget = new DateWidget();

    widget.setValue("2026-02-28");

    for (const bad of ["2026-02-31", "2026-13-01", "0000-01-01"]) {
        assert.throws(() => widget.setValue(bad), /canonical ISO string or null/);
        assert.equal(widget.value(), "2026-02-28");
    }
});


test("setValue accepts every real calendar date, leap day and edges included", () => {
    const widget = new DateWidget();

    for (const good of ["2024-02-29", "0001-01-01", "9999-12-31"]) {
        widget.setValue(good);
        assert.equal(widget.value(), good);
    }
});


test("a direct initial impossible date is reported invalid, never silently valid", () => {
    const widget = new DateWidget({ value: "2026-02-31" });

    assert.equal(widget.hasError(), true);
    assert.equal(widget.isReady(), false);
});


test("a real date is still judged against its bounds", () => {
    const widget = new DateWidget({ min: "2026-01-01", max: "2026-12-31" });

    // A real leap day, but before min: valid as a date, out of range as a value.
    typeInto(widget, "2024-02-29");
    assert.equal(widget.error(), "Must be on or after 2026-01-01");

    typeInto(widget, "2026-02-28");
    assert.equal(widget.hasError(), false);

    // An impossible date is invalid on its own terms, before any comparison.
    typeInto(widget, "2026-02-31");
    assert.equal(widget.error(), "Enter a valid date");
});
