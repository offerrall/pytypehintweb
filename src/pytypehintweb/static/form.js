import { checkPlan } from "./contract.js";
import { ownValue, putKey } from "./normalize.js";
import {
    ChoiceWidget, Field, GroupWidget, ListWidget, uniqueId,
} from "./fields.js";
import {
    BoolWidget, DateWidget, FileWidget, FloatChoiceWidget, FloatWidget,
    IntChoiceWidget, IntWidget, StrChoiceWidget, StrWidget, TimeWidget,
} from "./inputs.js";

const TYPE = "$type";
const VALUE = "$value";


function idFactory(prefix) {
    return () => uniqueId(prefix);
}


function scalar(widget) {
    return { widget, read: () => widget.value() };
}


function withValue(options, initial) {
    return initial === undefined ? options : { ...options, value: initial };
}


function withInitial(widget, initial) {
    if (initial !== undefined) {
        widget.setValue(initial);
    }

    return widget;
}


function childOpening({ initial, hidden }, name) {
    return {
        initial: initial === undefined ? undefined : ownValue(initial, name),
        hidden: hidden.flatMap((path) => path === name ? [""]
            : path.startsWith(`${name}.`) && path.length > name.length + 1
                ? [path.slice(name.length + 1)] : []),
    };
}


function compileFields(fields, nextId, opening) {
    return fields.map((field) => {
        const child = childOpening(opening, field.name);
        return compileField(field, nextId, child.initial, child.hidden);
    });
}


function compileNode(node, nextId, opening) {
    const { initial } = opening;
    switch (node.kind) {
        case "str":
            if (node.options.choices !== null) {
                return scalar(new StrChoiceWidget(node.options.choices, initial));
            }
            return scalar(new StrWidget(withValue(node.options, initial)));

        case "int":
            if (node.options.choices !== null) {
                return scalar(new IntChoiceWidget(node.options.choices, initial));
            }
            return scalar(new IntWidget(withValue(node.options, initial)));

        case "float":
            if (node.options.choices !== null) {
                return scalar(new FloatChoiceWidget(node.options.choices, initial));
            }
            return scalar(new FloatWidget(withValue(node.options, initial)));

        case "date":
            if (node.options.choices !== null) {
                return scalar(new StrChoiceWidget(node.options.choices, initial));
            }
            return scalar(new DateWidget(withValue(node.options, initial)));

        case "time":
            if (node.options.choices !== null) {
                return scalar(new StrChoiceWidget(node.options.choices, initial));
            }
            return scalar(new TimeWidget(withValue(node.options, initial)));

        case "enum":
            return scalar(new StrChoiceWidget(node.options.choices, initial));

        case "bool":
            return scalar(new BoolWidget(withValue(node.options, initial)));

        case "file":
            return scalar(withInitial(new FileWidget(node.options), initial));

        case "list":
            return compileList(node, nextId, opening);

        case "object":
            return compileObject(node, nextId, opening);

        case "choice":
            return compileChoice(node, nextId, opening);

        case "optional":
            return compileOptional(node, nextId, opening);

        default:
            throw new TypeError(`unknown node: ${node.kind}`);
    }
}


function compileList(node, nextId, opening) {
    const { initial } = opening;
    const readers = new WeakMap();

    const itemOpening = childOpening({ ...opening, initial: undefined }, "*");
    const createItem = (initial) => {
        const item = compileNode(node.item, nextId, { ...itemOpening, initial });
        item.widget.el.hidden = itemOpening.hidden.includes("");
        readers.set(item.widget, item.read);
        return item.widget;
    };

    const options = {
        addLabel: node.addLabel,
        removeLabel: node.removeLabel,
        minItems: node.minItems,
        maxItems: node.maxItems,
        minMessage: node.minMessage,
        maxMessage: node.maxMessage,
    };

    const widget = new ListWidget(
        createItem, initial === undefined ? [] : initial, options);

    return {
        widget,
        read: () => widget.widgets().map((child) => readers.get(child)()),
    };
}


