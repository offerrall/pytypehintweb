import { CHOICE_DEFAULTS, LIST_DEFAULTS } from "./defaults.js";
import { putKey } from "./normalize.js";

const SVG_NS = "http://www.w3.org/2000/svg";

let counter = 0;


function trashIcon() {
    const svg = document.createElementNS(SVG_NS, "svg");

    for (const [name, value] of Object.entries({
        viewBox: "0 0 24 24",
        width: "18",
        height: "18",
        fill: "none",
        stroke: "currentColor",
        "stroke-width": "2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "aria-hidden": "true",
        focusable: "false",
    })) {
        svg.setAttribute(name, value);
    }

    const outline = document.createElementNS(SVG_NS, "path");
    outline.setAttribute(
        "d",
        "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 "
        + "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6");

    const bars = document.createElementNS(SVG_NS, "path");
    bars.setAttribute("d", "M10 11v6 M14 11v6");

    svg.append(outline, bars);

    return svg;
}


export function uniqueId(prefix = "pth-a11y") {
    counter += 1;

    return `${prefix}-${counter}`;
}


export function describedBy(control, id, present) {
    if (control === null) {
        return;
    }

    const current = control.getAttribute("aria-describedby");
    const ids = current === null || current === "" ? [] : current.split(" ");
    const rest = ids.filter((each) => each !== id);

    if (present) {
        rest.push(id);
    }

    if (rest.length === 0) {
        control.removeAttribute("aria-describedby");
        return;
    }

    control.setAttribute("aria-describedby", rest.join(" "));
}


export function markInvalid(control, invalid) {
    if (control === null) {
        return;
    }

    if (invalid) {
        control.setAttribute("aria-invalid", "true");
        return;
    }

    control.removeAttribute("aria-invalid");
}


function subscribe(callbacks, callback) {
    if (typeof callback !== "function") {
        throw new TypeError("onChange callback must be a function");
    }

    callbacks.add(callback);

    return () => callbacks.delete(callback);
}


function emit(callbacks) {
    for (const callback of callbacks) {
        callback();
    }
}


export function createMessage(className) {
    const message = document.createElement("small");
    message.className = className;
    message.id = uniqueId(className);
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");

    return message;
}


export function renderMessage(messageEl, control, text, { invalid = true } = {}) {
    messageEl.textContent = text ?? "";
    messageEl.hidden = text === null;

    // `invalid` is true for a validation message (the usual case) and false for
    // an informative status the control still describes but is not in error over
    // — a file field waiting for its upload, say. The message stays announced
    // through aria-describedby either way; only aria-invalid is withheld.
    markInvalid(control, invalid && text !== null);
    describedBy(control, messageEl.id, text !== null);
}


export class Widget {
    constructor() {
        if (new.target === Widget) {
            throw new TypeError("Widget is abstract");
        }

        this.el = null;
        this._callbacks = new Set();
    }

    isEmpty() {
        throw new Error(`${this.constructor.name} must implement isEmpty()`);
    }

    error() {
        return null;
    }

    hasError() {
        return this.error() !== null;
    }

    value() {
        throw new Error(`${this.constructor.name} must implement value()`);
    }

    setValue(value) {
        // Programmatic assignment is validate-and-apply. It is a scalar-widget
        // operation: containers are built from a plan (constructors), not
        // mutated wholesale, so there is no candidate/rollback protocol.
        this._check(value);
        this._apply(value);
        this._emitChange();
    }

    _check(value) {
        throw new Error(`${this.constructor.name} must implement _check(value)`);
    }

    _apply(value) {
        throw new Error(`${this.constructor.name} must implement _apply(value)`);
    }

    onChange(callback) {
        return subscribe(this._callbacks, callback);
    }

    _emitChange() {
        emit(this._callbacks);
    }

    control() {
        return null;
    }

