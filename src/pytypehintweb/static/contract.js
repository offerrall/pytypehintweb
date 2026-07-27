import { isValidIsoDate } from "./iso.js";
import { ISO_TIME, fail, normalizePlan } from "./normalize.js";
import { onSliderGrid, sliderReaches } from "./slider.js";

export { sliderReaches } from "./slider.js";


function checkChoices(value, path) {
    if (value === null) {
        return;
    }

    if (value.length === 0) {
        fail(path, "expected a non-empty array");
    }

    const seen = new Set();

    value.forEach((choice, i) => {
        if (seen.has(choice)) {
            fail(`${path}[${i}]`, "duplicated choice");
        }

        seen.add(choice);
    });
}


const PLACEHOLDER = /\{[^{}]*\}/g;


function placeholders(value, path) {
    if (/[{}]/.test(value.replace(PLACEHOLDER, ""))) {
        fail(path, "has unbalanced braces");
    }

    return value.match(PLACEHOLDER) ?? [];
}


function checkTemplate(value, path, needsValue) {
    const found = placeholders(value, path);

    if (!needsValue) {
        if (found.length > 0) {
            fail(path, "must not contain placeholders");
        }
        return;
    }

    if (found.length !== 1 || found[0] !== "{value}") {
        fail(path,
             "must contain exactly one {value} placeholder and no other placeholders");
    }
}


function checkPositionTemplate(value, path) {
    const found = placeholders(value, path);

    if (found.length !== 2
            || !found.includes("{current}")
            || !found.includes("{total}")) {
        fail(path,
             "must contain exactly one {current} and one {total} placeholder");
    }
}


function checkLabel(value, path) {
    if (value === "") {
        fail(path, "must not be empty");
    }

    checkTemplate(value, path, false);
}


function checkFieldNames(fields, path) {
    const seen = new Set();

    fields.forEach((field, i) => {
        if (seen.has(field.name)) {
            fail(`${path}[${i}].name`, "duplicated field name");
        }

        seen.add(field.name);
    });
}


function stringLength(value) {
    return Array.from(value).length;
}


function checkSlider(options, path) {
    if (!options.slider) {
        return;
    }

    if (options.min === null || options.max === null) {
        fail(`${path}.options`, "slider needs both min and max");
    }

    if (options.multipleOf === null) {
        return;
    }

    const step = options.step === null ? 1 : options.step;

    if (!sliderReaches(options.min, options.max, step, options.multipleOf)) {
        fail(`${path}.options`,
             `no slider position between ${options.min} and ${options.max} `
             + `stepping by ${step} is a multiple of ${options.multipleOf}`);
    }
}


function compilePattern(pattern, path) {
    try {
        return new RegExp(`^(?:${pattern})$`, "u");
    } catch {
        fail(path, "invalid regular expression");
    }

    return null;
}


function checkStringChoices(options, regexp, path) {
    if (options.choices === null) {
        return;
    }

    options.choices.forEach((choice, i) => {
        const at = `${path}.options.choices[${i}]`;
        const length = stringLength(choice);

        if (options.minLength !== null && length < options.minLength) {
            fail(at, `is shorter than minLength ${options.minLength}`);
        }

        if (options.maxLength !== null && length > options.maxLength) {
            fail(at, `is longer than maxLength ${options.maxLength}`);
        }

        if (regexp !== null && !regexp.test(choice)) {
            fail(at, "does not match the declared pattern");
        }
    });
}


function checkIntChoices(options, path) {
    if (options.choices === null) {
        return;
    }

    options.choices.forEach((choice, i) => {
        const at = `${path}.options.choices[${i}]`;

        if (options.min !== null && choice < options.min) {
            fail(at, `is below min ${options.min}`);
        }

        if (options.max !== null && choice > options.max) {
            fail(at, `is above max ${options.max}`);
        }

        if (options.multipleOf !== null && choice % options.multipleOf !== 0) {
            fail(at, `is not a multiple of ${options.multipleOf}`);
        }
    });
}