function compileObject(node, nextId, opening) {
    const children = compileFields(node.fields, nextId, opening);

    const widget = new GroupWidget(
        children.map((child) => ({ name: child.name, widget: child.widget })),
    );

    return {
        widget,
        read: () => {
            const result = {};
            for (const child of children) {
                putKey(result, child.name, child.read());
            }
            return result;
        },
    };
}


function compileChoice(node, nextId, opening) {
    const { initial } = opening;
    const selectedIndex = initial === undefined ? 0 : initial.branch;

    const branches = node.branches.map((branch, index) => ({
        ...branch,
        compiled: compileNode(
            branch.node, nextId,
            {
                ...opening,
                initial: index === selectedIndex && initial !== undefined
                    ? initial.value : undefined,
            },
        ),
    }));

    const widget = new ChoiceWidget(
        branches.map((branch) => ({
            value: branch.value,
            widget: branch.compiled.widget,
        })),
        {
            selectedIndex,
            previousLabel: node.previousLabel,
            nextLabel: node.nextLabel,
            positionLabel: node.positionLabel,
        },
    );

    return {
        widget,
        read: () => {
            const branch = branches[widget.activeIndex()];
            const value = branch.compiled.read();

            if (branch.mode === "wrapped") {
                return { [TYPE]: branch.value, [VALUE]: value };
            }

            if (branch.mode === "inline") {
                return { [TYPE]: branch.value, ...value };
            }

            return value;
        },
    };
}


function compileOptional(node, nextId, opening) {
    const { initial } = opening;
    const inner = compileNode(node.node, nextId, {
        ...opening, initial: initial === null ? undefined : initial,
    });

    const widget = new Field(
        {
            id: nextId(),
            name: node.label,
            optional: true,
            optionalEnabled: initial === undefined ? node.enabled : initial !== null,
        },
        inner.widget,
    );

    return {
        widget,
        read: () => (widget.enabled() ? inner.read() : null),
    };
}


export function compileField(field, nextId, inherited, hidden = []) {
    const initial = inherited === undefined && field.hasDefault
        ? field.default
        : inherited;

    const enabled = inherited === undefined ? field.enabled : inherited !== null;

    const inner = compileNode(field.node, nextId, {
        initial: initial === null ? undefined : initial, hidden,
    });

    const widget = new Field(
        {
            id: nextId(),
            name: field.label,
            description: field.description === null ? undefined : field.description,
            optional: field.optional,
            optionalEnabled: enabled,
        },
        inner.widget,
    );

    widget.el.hidden = hidden.includes("");

    return {
        name: field.name,
        widget,
        read: () => (widget.enabled() ? inner.read() : null),
    };
}


export function compileForm(plan, { prefix = "pth", hidden = [] } = {}) {
    const normalized = checkPlan(plan);

    if (!Array.isArray(hidden) || hidden.some((path) => typeof path !== "string")) {
        throw new TypeError("hidden must be an array of strings");
    }

    const nextId = idFactory(prefix);
    const fields = compileFields(normalized.fields, nextId, { hidden });

    const callbacks = new Set();

    const emit = () => {
        for (const callback of callbacks) {
            callback();
        }
    };

    fields.forEach((field) => field.widget.onChange(emit));

    return {
        name: normalized.name,
        description: normalized.description,
        fields,
        isReady: () => fields.every((field) => field.widget.isReady()),
        uploads: () => fields.flatMap((field) => field.widget.uploads()),
        hasError: () => fields.some((field) => field.widget.hasError()),
        showErrors: () => fields.forEach((field) => field.widget.showErrors()),
        onChange: (callback) => {
            if (typeof callback !== "function") {
                throw new TypeError("onChange callback must be a function");
            }

            callbacks.add(callback);

            return () => callbacks.delete(callback);
        },
        read: () => {
            const result = {};
            for (const field of fields) {
                putKey(result, field.name, field.read());
            }
            return result;
        },
    };
}
