import "./dom.mjs";

import test from "node:test";
import assert from "node:assert/strict";

import { type } from "./dom.mjs";
import { compileForm } from "./harness.mjs";
import { normalizeField } from "../../src/pytypehintweb/static/normalize.js";
import { checkPlan as realCheckPlan } from "../../src/pytypehintweb/static/contract.js";


// A field name is any non-empty string (docs/plan.md: "name must be a non-empty
// string"), so a manual plan may name a field "__proto__". Building the
// transport object with a plain result[name] = value would trigger the
// Object.prototype __proto__ setter and silently drop the field; these pin that
// every declared name survives value()/read() and JSON transport.

function widgetOf(form, name) {
    return form.fields.find((field) => field.name === name).widget.widget;
}


test('a field named "__proto__" survives read() and JSON transport', () => {
    const form = compileForm({
        v: 1, kind: "form", name: "example",
        fields: [
            { name: "name", node: { kind: "str", options: {} } },
            { name: "__proto__", node: { kind: "str", options: {} } },
        ],
    }, { prefix: "proto" });

    type(widgetOf(form, "name"), "Ana");
    type(widgetOf(form, "__proto__"), "SECRETO");

    const out = form.read();

    assert.ok(Object.prototype.hasOwnProperty.call(out, "__proto__"),
              "the __proto__ field must be an own property, not the prototype");
    assert.equal(out["__proto__"], "SECRETO");
    assert.deepEqual(Object.keys(out), ["name", "__proto__"]);
    assert.equal(JSON.parse(JSON.stringify(out))["__proto__"], "SECRETO");
});


test('a nested object field named "__proto__" survives read()', () => {
    const form = compileForm({
        v: 1, kind: "form", name: "example",
        fields: [
            {
                name: "outer",
                node: {
                    kind: "object",
                    fields: [
                        { name: "ok", node: { kind: "str", options: {} } },
                        { name: "__proto__", node: { kind: "str", options: {} } },
                    ],
                },
            },
        ],
    }, { prefix: "proto-nested" });

    const group = widgetOf(form, "outer");
    type(group.children[0].widget.widget, "A");
    type(group.children[1].widget.widget, "B");

    const out = form.read();

    assert.equal(out.outer["__proto__"], "B");
    assert.deepEqual(Object.keys(out.outer), ["ok", "__proto__"]);
    // value() on the container is affected by the same setter and must agree.
    assert.equal(group.value()["__proto__"], "B");
});


// A real plan arrives via JSON.parse, where "__proto__" is an own data
// property (JSON.parse never invokes the setter). A JS object literal would set
// the prototype instead, so these build the default from JSON text to mirror
// transport faithfully.
test('a plan default keyed "__proto__" is preserved by normalization', () => {
    const opts = JSON.stringify(strOptions());
    const field = normalizeField(JSON.parse(`{
        "name": "outer", "label": "outer", "description": null,
        "optional": false, "enabled": true, "hasDefault": true,
        "default": { "ok": "A", "__proto__": "B" },
        "node": { "kind": "object", "fields": [
            { "name": "ok", "label": "ok", "description": null,
              "optional": false, "enabled": true, "hasDefault": false,
              "node": { "kind": "str", "options": ${opts} } },
            { "name": "__proto__", "label": "p", "description": null,
              "optional": false, "enabled": true, "hasDefault": false,
              "node": { "kind": "str", "options": ${opts} } }
        ]}
    }`));

    assert.equal(field.default["__proto__"], "B");
    assert.deepEqual(Object.keys(field.default), ["ok", "__proto__"]);
});


test('a default keyed "__proto__" round-trips through compileForm().read()', () => {
    const plan = JSON.parse(`{
        "v": 1, "kind": "form", "name": "example", "description": null,
        "fields": [{
            "name": "outer", "label": "outer", "description": null,
            "optional": false, "enabled": true, "hasDefault": true,
            "default": { "ok": "A", "__proto__": "B" },
            "node": { "kind": "object", "fields": [
                { "name": "ok", "node": { "kind": "str", "options": {} } },
                { "name": "__proto__", "node": { "kind": "str", "options": {} } }
            ]}
        }]
    }`);

    const compiled = compileForm(plan, { prefix: "proto-default" });

    assert.equal(compiled.read().outer["__proto__"], "B");
});


// "$type" and "$value" are the reserved keys of the discriminated transport. A
// field carrying either overwrites the discriminator (an inline branch spreads
// its object next to $type) or is misread as a wrapped payload ($value), so the
// contract must reject them rather than emit an unroutable object.
for (const reserved of ["$type", "$value"]) {
    test(`a field named "${reserved}" is rejected by the contract`, () => {
        assert.throws(
            () => normalizeField({
                name: reserved, label: reserved, description: null,
                optional: false, enabled: true, hasDefault: false,
                node: { kind: "str", options: strOptions() },
            }),
            /reserved by the transport/);
    });

    test(`a nested object field named "${reserved}" is rejected`, () => {
        const plan = {
            v: 1, kind: "form", name: "example", description: null,
            fields: [{
                name: "outer", label: "outer", description: null,
                optional: false, enabled: true, hasDefault: false,
                node: {
                    kind: "object",
                    fields: [{
                        name: reserved, label: reserved, description: null,
                        optional: false, enabled: true, hasDefault: false,
                        node: { kind: "str", options: strOptions() },
                    }],
                },
            }],
        };

        assert.throws(() => realCheckPlan(plan), /reserved by the transport/);
    });
}


test('a $type field inside an inline union branch is rejected (no discriminator clash)', () => {
    const plan = {
        v: 1, kind: "form", name: "example", description: null,
        fields: [{
            name: "u", label: "u", description: null, optional: false,
            enabled: true, hasDefault: false,
            node: {
                kind: "choice", previousLabel: "p", nextLabel: "n",
                positionLabel: "{current}/{total}",
                branches: [
                    { value: "A", mode: "inline", node: { kind: "object", fields: [
                        { name: "$type", label: "$type", description: null,
                          optional: false, enabled: true, hasDefault: false,
                          node: { kind: "str", options: strOptions() } },
                    ] } },
                    { value: "B", mode: "inline", node: { kind: "object", fields: [
                        { name: "y", label: "y", description: null,
                          optional: false, enabled: true, hasDefault: false,
                          node: { kind: "str", options: strOptions() } },
                    ] } },
                ],
            },
        }],
    };

    assert.throws(() => realCheckPlan(plan), /reserved by the transport/);
});


function strOptions() {
    return {
        minLength: null, maxLength: null, pattern: null,
        patternMessage: "Invalid format", minMessage: "min {value}",
        maxMessage: "max {value}", placeholder: null, password: false,
        rows: null, choices: null,
    };
}
