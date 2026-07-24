import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { checkPlan, compileForm } from "./harness.mjs";
import { StrWidget } from "../../src/pytypehintweb/static/inputs.js";


function planWith(node) {
    return { v: 1, kind: "form", name: "x", fields: [{ name: "value", node }] };
}


test("an ordinary string input has neither pattern nor title", () => {
    const widget = new StrWidget();

    assert.equal(widget.input.getAttribute("pattern"), null);
    assert.equal(widget.input.getAttribute("title"), null);
});


test("a pattern string input writes a title but never a native pattern", () => {
    // The library validates patterns with its own compiled RegExp; the native
    // HTML pattern attribute is deliberately not written so the browser's
    // constraint-validation UI does not compete. The title remains as help text.
    const widget = new StrWidget({
        pattern: "[a-z]+",
        patternMessage: "lowercase letters only",
    });

    assert.equal(widget.input.getAttribute("pattern"), null);
    assert.equal(widget.input.getAttribute("title"), "lowercase letters only");
    assert.equal(widget.matchesPattern(), false);

    widget.input.value = "abc";
    assert.equal(widget.matchesPattern(), true);
});


test("a pattern textarea validates but writes no native pattern attribute", () => {
    const widget = new StrWidget({ pattern: "[a-z]+", rows: 3 });

    assert.equal(widget.input.tagName, "TEXTAREA");
    assert.equal(widget.input.getAttribute("pattern"), null);

    widget.input.value = "AB1";
    assert.equal(widget.matchesPattern(), false);

    widget.input.value = "abc";
    assert.equal(widget.matchesPattern(), true);
});


test("an invalid pattern without choices fails in checkPlan", () => {
    assert.throws(
        () => checkPlan(planWith({ kind: "str", options: { pattern: "(unclosed" } })),
        /options\.pattern: invalid regular expression/);
});


test("an invalid pattern with choices fails in checkPlan", () => {
    assert.throws(
        () => checkPlan(planWith({
            kind: "str",
            options: { pattern: "(unclosed", choices: ["a"] },
        })),
        /options\.pattern: invalid regular expression/);
});


test("a valid pattern builds a form", () => {
    assert.doesNotThrow(
        () => compileForm(planWith({ kind: "str", options: { pattern: "[a-z]+" } })));
});


test("a directly constructed widget throws on an uncompilable pattern", () => {
    // A pattern is programmer configuration, not a live user value. Like the
    // other constructor argument checks, misuse throws a TypeError at once
    // rather than mounting a permanently invalid widget — the same verdict
    // checkPlan reaches for a plan, and what the direct-construction docs promise.
    for (const bad of ["[", "(unclosed", "a{2,1}", "(?<"]) {
        assert.throws(() => new StrWidget({ pattern: bad }), TypeError);
    }
});


test("a valid pattern carries no construction-time error into its live state", () => {
    // The removed patternError path used to surface a compile message before the
    // user touched the field; a compilable pattern must never do that.
    const widget = new StrWidget({ pattern: "[0-9]+" });

    widget.setValue("12");
    assert.equal(widget.error(), null);
    assert.equal(widget.hasError(), false);

    widget.setValue("ab");
    assert.equal(widget.error(), "Invalid format");
});


test("checkPlan does not leak the native regex exception", () => {
    try {
        checkPlan(planWith({ kind: "str", options: { pattern: "(unclosed" } }));
        assert.fail("expected checkPlan to throw");
    } catch (error) {
        assert.match(error.message, /pattern: invalid regular expression/);
        assert.ok(!/SyntaxError|Invalid regular expression:/.test(error.message),
                  "the native engine message must not leak");
    }
});