    // The files chosen locally that a host still has to upload, as
    // { reference, file, complete } — complete() marks one as no longer pending
    // without touching value(). Only FileWidget ever holds any; a container
    // gathers its children's, so a host never walks the plan looking for them.
    uploads() {
        return [];
    }

    isReady() {
        return !this.isEmpty() && !this.hasError();
    }

    // Reveal any validation message the widget has held back until the user
    // touched it — the submit-time "mark all errors" pass a host runs when the
    // user submits without having visited every field. The default does nothing
    // (a checkbox or a select is never in error); the touched scalar inputs flip
    // their flag and re-render, and the containers reach their children.
    // Idempotent, and it never changes value(), read() or isReady() — only what
    // is shown.
    showErrors() {}
}


function checkControl(control) {
    if (control === null || control === undefined) {
        return null;
    }

    const elementType = globalThis.HTMLElement ?? globalThis.Element;
    const isElement = elementType === undefined
        ? typeof control === "object"
        : control instanceof elementType;

    if (!isElement) {
        throw new TypeError("Widget.control() must return an HTMLElement or null");
    }

    return control;
}


// A container is built from a plan through constructors, never assigned
// wholesale, so it has no composite setValue(). It says so plainly rather than
// inheriting the base template and failing deep inside on the abstract "_check".
function rejectContainerSetValue(widget) {
    throw new TypeError(
        `${widget.constructor.name} does not support setValue(): a container is `
        + "built from a plan, not assigned. Assign the scalar widgets inside it.");
}


export class Field extends Widget {
    constructor(
        {
            id,
            name,
            description,
            optional = false,
            optionalEnabled = true,
        },
        widget,
    ) {
        super();

        if (!(widget instanceof Widget)) {
            throw new TypeError("Field only accepts a Widget");
        }

        this.widget = widget;
        this.toggle = null;

        const base = id === undefined ? uniqueId("pth-field") : id;

        this.el = document.createElement("div");
        this.el.className = "pth-field";

        const header = document.createElement("div");
        header.className = "pth-field-header";

        const label = document.createElement("label");
        label.className = "pth-label";
        label.id = `${base}-label`;
        label.textContent = name;
        header.append(label);

        const control = checkControl(widget.control());

        if (control !== null) {
            control.id = base;
            label.htmlFor = base;
        } else {
            widget.el.id = `${base}-content`;
            widget.el.setAttribute("role", "group");
            widget.el.setAttribute("aria-labelledby", label.id);
        }

        if (optional) {
            this.toggle = document.createElement("input");
            this.toggle.type = "checkbox";
            this.toggle.className = "pth-toggle";
            this.toggle.checked = optionalEnabled;
            this.toggle.setAttribute("aria-labelledby", label.id);
            this.toggle.setAttribute(
                "aria-controls",
                control !== null ? base : `${base}-content`);

            this.toggle.addEventListener("change", () => {
                this._applyToggle();
                this._emitChange();
            });

            header.append(this.toggle);
        }

        this.el.append(header);

        // null and undefined are both absence (compileField maps null to
        // undefined; the direct API takes either). Treating null as a description
        // would append an empty <small>, mint an id, and point aria-describedby
        // at nothing.
        if (description !== undefined && description !== null) {
            const descriptionEl = document.createElement("small");
            descriptionEl.className = "pth-description";
            descriptionEl.id = `${base}-description`;
            descriptionEl.textContent = description;
            this.el.append(descriptionEl);
            describedBy(control ?? widget.el, descriptionEl.id, true);
        }

        this.el.append(widget.el);

        widget.onChange(() => this._emitChange());

        this._applyToggle();
    }

    control() {
        return this.widget.control();
    }

    enabled() {
        if (this.toggle === null) {
            return true;
        }

        return this.toggle.checked;
    }

