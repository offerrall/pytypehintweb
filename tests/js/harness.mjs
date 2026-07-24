// Test harness: wraps the real entry points so behavioural tests can author
// compact plans while the product itself accepts only fully expanded ones.
// expandPlan() stands in for a producer (plan_of), filling every mandatory
// property with its documented default and forcing the current contract
// version. Tests that assert structural rejection import the real functions
// directly instead of this module.

import { compileForm as realCompileForm } from "../../src/pytypehintweb/static/form.js";
import { checkPlan as realCheckPlan } from "../../src/pytypehintweb/static/contract.js";
import { expandPlan } from "./plan-fixture.mjs";


export function compileForm(plan, options) {
    return realCompileForm(expandPlan(plan), options);
}


export function checkPlan(plan) {
    return realCheckPlan(expandPlan(plan));
}