function checkFloatChoices(options, path) {
    if (options.choices === null) {
        return;
    }

    options.choices.forEach((choice, i) => {
        const at = `${path}.options.choices[${i}]`;

        if (options.min !== null) {
            const below = options.minExclusive
                ? choice <= options.min
                : choice < options.min;

            if (below) {
                fail(at, `is below min ${options.min}`);
            }
        }

        if (options.max !== null) {
            const above = options.maxExclusive
                ? choice >= options.max
                : choice > options.max;

            if (above) {
                fail(at, `is above max ${options.max}`);
            }
        }
    });
}


function checkStrNode(node, path) {
    const options = node.options;

    checkTemplate(options.patternMessage, `${path}.options.patternMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkChoices(options.choices, `${path}.options.choices`);

    if (options.minLength !== null && options.maxLength !== null
            && options.minLength > options.maxLength) {
        fail(`${path}.options.minLength`, "must not exceed maxLength");
    }

    if (options.choices !== null && options.password) {
        fail(`${path}.options`, "choices and password ask for different controls");
    }

    if (options.choices !== null && options.rows !== null) {
        fail(`${path}.options`, "choices and rows ask for different controls");
    }

    if (options.choices !== null && options.placeholder !== null) {
        fail(`${path}.options`,
             "choices and placeholder ask for different controls");
    }

    if (options.rows !== null && options.password) {
        fail(`${path}.options`, "rows and password ask for different controls");
    }

    const regexp = options.pattern === null
        ? null
        : compilePattern(options.pattern, `${path}.options.pattern`);

    checkStringChoices(options, regexp, path);
}


function checkIntNode(node, path) {
    const options = node.options;

    checkTemplate(options.safeMessage, `${path}.options.safeMessage`, false);
    checkTemplate(options.invalidMessage, `${path}.options.invalidMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkTemplate(options.multipleOfMessage,
                  `${path}.options.multipleOfMessage`, true);
    checkLabel(options.increaseLabel, `${path}.options.increaseLabel`);
    checkLabel(options.decreaseLabel, `${path}.options.decreaseLabel`);
    checkChoices(options.choices, `${path}.options.choices`);

    if (options.min !== null && options.max !== null
            && options.min > options.max) {
        fail(`${path}.options.min`, "must not exceed max");
    }

    if (options.choices !== null && options.slider) {
        fail(`${path}.options`, "choices and slider ask for different controls");
    }

    if (options.choices !== null && options.placeholder !== null) {
        fail(`${path}.options`,
             "choices and placeholder ask for different controls");
    }

    if (options.slider && options.placeholder !== null) {
        fail(`${path}.options`,
             "slider and placeholder ask for different controls");
    }

    checkSlider(options, path);
    checkIntChoices(options, path);
}


function checkFloatNode(node, path) {
    const options = node.options;

    checkTemplate(options.invalidMessage, `${path}.options.invalidMessage`, false);
    checkTemplate(options.finiteMessage, `${path}.options.finiteMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkLabel(options.increaseLabel, `${path}.options.increaseLabel`);
    checkLabel(options.decreaseLabel, `${path}.options.decreaseLabel`);
    checkChoices(options.choices, `${path}.options.choices`);

    if (options.min !== null && options.max !== null) {
        const empty = options.min > options.max
            || (options.min === options.max
                && (options.minExclusive || options.maxExclusive));

        if (empty) {
            fail(`${path}.options.min`,
                 "min and max leave no representable value");
        }
    }

    if (options.choices !== null && options.placeholder !== null) {
        fail(`${path}.options`,
             "choices and placeholder ask for different controls");
    }

    checkFloatChoices(options, path);
}


function checkIsoChoices(options, path) {
    if (options.choices === null) {
        return;
    }

    options.choices.forEach((choice, i) => {
        const at = `${path}.options.choices[${i}]`;

        if (options.min !== null) {
            const below = options.minExclusive === true
                ? choice <= options.min
                : choice < options.min;

            if (below) {
                fail(at, `is before min ${options.min}`);
            }
        }

        if (options.max !== null) {
            const above = options.maxExclusive === true
                ? choice >= options.max
                : choice > options.max;

            if (above) {
                fail(at, `is after max ${options.max}`);
            }
        }
    });
}


function checkDateNode(node, path) {
    const options = node.options;

    checkTemplate(options.invalidMessage, `${path}.options.invalidMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkChoices(options.choices, `${path}.options.choices`);

    if (options.min !== null && options.max !== null && options.min > options.max) {
        fail(`${path}.options.min`, "min and max leave no representable value");
    }

    if (options.choices !== null && options.placeholder !== null) {
        fail(`${path}.options`,
             "choices and placeholder ask for different controls");
    }

    checkIsoChoices(options, path);
}


function checkTimeNode(node, path) {
    const options = node.options;

    checkTemplate(options.invalidMessage, `${path}.options.invalidMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkChoices(options.choices, `${path}.options.choices`);

    if (options.min !== null && options.max !== null) {
        const empty = options.min > options.max
            || (options.min === options.max
                && (options.minExclusive || options.maxExclusive));

        if (empty) {
            fail(`${path}.options.min`,
                 "min and max leave no representable value");
        }
    }

    if (options.choices !== null && options.placeholder !== null) {
        fail(`${path}.options`,
             "choices and placeholder ask for different controls");
    }

    checkIsoChoices(options, path);
}


function checkFileNode(node, path) {
    const options = node.options;

    checkTemplate(options.invalidMessage, `${path}.options.invalidMessage`, false);
    checkTemplate(options.minMessage, `${path}.options.minMessage`, true);
    checkTemplate(options.maxMessage, `${path}.options.maxMessage`, true);
    checkTemplate(options.currentLabel, `${path}.options.currentLabel`, true);
    checkLabel(options.currentRemoveLabel, `${path}.options.currentRemoveLabel`);
    checkLabel(options.currentReplaceLabel, `${path}.options.currentReplaceLabel`);
    checkLabel(options.currentRestoreLabel, `${path}.options.currentRestoreLabel`);

    if (options.minFiles !== null && options.maxFiles !== null
            && options.minFiles > options.maxFiles) {
        fail(`${path}.options.minFiles`, "must not exceed maxFiles");
    }

    if (!options.multiple
            && (options.minFiles !== null || options.maxFiles !== null)) {
        fail(`${path}.options`,
             "minFiles and maxFiles require a multiple file node");
    }
}


function checkNode(node, path) {
    if (node.kind === "str") {
        checkStrNode(node, path);
        return;
    }

    if (node.kind === "file") {
        checkFileNode(node, path);
        return;
    }

    if (node.kind === "int") {
        checkIntNode(node, path);
        return;
    }

    if (node.kind === "float") {
        checkFloatNode(node, path);
        return;
    }

    if (node.kind === "date") {
        checkDateNode(node, path);
        return;
    }

    if (node.kind === "time") {
        checkTimeNode(node, path);
        return;
    }

    if (node.kind === "bool") {
        return;
    }

    if (node.kind === "enum") {
        return;
    }

    if (node.kind === "list") {
        if (node.minItems !== null && node.maxItems !== null
                && node.minItems > node.maxItems) {
            fail(`${path}.minItems`, "must not exceed maxItems");
        }

        checkLabel(node.addLabel, `${path}.addLabel`);
        checkLabel(node.removeLabel, `${path}.removeLabel`);
        checkTemplate(node.minMessage, `${path}.minMessage`, true);
        checkTemplate(node.maxMessage, `${path}.maxMessage`, true);
        checkNode(node.item, `${path}.item`);
        return;
    }

    if (node.kind === "object") {
        if (node.fields.length === 0) {
            fail(`${path}.fields`, "expected a non-empty array");
        }

        checkFieldNames(node.fields, `${path}.fields`);
        node.fields.forEach((field, i) => checkField(field, `${path}.fields[${i}]`));
        return;
    }

    if (node.kind === "choice") {
        checkLabel(node.previousLabel, `${path}.previousLabel`);
        checkLabel(node.nextLabel, `${path}.nextLabel`);
        checkPositionTemplate(node.positionLabel, `${path}.positionLabel`);

        if (node.branches.length < 2) {
            fail(`${path}.branches`,
                 "expected at least two branches; a single branch is the node "
                 + "itself");
        }

        const seen = new Set();

        node.branches.forEach((branch, i) => {
            const at = `${path}.branches[${i}]`;

            if (seen.has(branch.value)) {
                fail(`${at}.value`, "duplicated branch value");
            }

            if (branch.mode === "inline" && branch.node.kind !== "object") {
                fail(`${at}.mode`, "inline requires an object node");
            }

            seen.add(branch.value);
            checkNode(branch.node, `${at}.node`);
        });
        return;
    }

    checkLabel(node.label, `${path}.label`);
    checkNode(node.node, `${path}.node`);
}


function checkStrDefault(options, value, path) {
    const length = stringLength(value);

    if (options.minLength !== null && length < options.minLength) {
        fail(path, `is shorter than minLength ${options.minLength}`);
    }

    if (options.maxLength !== null && length > options.maxLength) {
        fail(path, `is longer than maxLength ${options.maxLength}`);
    }

    if (options.pattern !== null) {
        const regexp = compilePattern(options.pattern, `${path}`);

        if (regexp !== null && !regexp.test(value)) {
            fail(path, "does not match the declared pattern");
        }
    }

    if (options.choices !== null && !options.choices.includes(value)) {
        fail(path, "expected one of the declared choices");
    }
}


function checkIntDefault(options, value, path) {
    if (options.min !== null && value < options.min) {
        fail(path, `is below min ${options.min}`);
    }

    if (options.max !== null && value > options.max) {
        fail(path, `is above max ${options.max}`);
    }

    if (options.multipleOf !== null && value % options.multipleOf !== 0) {
        fail(path, `is not a multiple of ${options.multipleOf}`);
    }

    if (options.choices !== null && !options.choices.includes(value)) {
        fail(path, "expected one of the declared choices");
    }

    if (options.slider) {
        const step = options.step === null ? 1 : options.step;

        if (!onSliderGrid(value, options.min, options.max, step)) {
            fail(path,
                 `is not on the slider grid stepping by ${step} from `
                 + `${options.min}`);
        }
    }
}


function fileReferenceAccepted(extensions, reference) {
    if (extensions.length === 0) {
        return true;
    }

    const lower = reference.toLowerCase();

    return extensions.some((extension) => lower.endsWith(extension));
}


function checkFileReference(options, value, path) {
    if (typeof value !== "string") {
        fail(path, "expected a string file reference");
    }

    if (value === "") {
        fail(path, "expected a non-empty file reference");
    }

    if (!fileReferenceAccepted(options.extensions, value)) {
        fail(path, "is not an accepted file type");
    }
}


function checkFileDefault(options, value, path) {
    if (!options.multiple) {
        checkFileReference(options, value, path);
        return;
    }

    if (!Array.isArray(value)) {
        fail(path, "expected an array of file references for a multiple file node");
    }

    value.forEach((item, i) => checkFileReference(options, item, `${path}[${i}]`));

    if (options.minFiles !== null && value.length < options.minFiles) {
        fail(path, `expected at least ${options.minFiles} file references`);
    }

    if (options.maxFiles !== null && value.length > options.maxFiles) {
        fail(path, `expected at most ${options.maxFiles} file references`);
    }
}


function checkFloatDefault(options, value, path) {
    if (options.min !== null) {
        const below = options.minExclusive ? value <= options.min : value < options.min;

        if (below) {
            fail(path, `is below min ${options.min}`);
        }
    }

    if (options.max !== null) {
        const above = options.maxExclusive ? value >= options.max : value > options.max;

        if (above) {
            fail(path, `is above max ${options.max}`);
        }
    }

    if (options.choices !== null && !options.choices.includes(value)) {
        fail(path, "expected one of the declared choices");
    }
}


function checkIsoDefault(options, value, path) {
    if (options.min !== null) {
        const below = options.minExclusive === true
            ? value <= options.min
            : value < options.min;

        if (below) {
            fail(path, `is before min ${options.min}`);
        }
    }

    if (options.max !== null) {
        const above = options.maxExclusive === true
            ? value >= options.max
            : value > options.max;

        if (above) {
            fail(path, `is after max ${options.max}`);
        }
    }

    if (options.choices !== null && !options.choices.includes(value)) {
        fail(path, "expected one of the declared choices");
    }
}


function checkInitial(node, value, path) {
    if (node.kind === "str") {
        if (typeof value !== "string") {
            fail(path, "expected a string for str node");
        }

        checkStrDefault(node.options, value, path);
        return;
    }

    if (node.kind === "int") {
        if (typeof value !== "number" || !Number.isSafeInteger(value)) {
            fail(path, "expected a safe integer for int node");
        }

        checkIntDefault(node.options, value, path);
        return;
    }

    if (node.kind === "float") {
        if (typeof value !== "number" || !Number.isFinite(value)) {
            fail(path, "expected a finite number for float node");
        }

        checkFloatDefault(node.options, value, path);
        return;
    }

    if (node.kind === "date") {
        if (!isValidIsoDate(value)) {
            fail(path, "expected an ISO date for date node");
        }

        checkIsoDefault(node.options, value, path);
        return;
    }

    if (node.kind === "time") {
        if (typeof value !== "string" || !ISO_TIME.test(value)) {
            fail(path, "expected an ISO time for time node");
        }

        checkIsoDefault(node.options, value, path);
        return;
    }

    if (node.kind === "bool") {
        if (typeof value !== "boolean") {
            fail(path, "expected a boolean for bool node");
        }
        return;
    }

    if (node.kind === "file") {
        checkFileDefault(node.options, value, path);
        return;
    }

    if (node.kind === "enum") {
        if (typeof value !== "string") {
            fail(path, "expected a string for enum node");
        }

        if (!node.options.choices.includes(value)) {
            fail(path, "expected one of the declared choices");
        }
        return;
    }

    if (node.kind === "list") {
        if (!Array.isArray(value)) {
            fail(path, "expected an array for list node");
        }

        if (node.minItems !== null && value.length < node.minItems) {
            fail(path, `expected at least ${node.minItems} items`);
        }

        if (node.maxItems !== null && value.length > node.maxItems) {
            fail(path, `expected at most ${node.maxItems} items`);
        }

        value.forEach((item, i) => checkInitial(node.item, item, `${path}[${i}]`));
        return;
    }

    if (node.kind === "object") {
        if (value === null || typeof value !== "object" || Array.isArray(value)) {
            fail(path, "expected an object for object node");
        }

        const known = new Map(node.fields.map((field) => [field.name, field]));

        for (const key of Object.keys(value)) {
            const field = known.get(key);

            if (field === undefined) {
                fail(`${path}.${key}`, "unknown object field");
            }

            checkFieldInitial(field, value[key], `${path}.${key}`);
        }
        return;
    }

    if (node.kind === "choice") {
        if (value === null || typeof value !== "object" || Array.isArray(value)) {
            fail(path, "expected an object for choice node");
        }

        if (!Number.isInteger(value.branch)) {
            fail(`${path}.branch`, "expected an integer");
        }

        if (value.branch < 0 || value.branch >= node.branches.length) {
            fail(`${path}.branch`, `branch ${value.branch} is out of range`);
        }

        for (const key of Object.keys(value)) {
            if (key !== "branch" && key !== "value") {
                fail(`${path}.${key}`, "unknown property");
            }
        }

        checkInitial(node.branches[value.branch].node, value.value, `${path}.value`);
        return;
    }

    if (value === null) {
        return;
    }

    checkInitial(node.node, value, path);
}


function checkFieldInitial(field, value, path) {
    if (value === null && field.optional) {
        return;
    }

    checkInitial(field.node, value, path);
}


function checkField(field, path) {
    checkNode(field.node, `${path}.node`);

    if (field.hasDefault) {
        checkFieldInitial(field, field.default, `${path}.default`);
    }
}


export function checkPlan(plan) {
    const normalized = normalizePlan(plan);

    checkFieldNames(normalized.fields, "plan.fields");
    normalized.fields.forEach(
        (field, i) => checkField(field, `plan.fields[${i}]`));

    return normalized;
}