    setEnabled(enabled) {
        // Programmatic equivalent of clicking the optional toggle: flips it, hides
        // or shows the content, and emits one change — the same path as a user
        // click. A required field has no toggle and is always on.
        if (typeof enabled !== "boolean") {
            throw new TypeError("Field.setEnabled expects a boolean");
        }

        if (this.toggle === null) {
            if (!enabled) {
                throw new TypeError(
                    "Field.setEnabled: a required field cannot be disabled");
            }
            return;
        }

        if (this.toggle.checked === enabled) {
            return;
        }

        this.toggle.checked = enabled;
        this._applyToggle();
        this._emitChange();
    }

    setValue() {
        rejectContainerSetValue(this);
    }

    value() {
        if (!this.enabled()) {
            return null;
        }

        return this.widget.value();
    }

    uploads() {
        // A switched-off optional reads null, so nothing under it is uploaded.
        if (!this.enabled()) {
            return [];
        }

        return this.widget.uploads();
    }

    isEmpty() {
        if (!this.enabled()) {
            return false;
        }

        return this.widget.isEmpty();
    }

    hasError() {
        if (!this.enabled()) {
            return false;
        }

        return this.widget.hasError();
    }

    isReady() {
        if (!this.enabled()) {
            return true;
        }

        return this.widget.isReady();
    }

    showErrors() {
        // A switched-off optional reads null and is never in error, so there is
        // nothing to reveal; an enabled field defers to its widget.
        if (this.enabled()) {
            this.widget.showErrors();
        }
    }

    _applyToggle() {
        this.widget.el.hidden = !this.enabled();
    }
}


export class ChoiceWidget extends Widget {
    constructor(branches, {
        selectedIndex = 0,
        previousLabel = CHOICE_DEFAULTS.previousLabel,
        nextLabel = CHOICE_DEFAULTS.nextLabel,
        positionLabel = CHOICE_DEFAULTS.positionLabel,
    } = {}) {
        super();

        if (!Array.isArray(branches) || branches.length === 0) {
            throw new TypeError("ChoiceWidget needs at least one branch");
        }

        if (!Number.isInteger(selectedIndex)
                || selectedIndex < 0
                || selectedIndex >= branches.length) {
            throw new RangeError(`ChoiceWidget has no branch ${selectedIndex}`);
        }

        for (const branch of branches) {
            if (
                branch === null ||
                typeof branch !== "object" ||
                !(branch.widget instanceof Widget)
            ) {
                throw new TypeError("Each branch needs { widget: Widget }");
            }
        }

        this.branches = branches;
        this.index = selectedIndex;
        this.positionLabel = positionLabel;

        this.el = document.createElement("div");
        this.el.className = "pth-choice";

        const nav = document.createElement("div");
        nav.className = "pth-mode-navigation";

        this.previous = document.createElement("button");
        this.previous.type = "button";
        this.previous.className = "pth-mode-previous";
        this.previous.textContent = "‹";
        this.previous.setAttribute("aria-label", previousLabel);
        this.previous.addEventListener("click", () => this._move(-1));

        this.position = document.createElement("span");
        this.position.className = "pth-mode-position";
        this.position.setAttribute("aria-live", "polite");

        this.next = document.createElement("button");
        this.next.type = "button";
        this.next.className = "pth-mode-next";
        this.next.textContent = "›";
        this.next.setAttribute("aria-label", nextLabel);
        this.next.addEventListener("click", () => this._move(1));

        nav.append(this.previous, this.position, this.next);
        this.el.append(nav);

        this.content = document.createElement("div");
        this.content.className = "pth-mode-content";
        this.el.append(this.content);

        for (const branch of branches) {
            branch.widget.onChange(() => this._emitChange());
        }

        this._render();
    }

    active() {
        return this.branches[this.index].widget;
    }

    activeIndex() {
        return this.index;
    }

    selectedValue() {
        return this.branches[this.index].value;
    }

    control() {
        return null;
    }

    setValue() {
        rejectContainerSetValue(this);
    }

    value() {
        return this.active().value();
    }

    uploads() {
        // Only the active branch is read, so only it uploads.
        return this.active().uploads();
    }

    isEmpty() {
        return this.active().isEmpty();
    }

    hasError() {
        return this.active().hasError();
    }

    isReady() {
        return this.active().isReady();
    }

    showErrors() {
        // Only the active branch is shown and read, so only it reveals.
        this.active().showErrors();
    }

    _move(direction) {
        const target = this.index + direction;

        if (target < 0 || target >= this.branches.length) {
            return;
        }

        this.index = target;
        this._render();
        this._keepFocusReachable(direction);
        this._emitChange();
    }

    // Reaching an extreme disables the button just activated (index 0 disables
    // previous, the last disables next), and a disabled control drops focus to
    // the body. Move it to the still-enabled sibling instead. Only these two
    // buttons, only on an interactive move — never at construction.
    _keepFocusReachable(direction) {
        const activated = direction < 0 ? this.previous : this.next;

        if (!activated.disabled) {
            return;
        }

        const sibling = direction < 0 ? this.next : this.previous;

        if (typeof sibling.focus === "function") {
            sibling.focus();
        }
    }

    _render() {
        this.content.replaceChildren(this.active().el);
        this.position.textContent = this.positionLabel
            .replace("{current}", String(this.index + 1))
            .replace("{total}", String(this.branches.length));
        this.previous.disabled = this.index === 0;
        this.next.disabled = this.index === this.branches.length - 1;
    }
}


export class GroupWidget extends Widget {
    constructor(children) {
        super();

        if (!Array.isArray(children) || children.length === 0) {
            throw new TypeError("GroupWidget needs at least one child");
        }

        for (const child of children) {
            if (
                child === null ||
                typeof child !== "object" ||
                typeof child.name !== "string" ||
                !(child.widget instanceof Widget)
            ) {
                throw new TypeError("Each child needs { name: string, widget: Widget }");
            }
        }

        this.children = children;
        this.el = document.createElement("div");
        this.el.className = "pth-group";

        for (const child of children) {
            this.el.append(child.widget.el);
            child.widget.onChange(() => this._emitChange());
        }
    }

    setValue() {
        rejectContainerSetValue(this);
    }

    value() {
        const result = {};

        for (const child of this.children) {
            putKey(result, child.name, child.widget.value());
        }

        return result;
    }

    uploads() {
        return this.children.flatMap((child) => child.widget.uploads());
    }

    isEmpty() {
        return this.children.some((child) => child.widget.isEmpty());
    }

    hasError() {
        return this.children.some((child) => child.widget.hasError());
    }

    isReady() {
        return this.children.every((child) => child.widget.isReady());
    }

    showErrors() {
        for (const child of this.children) {
            child.widget.showErrors();
        }
    }
}


export class ListWidget extends Widget {
    constructor(
        createItem,
        initialValues = [],
        {
            addLabel = LIST_DEFAULTS.addLabel,
            removeLabel = LIST_DEFAULTS.removeLabel,
            minItems = LIST_DEFAULTS.minItems,
            maxItems = LIST_DEFAULTS.maxItems,
            minMessage = LIST_DEFAULTS.minMessage,
            maxMessage = LIST_DEFAULTS.maxMessage,
        } = {},
    ) {
        super();

        if (typeof createItem !== "function") {
            throw new TypeError("ListWidget needs a factory returning Widgets");
        }

        if (!Array.isArray(initialValues)) {
            throw new TypeError("ListWidget initial values must be an array");
        }

        if (typeof addLabel !== "string") {
            throw new TypeError("ListWidget addLabel must be a string");
        }

        if (typeof removeLabel !== "string") {
            throw new TypeError("ListWidget removeLabel must be a string");
        }

        for (const [name, limit] of [["minItems", minItems], ["maxItems", maxItems]]) {
            if (limit !== null && (!Number.isSafeInteger(limit) || limit < 0)) {
                throw new TypeError(
                    `ListWidget ${name} must be a non-negative safe integer`);
            }
        }

        if (minItems !== null && maxItems !== null && minItems > maxItems) {
            throw new RangeError("ListWidget minItems must not exceed maxItems");
        }

        if (maxItems !== null && initialValues.length > maxItems) {
            throw new TypeError(
                "ListWidget initial values must not exceed maxItems");
        }

        this.addLabel = addLabel;
        this.removeLabel = removeLabel;
        this.minItems = minItems;
        this.maxItems = maxItems;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;
        this._touched = false;

        this.createItem = createItem;
        this.items = [];

        this.el = document.createElement("div");
        this.el.className = "pth-list";

        this.itemsEl = document.createElement("div");
        this.itemsEl.className = "pth-list-items";
        this.el.append(this.itemsEl);

        this.addButton = document.createElement("button");
        this.addButton.type = "button";
        this.addButton.className = "pth-list-add";
        this.addButton.textContent = this.addLabel;

        this.addButton.addEventListener("click", () => {
            this._touched = true;
            this.add();
        });

        this.el.append(this.addButton);

        this.message = createMessage("pth-list-message");
        this.el.append(this.message);

        for (const initialValue of initialValues) {
            this.add(initialValue);
        }

        this._applyState();
    }

    canAdd() {
        return this.maxItems === null || this.items.length < this.maxItems;
    }

    canRemove() {
        return this.minItems === null || this.items.length > this.minItems;
    }

    _mountItem(widget) {
        if (!(widget instanceof Widget)) {
            throw new TypeError("The ListWidget factory must return a Widget");
        }

        const row = document.createElement("div");
        row.className = "pth-list-item";

        const content = document.createElement("div");
        content.className = "pth-list-item-content";
        content.append(widget.el);

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "pth-list-remove";
        removeButton.append(trashIcon());

        const item = {
            widget,
            row,
            removeButton,
            unsubscribe: widget.onChange(() => this._emitChange()),
        };

        removeButton.addEventListener("click", () => {
            this._touched = true;
            this.remove(item);
        });

        row.append(content);
        row.append(removeButton);

        this.items.push(item);
        this.itemsEl.append(row);

        return item;
    }

    add(initialValue) {
        if (!this.canAdd()) {
            return null;
        }

        const item = this._mountItem(this.createItem(initialValue));

        this._applyState();
        this._emitChange();

        return item.widget;
    }

    remove(item) {
        const index = this.items.indexOf(item);

        if (index === -1 || !this.canRemove()) {
            return;
        }

        this.items.splice(index, 1);
        item.unsubscribe();
        item.row.remove();

        this._applyState();
        this._emitChange();
    }

    widgets() {
        return this.items.map((item) => item.widget);
    }

    setValue() {
        rejectContainerSetValue(this);
    }

    value() {
        return this.items.map((item) => item.widget.value());
    }

    uploads() {
        return this.items.flatMap((item) => item.widget.uploads());
    }

    isEmpty() {
        return false;
    }

    touched() {
        return this._touched;
    }

    error() {
        const count = this.items.length;

        if (this.minItems !== null && count < this.minItems) {
            return this.minMessage.replace("{value}", String(this.minItems));
        }

        if (this.maxItems !== null && count > this.maxItems) {
            return this.maxMessage.replace("{value}", String(this.maxItems));
        }

        return null;
    }

    hasError() {
        return this.error() !== null
            || this.items.some((item) => item.widget.hasError());
    }

    isReady() {
        return this.error() === null
            && this.items.every((item) => item.widget.isReady());
    }

    showErrors() {
        // Reveal the list's own count message and every item's.
        this._touched = true;
        this._applyState();

        for (const item of this.items) {
            item.widget.showErrors();
        }
    }

    _applyState() {
        this.addButton.disabled = !this.canAdd();

        this.items.forEach((item, index) => {
            item.removeButton.disabled = !this.canRemove();
            item.removeButton.setAttribute(
                "aria-label", `${this.removeLabel} ${index + 1}`);
        });

        renderMessage(
            this.message, this.el, this._touched ? this.error() : null);
    }
}
