import {
    DATE_DEFAULTS, FILE_DEFAULTS, FLOAT_DEFAULTS, INT_DEFAULTS, STR_DEFAULTS,
    TIME_DEFAULTS,
} from "./defaults.js";
import { Widget, createMessage, renderMessage } from "./fields.js";
import { isValidIsoDate } from "./iso.js";
import { firstSliderValue, onSliderGrid } from "./slider.js";

const INTEGER = /^-?\d+$/;

export const COLOR_PATTERN = "#[0-9a-fA-F]{6}";

const ISO_TIME = /^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$/;
const isIsoTime = (value) => ISO_TIME.test(value);

const FLOAT = /^-?\d+(\.\d+)?$/;

function isWritableFloat(value) {
    return typeof value === "number"
        && Number.isFinite(value)
        && FLOAT.test(String(value));
}

const MIN_SAFE_BIGINT = BigInt(Number.MIN_SAFE_INTEGER);
const MAX_SAFE_BIGINT = BigInt(Number.MAX_SAFE_INTEGER);

const SAFE_ATTRIBUTES = new Set([
    "min", "max", "step", "rows", "placeholder", "title", "type", "accept",
    "role", "aria-label", "aria-labelledby", "aria-describedby",
    "aria-invalid", "aria-controls",
]);


function setAttributes(el, attributes) {
    for (const [name, value] of Object.entries(attributes)) {
        if (!SAFE_ATTRIBUTES.has(name)) {
            throw new TypeError(
                `${name} is not a plan-writable attribute`);
        }

        if (value === null || value === undefined) {
            continue;
        }

        el.setAttribute(name, String(value));
    }
}


function withValue(template, value) {
    return template.replace("{value}", String(value));
}


function stringLength(value) {
    return Array.from(value).length;
}


function checkChoices(choices, isValid, what) {
    if (!Array.isArray(choices) || choices.length === 0) {
        throw new TypeError(`${what} needs a non-empty array of choices`);
    }

    const seen = new Set();

    for (const choice of choices) {
        if (!isValid(choice)) {
            throw new TypeError(`${what} got an invalid choice: ${String(choice)}`);
        }

        if (seen.has(choice)) {
            throw new TypeError(`${what} got a duplicated choice: ${String(choice)}`);
        }

        seen.add(choice);
    }
}


class ChoiceInput extends Widget {
    constructor(choices, initialValue, what) {
        super();

        this.choices = choices;
        this.what = what;

        this.el = document.createElement("select");
        this.el.className = "pth-choice-input";

        choices.forEach((choice, index) => {
            this.el.append(new Option(String(choice), String(index)));
        });

        this.el.addEventListener("change", () => this._emitChange());

        if (initialValue === undefined) {
            this.el.value = "0";
            return;
        }

        const index = choices.indexOf(initialValue);

        if (index === -1) {
            throw new TypeError(`${what} got an initial value outside its choices`);
        }

        this.el.value = String(index);
    }

    control() {
        return this.el;
    }

    value() {
        return this.choices[Number(this.el.value)];
    }

    isEmpty() {
        return false;
    }

    _check(value) {
        if (this.choices.indexOf(value) === -1) {
            throw new TypeError(`${this.what} accepts only one of its choices`);
        }
    }

    _apply(value) {
        this.el.value = String(this.choices.indexOf(value));
    }
}


export class StrChoiceWidget extends ChoiceInput {
    constructor(choices, initialValue) {
        checkChoices(choices, (c) => typeof c === "string", "StrChoiceWidget");
        super(choices, initialValue, "StrChoiceWidget");
    }
}


export class IntChoiceWidget extends ChoiceInput {
    constructor(choices, initialValue) {
        checkChoices(choices, (c) => Number.isSafeInteger(c), "IntChoiceWidget");
        super(choices, initialValue, "IntChoiceWidget");
    }
}


export class FloatChoiceWidget extends ChoiceInput {
    constructor(choices, initialValue) {
        checkChoices(
            choices,
            (c) => typeof c === "number" && Number.isFinite(c),
            "FloatChoiceWidget");
        super(choices, initialValue, "FloatChoiceWidget");
    }
}


export class BoolWidget extends Widget {
    constructor({ value = false } = {}) {
        super();

        this.el = document.createElement("div");
        this.el.className = "pth-bool";

        this.input = document.createElement("input");
        this.input.type = "checkbox";
        this.input.checked = value === true;
        this.el.append(this.input);

        this.input.addEventListener("change", () => this._emitChange());
    }

    control() {
        return this.input;
    }

    value() {
        return this.input.checked === true;
    }

    isEmpty() {
        return false;
    }

    _check(value) {
        if (typeof value !== "boolean") {
            throw new TypeError("BoolWidget.setValue expects true or false");
        }
    }

    _apply(value) {
        this.input.checked = value;
    }
}


const FILE_SLUG_LIMIT = 15;

const ASCII_FOLDINGS = {
    "ß": "ss", "æ": "ae", "œ": "oe", "ø": "o", "å": "a", "đ": "d", "ð": "d",
    "þ": "th", "ł": "l", "ı": "i",
};


export function asciiSlug(text) {
    return text
        .normalize("NFD")
        .replace(/\p{M}+/gu, "")
        .toLowerCase()
        .replace(/[ßæœøåđðþłı]/gu, (char) => ASCII_FOLDINGS[char])
        .replace(/[^a-z0-9]+/gu, "-")
        .replace(/^-+|-+$/gu, "")
        .slice(0, FILE_SLUG_LIMIT)
        .replace(/-+$/u, "");
}


export function mintFileReference(name, extension) {
    const slug = asciiSlug(name.slice(0, name.length - extension.length));
    const hash = globalThis.crypto.randomUUID();

    return slug === ""
        ? `${hash}${extension}`
        : `${slug}-${hash}${extension}`;
}


export class FileWidget extends Widget {
    constructor({
        extensions = FILE_DEFAULTS.extensions,
        invalidMessage = FILE_DEFAULTS.invalidMessage,
        multiple = FILE_DEFAULTS.multiple,
        minFiles = FILE_DEFAULTS.minFiles,
        maxFiles = FILE_DEFAULTS.maxFiles,
        minMessage = FILE_DEFAULTS.minMessage,
        maxMessage = FILE_DEFAULTS.maxMessage,
        currentLabel = FILE_DEFAULTS.currentLabel,
        currentRemoveLabel = FILE_DEFAULTS.currentRemoveLabel,
        currentReplaceLabel = FILE_DEFAULTS.currentReplaceLabel,
        currentRestoreLabel = FILE_DEFAULTS.currentRestoreLabel,
    } = {}) {
        super();

        if (!Array.isArray(extensions)) {
            throw new TypeError("FileWidget extensions must be an array");
        }

        this.extensions = extensions;
        this.invalidMessage = invalidMessage;
        this.multiple = multiple === true;
        this.minFiles = minFiles;
        this.maxFiles = maxFiles;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;
        this.currentLabel = currentLabel;
        this.currentRemoveLabel = currentRemoveLabel;
        this.currentReplaceLabel = currentReplaceLabel;
        this.currentRestoreLabel = currentRestoreLabel;

        this._files = [];
        this._refs = [];
        this._invalid = false;
        this._current = null;
        this._stashedCurrent = null;
        this._uploaded = new Set();
        this.touched = false;

        this.el = document.createElement("div");
        this.el.className = "pth-file";

        this.row = document.createElement("div");
        this.row.className = "pth-file-row";
        this.el.append(this.row);

        this.input = document.createElement("input");
        this.input.type = "file";
        this.input.className = "pth-file-input";
        if (this.multiple) {
            this.input.multiple = true;
        }

        this._accept = extensions.join(",");
        setAttributes(this.input, { accept: this._accept === "" ? null : this._accept });

        this.row.append(this.input);

        this.addBtn = null;
        if (this.multiple) {
            this.addBtn = document.createElement("button");
            this.addBtn.type = "button";
            this.addBtn.className = "pth-file-add";
            this.addBtn.textContent = "+";
            this.addBtn.setAttribute("aria-label", "Add file");
            this.addBtn.addEventListener("click", () => this._openPicker());
            this.row.append(this.addBtn);
        }

        this.restore = document.createElement("button");
        this.restore.type = "button";
        this.restore.className = "pth-file-restore";
        this.restore.textContent = "↺";
        this.restore.hidden = true;
        this.restore.setAttribute("aria-label", currentRestoreLabel);
        this.restore.addEventListener("click", () => this._restore());
        this.row.append(this.restore);

        this.current = document.createElement("div");
        this.current.className = "pth-file-current";
        this.current.hidden = true;
        this.el.append(this.current);

        this.list = document.createElement("div");
        this.list.className = "pth-file-list";
        this.list.hidden = true;
        this.el.append(this.list);

        this.message = createMessage("pth-file-message");
        this.el.append(this.message);

        this.input.addEventListener("change", () => this._ingestFromInput());
        this._setupDrag();

        this._renderCurrent();
        this._renderList();
        this._showMessage();
    }

    control() {
        return this.input;
    }

    file() {
        return this._files.length > 0 ? this._files[0] : null;
    }

    files() {
        return this._files.slice();
    }

    value() {
        if (this._current !== null) {
            return this.multiple ? this._current.slice() : this._current[0];
        }

        if (this.multiple) {
            return this._refs.slice();
        }

        return this._refs.length > 0 ? this._refs[0] : null;
    }

    uploads() {
        if (this._current !== null) {
            return [];
        }

        const pending = [];

        for (const [index, reference] of this._refs.entries()) {
            if (this._uploaded.has(reference)) {
                continue;
            }

            pending.push({
                reference,
                file: this._files[index],
                complete: () => { this._uploaded.add(reference); },
            });
        }

        return pending;
    }

    isEmpty() {
        if (this._current !== null) {
            return false;
        }

        if (this.multiple) {
            return false;
        }

        return this._files.length === 0;
    }

    setValue(value) {
        if (value === null) {
            this._clear();
            return;
        }

        this._current = this._asReferences(value);
        this._files = [];
        this._refs = [];
        this._invalid = false;
        this._stashedCurrent = null;
        this.input.value = "";

        this._renderCurrent();
        this._showMessage();
        this._emitChange();
    }

    error() {
        if (this._current !== null) {
            return null;
        }

        if (this._invalid) {
            return this.invalidMessage;
        }

        if (this.multiple) {
            const count = this._refs.length;

            if (this.minFiles !== null && count < this.minFiles) {
                return this.minMessage.replace("{value}", String(this.minFiles));
            }

            if (this.maxFiles !== null && count > this.maxFiles) {
                return this.maxMessage.replace("{value}", String(this.maxFiles));
            }
        }

        return null;
    }

    _asReferences(value) {
        let candidates;

        if (this.multiple) {
            if (typeof value === "string") {
                candidates = [value];
            } else if (Array.isArray(value)
                    && value.every((v) => typeof v === "string")) {
                candidates = value.slice();
            } else {
                throw new TypeError(
                    "FileWidget.setValue expects a string, an array of strings, or null");
            }
        } else if (typeof value === "string") {
            candidates = [value];
        } else {
            throw new TypeError("FileWidget.setValue expects a string or null");
        }

        for (const reference of candidates) {
            if (reference === "") {
                throw new TypeError("FileWidget.setValue expects a non-empty reference");
            }

            if (!this._accepts(reference)) {
                throw new TypeError(
                    "FileWidget.setValue got a reference whose extension is not accepted");
            }
        }

        return candidates;
    }

    _accepts(reference) {
        if (this.extensions.length === 0) {
            return true;
        }

        const lower = reference.toLowerCase();

        return this.extensions.some((extension) => lower.endsWith(extension));
    }

    _clear() {
        this._files = [];
        this._refs = [];
        this._invalid = false;
        this._current = null;
        this._stashedCurrent = null;
        this.input.value = "";

        this._renderCurrent();
        this._renderList();
        this._showMessage();
        this._emitChange();
    }

    _beginReplace() {
        this._stashedCurrent = this._current;
        this._current = null;
        this._files = [];
        this._refs = [];
        this._invalid = false;
        this.input.value = "";

        this._renderCurrent();
        this._renderList();
        this._showMessage();
        this._emitChange();
    }

    _restore() {
        if (this._stashedCurrent === null) {
            return;
        }

        this._current = this._stashedCurrent;
        this._stashedCurrent = null;
        this._files = [];
        this._refs = [];
        this._invalid = false;
        this.input.value = "";

        this._renderCurrent();
        this._renderList();
        this._showMessage();
        this._emitChange();
    }

    _matchedExtension(name) {
        const lower = name.toLowerCase();

        if (this.extensions.length === 0) {
            const dot = lower.lastIndexOf(".");
            return dot === -1 ? "" : lower.slice(dot);
        }

        return this.extensions.find((extension) => lower.endsWith(extension))
            ?? null;
    }

    _ingestFromInput() {
        this._ingest(this.input.files ? Array.from(this.input.files) : []);
    }

    _syncNativeInput() {
        if (this._files.length === 0) {
            this.input.value = "";
            return;
        }

        const Transfer = globalThis.DataTransfer;

        if (typeof Transfer !== "function") {
            return;
        }

        const data = new Transfer();

        for (const file of this._files) {
            data.items.add(file);
        }

        this.input.files = data.files;
    }

    _ingest(incoming, append = false) {
        this.touched = true;
        this._current = null;

        const chosen = this.multiple ? incoming : incoming.slice(0, 1);
        const matched = chosen.map((file) => this._matchedExtension(file.name));

        if (chosen.length > 0 && matched.some((extension) => extension === null)) {
            this._invalid = true;

            if (!this.multiple) {
                this._files = chosen;
                this._refs = [];
            }
        } else {
            this._invalid = false;

            const refs = matched.map(
                (extension, i) => mintFileReference(chosen[i].name, extension));

            if (this.multiple && append) {
                this._files = [...this._files, ...chosen];
                this._refs = [...this._refs, ...refs];
            } else {
                this._files = chosen;
                this._refs = refs;
            }
        }

        this._syncNativeInput();
        this._renderCurrent();
        this._renderList();
        this._showMessage();
        this._emitChange();
    }

    _removeAt(index) {
        this.touched = true;
        this._files.splice(index, 1);
        this._refs.splice(index, 1);

        if (this._files.length === 0) {
            this._invalid = false;
        }

        this._syncNativeInput();
        this._renderList();
        this._showMessage();
        this._emitChange();
    }

    _openPicker() {
        const picker = document.createElement("input");
        picker.type = "file";
        picker.multiple = this.multiple;

        if (this._accept !== "") {
            setAttributes(picker, { accept: this._accept });
        }

        picker.addEventListener("change", () => {
            this._ingest(picker.files ? Array.from(picker.files) : [], true);
        });

        if (typeof picker.click === "function") {
            picker.click();
        }
    }

    _setupDrag() {
        let depth = 0;

        this.row.addEventListener("dragenter", (event) => {
            if (event) {
                event.preventDefault();
            }
            depth += 1;
            this.row.classList.add("pth-dragging");
        });

        this.row.addEventListener("dragover", (event) => {
            if (event) {
                event.preventDefault();
            }
        });

        this.row.addEventListener("dragleave", (event) => {
            if (event) {
                event.preventDefault();
            }
            depth -= 1;
            if (depth <= 0) {
                depth = 0;
                this.row.classList.remove("pth-dragging");
            }
        });

        this.row.addEventListener("drop", (event) => {
            if (event) {
                event.preventDefault();
            }
            depth = 0;
            this.row.classList.remove("pth-dragging");
            const dropped = event && event.dataTransfer
                ? Array.from(event.dataTransfer.files)
                : [];
            this._ingest(dropped, true);
        });
    }

    _formatSize(bytes) {
        if (typeof bytes !== "number" || !Number.isFinite(bytes) || bytes < 0) {
            return null;
        }

        if (bytes === 0) {
            return "0 B";
        }

        const units = ["B", "KB", "MB", "GB", "TB"];
        const power = Math.min(
            Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
        const scaled = bytes / (1024 ** power);

        return `${Math.round(scaled * 100) / 100} ${units[power]}`;
    }

    _renderList() {
        this.list.replaceChildren();

        if (this._files.length === 0) {
            this.list.hidden = true;
            return;
        }

        this.list.hidden = false;

        this._files.forEach((file, index) => {
            const item = document.createElement("div");
            item.className = "pth-file-item";

            const info = document.createElement("div");
            info.className = "pth-file-info";

            const name = document.createElement("span");
            name.className = "pth-file-name";
            name.textContent = file.name;
            name.setAttribute("title", file.name);
            info.append(name);

            const size = this._formatSize(file.size);

            if (size !== null) {
                const sizeEl = document.createElement("span");
                sizeEl.className = "pth-file-size";
                sizeEl.textContent = size;
                info.append(sizeEl);
            }

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "pth-file-remove";
            remove.textContent = "×";
            remove.setAttribute(
                "aria-label", `${this.currentRemoveLabel} ${index + 1}`);
            remove.addEventListener("click", () => this._removeAt(index));

            item.append(info, remove);
            this.list.append(item);
        });
    }

    _renderCurrent() {
        this.current.replaceChildren();

        if (this._current === null) {
            this.current.hidden = true;
            this.row.hidden = false;
            this.restore.hidden = this._stashedCurrent === null;
            return;
        }

        this.current.hidden = false;
        this.row.hidden = true;
        this.restore.hidden = true;

        for (const label of this._current) {
            const item = document.createElement("span");
            item.className = "pth-file-current-label";
            item.textContent = this.currentLabel.replace("{value}", label);
            this.current.append(item);
        }

        const replace = document.createElement("button");
        replace.type = "button";
        replace.className = "pth-file-current-replace";
        replace.textContent = this.currentReplaceLabel;
        replace.addEventListener("click", () => this._beginReplace());
        this.current.append(replace);
    }

    showErrors() {
        this.touched = true;
        this._showMessage();
    }

    _showMessage() {
        renderMessage(
            this.message, this.input, this.touched ? this.error() : null);
    }
}


export class StrWidget extends Widget {
    constructor({
        minLength = STR_DEFAULTS.minLength,
        maxLength = STR_DEFAULTS.maxLength,
        pattern = STR_DEFAULTS.pattern,
        patternMessage = STR_DEFAULTS.patternMessage,
        minMessage = STR_DEFAULTS.minMessage,
        maxMessage = STR_DEFAULTS.maxMessage,
        placeholder = STR_DEFAULTS.placeholder,
        password = STR_DEFAULTS.password,
        rows = STR_DEFAULTS.rows,
        value = "",
    } = {}) {
        super();

        this.minLength = minLength;
        this.maxLength = maxLength;
        this.pattern = pattern;
        this.patternMessage = patternMessage;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;
        this.regexp = null;

        if (rows !== null && password) {
            throw new TypeError("StrWidget cannot be a textarea and a password at once");
        }

        if (rows !== null && (!Number.isSafeInteger(rows) || rows <= 0)) {
            throw new TypeError("StrWidget rows must be a positive safe integer");
        }

        if (pattern !== null) {
            try {
                this.regexp = new RegExp(`^(?:${pattern})$`, "u");
            } catch (error) {
                throw new TypeError(
                    `StrWidget cannot compile pattern ${pattern}: ${error.message}`);
            }
        }

        this.el = document.createElement("div");
        this.el.className = "pth-str";

        if (rows === null) {
            this.input = document.createElement("input");
            this.input.type = password ? "password" : "text";
        } else {
            this.input = document.createElement("textarea");
            this.input.setAttribute("rows", String(rows));
        }

        setAttributes(this.input, {
            title: pattern === null ? null : patternMessage,
            placeholder,
        });
        this.input.value = value;

        this.picker = null;

        if (rows === null && pattern === COLOR_PATTERN) {
            this.picker = document.createElement("input");
            this.picker.type = "color";
            this.picker.className = "pth-str-picker";
            this.picker.setAttribute("aria-label", "Color picker");

            const row = document.createElement("div");
            row.className = "pth-str-row";
            row.append(this.input, this.picker);
            this.el.append(row);

            this.picker.addEventListener("input", () => {
                this.input.value = this.picker.value;
                this._handleInput();
            });
        } else {
            this.el.append(this.input);
        }

        this.message = createMessage("pth-str-message");
        this.el.append(this.message);

        this.touched = false;
        this.input.addEventListener("input", () => this._handleInput());
        this._syncPicker();
        this._showMessage();
    }

    _handleInput() {
        this.touched = true;
        this._syncPicker();
        this._showMessage();
        this._emitChange();
    }

    _syncPicker() {
        if (this.picker === null) {
            return;
        }

        const value = this.input.value;

        if (this._matchesPattern(value)) {
            this.picker.value = value.toLowerCase();
        }
    }

    control() {
        return this.input;
    }

    value() {
        return this.input.value;
    }

    _check(value) {
        if (typeof value !== "string") {
            throw new TypeError("StrWidget.setValue expects a string");
        }
    }

    _apply(value) {
        this.input.value = value;
        this._syncPicker();
        this._showMessage();
    }

    isEmpty() {
        return false;
    }

    matchesPattern() {
        return this._matchesPattern(this.input.value);
    }

    _matchesPattern(value) {
        if (this.regexp === null) {
            return true;
        }

        return this.regexp.test(value);
    }

    error() {
        const length = stringLength(this.input.value);

        if (this.minLength !== null && length < this.minLength) {
            return withValue(this.minMessage, this.minLength);
        }

        if (this.maxLength !== null && length > this.maxLength) {
            return withValue(this.maxMessage, this.maxLength);
        }

        if (!this.matchesPattern()) {
            return this.patternMessage;
        }

        return null;
    }

    showErrors() {
        this.touched = true;
        this._showMessage();
    }

    _showMessage() {
        renderMessage(this.message, this.input, this.touched ? this.error() : null);
    }
}


export class IntWidget extends Widget {
    constructor({
        min = INT_DEFAULTS.min,
        max = INT_DEFAULTS.max,
        multipleOf = INT_DEFAULTS.multipleOf,
        step = INT_DEFAULTS.step,
        slider = INT_DEFAULTS.slider,
        showValue = true,
        placeholder = INT_DEFAULTS.placeholder,
        safeMessage = INT_DEFAULTS.safeMessage,
        invalidMessage = INT_DEFAULTS.invalidMessage,
        minMessage = INT_DEFAULTS.minMessage,
        maxMessage = INT_DEFAULTS.maxMessage,
        multipleOfMessage = INT_DEFAULTS.multipleOfMessage,
        increaseLabel = INT_DEFAULTS.increaseLabel,
        decreaseLabel = INT_DEFAULTS.decreaseLabel,
        value = "",
    } = {}) {
        super();

        if (slider && (min === null || max === null)) {
            throw new TypeError("IntWidget needs min and max to render a slider");
        }

        if (step !== null && (!Number.isSafeInteger(step) || step <= 0)) {
            throw new TypeError("IntWidget step must be a positive safe integer");
        }

        if (multipleOf !== null
                && (!Number.isSafeInteger(multipleOf) || multipleOf <= 0)) {
            throw new TypeError(
                "IntWidget multipleOf must be a positive safe integer");
        }

        this.min = min;
        this.max = max;
        this.multipleOf = multipleOf;
        this.stepAmount = step ?? multipleOf ?? 1;
        this.safeMessage = safeMessage;
        this.invalidMessage = invalidMessage;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;
        this.multipleOfMessage = multipleOfMessage;

        this.el = document.createElement("div");
        this.el.className = "pth-int";

        this.slider = slider;
        this.input = document.createElement("input");
        this.readout = null;

        if (slider) {
            const grid = step ?? 1;

            this.sliderStride = grid;
            this.input.type = "range";
            setAttributes(this.input, {
                min,
                max,
                step: grid,
            });
            this.input.value = value === ""
                ? String(this._initialSliderValue(min, max, grid))
                : String(value);

            this.el.append(this.input);

            if (showValue) {
                this.readout = document.createElement("output");
                this.readout.className = "pth-int-value";
                this.el.append(this.readout);
            }
        } else {
            this.input.type = "text";
            this.input.setAttribute("inputmode", "numeric");
            setAttributes(this.input, { placeholder });
            this.input.value = value === "" ? "" : String(value);

            const wrapper = document.createElement("div");
            wrapper.className = "pth-number";
            wrapper.append(this.input);

            const controls = document.createElement("div");
            controls.className = "pth-number-controls";
            controls.append(
                this._stepButton("▲", increaseLabel, 1),
                this._stepButton("▼", decreaseLabel, -1));
            wrapper.append(controls);

            this.el.append(wrapper);

            this.input.addEventListener("keydown", (event) => {
                if (!event) {
                    return;
                }

                if (event.key === "ArrowUp") {
                    event.preventDefault();
                    this._step(1);
                } else if (event.key === "ArrowDown") {
                    event.preventDefault();
                    this._step(-1);
                }
            });
        }

        this.message = createMessage("pth-int-message");
        this.el.append(this.message);

        this.touched = false;
        this.input.addEventListener("input", () => {
            this.touched = true;
            this._showMessage();
            this._emitChange();
        });
        this._showMessage();
    }

    _initialSliderValue(min, max, stride) {
        if (this.multipleOf === null) {
            return min;
        }

        const first = firstSliderValue(min, max, stride, this.multipleOf);

        if (first === null) {
            throw new TypeError(
                "IntWidget slider has no reachable position that is a "
                + "multiple of multipleOf");
        }

        return first;
    }

    _stepButton(glyph, label, direction) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "pth-number-btn";
        button.textContent = glyph;
        button.setAttribute("aria-label", label);
        button.addEventListener("click", () => this._step(direction));

        return button;
    }

    _step(direction) {
        const current = this.number() ?? 0;
        let next = current + this.stepAmount * direction;

        if (this.max !== null && next > this.max) {
            next = this.max;
        }

        if (this.min !== null && next < this.min) {
            next = this.min;
        }

        if (next === current) {
            return;
        }

        this.input.value = String(next);
        this.input.dispatchEvent(new Event("input"));
    }

    control() {
        return this.input;
    }

    _parse() {
        const text = this.input.value.trim();

        if (text === "") {
            return { kind: "empty", value: null };
        }

        if (!INTEGER.test(text)) {
            return { kind: "invalid", value: null };
        }

        const integer = BigInt(text);

        if (integer < MIN_SAFE_BIGINT || integer > MAX_SAFE_BIGINT) {
            return { kind: "unsafe", value: null };
        }

        return { kind: "value", value: Number(integer) };
    }

    number() {
        return this._parse().value;
    }

    value() {
        return this._parse().value;
    }

    _check(value) {
        if (value === null) {
            if (this.slider) {
                throw new TypeError("slider value must be a safe integer");
            }
            return;
        }

        if (typeof value !== "number" || !Number.isSafeInteger(value)) {
            throw new TypeError(
                "IntWidget.setValue expects a safe integer or null");
        }

        if (this.slider) {
            if (value < this.min || value > this.max) {
                throw new TypeError(
                    `slider value ${value} is outside ${this.min}..${this.max}`);
            }

            if (!onSliderGrid(value, this.min, this.sliderStride)) {
                throw new TypeError(
                    `slider value ${value} is not on the grid stepping by `
                    + `${this.sliderStride} from ${this.min}`);
            }
        }
    }

    _apply(value) {
        this.input.value = value === null ? "" : String(value);
        this._showMessage();
    }

    isEmpty() {
        return this.input.value.trim() === "";
    }

    error() {
        const state = this._parse();

        if (state.kind === "empty") {
            return null;
        }

        if (state.kind === "invalid") {
            return this.invalidMessage;
        }

        if (state.kind === "unsafe") {
            return this.safeMessage;
        }

        const number = state.value;

        if (this.min !== null && number < this.min) {
            return withValue(this.minMessage, this.min);
        }

        if (this.max !== null && number > this.max) {
            return withValue(this.maxMessage, this.max);
        }

        if (this.multipleOf !== null && number % this.multipleOf !== 0) {
            return withValue(this.multipleOfMessage, this.multipleOf);
        }

        return null;
    }

    showErrors() {
        this.touched = true;
        this._showMessage();
    }

    _showMessage() {
        if (this.readout !== null) {
            this.readout.textContent = this.input.value;
        }

        renderMessage(this.message, this.input, this.touched ? this.error() : null);
    }
}


export class FloatWidget extends Widget {
    constructor({
        min = FLOAT_DEFAULTS.min,
        max = FLOAT_DEFAULTS.max,
        minExclusive = FLOAT_DEFAULTS.minExclusive,
        maxExclusive = FLOAT_DEFAULTS.maxExclusive,
        step = FLOAT_DEFAULTS.step,
        placeholder = FLOAT_DEFAULTS.placeholder,
        invalidMessage = FLOAT_DEFAULTS.invalidMessage,
        finiteMessage = FLOAT_DEFAULTS.finiteMessage,
        minMessage = FLOAT_DEFAULTS.minMessage,
        maxMessage = FLOAT_DEFAULTS.maxMessage,
        increaseLabel = FLOAT_DEFAULTS.increaseLabel,
        decreaseLabel = FLOAT_DEFAULTS.decreaseLabel,
        value = "",
    } = {}) {
        super();

        if (step !== null
                && (typeof step !== "number" || !Number.isFinite(step) || step <= 0)) {
            throw new TypeError("FloatWidget step must be a positive finite number");
        }

        if (typeof value === "number" && !isWritableFloat(value)) {
            throw new TypeError(
                "FloatWidget value must be a number JavaScript writes as a "
                + "simple decimal, not exponent notation");
        }

        this.min = min;
        this.max = max;
        this.minExclusive = minExclusive;
        this.maxExclusive = maxExclusive;
        this.stepAmount = step ?? 1;
        this.invalidMessage = invalidMessage;
        this.finiteMessage = finiteMessage;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;

        this.el = document.createElement("div");
        this.el.className = "pth-float";

        this.input = document.createElement("input");
        this.input.type = "text";
        this.input.setAttribute("inputmode", "decimal");
        setAttributes(this.input, { placeholder });
        this.input.value = value === "" ? "" : String(value);

        const wrapper = document.createElement("div");
        wrapper.className = "pth-number";
        wrapper.append(this.input);

        const controls = document.createElement("div");
        controls.className = "pth-number-controls";
        controls.append(
            this._stepButton("▲", increaseLabel, 1),
            this._stepButton("▼", decreaseLabel, -1));
        wrapper.append(controls);

        this.el.append(wrapper);

        this.input.addEventListener("keydown", (event) => {
            if (!event) {
                return;
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                this._step(1);
            } else if (event.key === "ArrowDown") {
                event.preventDefault();
                this._step(-1);
            }
        });

        this.message = createMessage("pth-float-message");
        this.el.append(this.message);

        this.touched = false;
        this.input.addEventListener("input", () => {
            this.touched = true;
            this._showMessage();
            this._emitChange();
        });
        this._showMessage();
    }

    _stepButton(glyph, label, direction) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "pth-number-btn";
        button.textContent = glyph;
        button.setAttribute("aria-label", label);
        button.addEventListener("click", () => this._step(direction));

        return button;
    }

    _step(direction) {
        const current = this.number() ?? 0;
        let next = current + this.stepAmount * direction;

        if (this.max !== null && next > this.max) {
            next = this.max;
        }

        if (this.min !== null && next < this.min) {
            next = this.min;
        }

        if (next === current || !isWritableFloat(next)) {
            return;
        }

        this.input.value = String(next);
        this.input.dispatchEvent(new Event("input"));
    }

    control() {
        return this.input;
    }

    _parse() {
        const text = this.input.value.trim();

        if (text === "") {
            return { kind: "empty", value: null };
        }

        if (!FLOAT.test(text)) {
            return { kind: "invalid", value: null };
        }

        const number = Number(text);

        if (!Number.isFinite(number)) {
            return { kind: "nonfinite", value: null };
        }

        return { kind: "value", value: number };
    }

    number() {
        return this._parse().value;
    }

    value() {
        return this._parse().value;
    }

    _check(value) {
        if (value === null) {
            return;
        }

        if (typeof value !== "number" || !Number.isFinite(value)) {
            throw new TypeError(
                "FloatWidget.setValue expects a finite number or null");
        }

        if (!isWritableFloat(value)) {
            throw new TypeError(
                "FloatWidget.setValue expects a number JavaScript writes as a "
                + "simple decimal, not exponent notation");
        }
    }

    _apply(value) {
        this.input.value = value === null ? "" : String(value);
        this._showMessage();
    }

    isEmpty() {
        return this.input.value.trim() === "";
    }

    error() {
        const state = this._parse();

        if (state.kind === "empty") {
            return null;
        }

        if (state.kind === "invalid") {
            return this.invalidMessage;
        }

        if (state.kind === "nonfinite") {
            return this.finiteMessage;
        }

        const number = state.value;

        if (this.min !== null) {
            const below = this.minExclusive
                ? number <= this.min
                : number < this.min;

            if (below) {
                return withValue(this.minMessage, this.min);
            }
        }

        if (this.max !== null) {
            const above = this.maxExclusive
                ? number >= this.max
                : number > this.max;

            if (above) {
                return withValue(this.maxMessage, this.max);
            }
        }

        return null;
    }

    showErrors() {
        this.touched = true;
        this._showMessage();
    }

    _showMessage() {
        renderMessage(this.message, this.input, this.touched ? this.error() : null);
    }
}


class IsoInput extends Widget {
    constructor({
        type, isValid, className, messageClass, what,
        min, max, minExclusive, maxExclusive, step,
        placeholder, invalidMessage, minMessage, maxMessage, value,
    }) {
        super();

        this.isValid = isValid;
        this.what = what;
        this.min = min;
        this.max = max;
        this.minExclusive = minExclusive;
        this.maxExclusive = maxExclusive;
        this.invalidMessage = invalidMessage;
        this.minMessage = minMessage;
        this.maxMessage = maxMessage;

        this.el = document.createElement("div");
        this.el.className = className;

        this.input = document.createElement("input");
        this.input.type = type;
        setAttributes(this.input, { min, max, step, placeholder });
        this.input.value = value === "" ? "" : String(value);
        this.el.append(this.input);

        this.message = createMessage(messageClass);
        this.el.append(this.message);

        this.touched = false;
        this.input.addEventListener("input", () => {
            this.touched = true;
            this._showMessage();
            this._emitChange();
        });
        this._showMessage();
    }

    control() {
        return this.input;
    }

    value() {
        return this.input.value === "" ? null : this.input.value;
    }

    isEmpty() {
        return this.input.value === "";
    }

    _check(value) {
        if (value === null) {
            return;
        }

        if (typeof value !== "string" || !this.isValid(value)) {
            throw new TypeError(
                `${this.what}.setValue expects a canonical ISO string or null`);
        }
    }

    _apply(value) {
        this.input.value = value === null ? "" : value;
        this._showMessage();
    }

    error() {
        const value = this.input.value;

        if (value === "") {
            return null;
        }

        if (!this.isValid(value)) {
            return this.invalidMessage;
        }

        if (this.min !== null) {
            const below = this.minExclusive ? value <= this.min : value < this.min;

            if (below) {
                return withValue(this.minMessage, this.min);
            }
        }

        if (this.max !== null) {
            const above = this.maxExclusive ? value >= this.max : value > this.max;

            if (above) {
                return withValue(this.maxMessage, this.max);
            }
        }

        return null;
    }

    showErrors() {
        this.touched = true;
        this._showMessage();
    }

    _showMessage() {
        renderMessage(this.message, this.input, this.touched ? this.error() : null);
    }
}


export class DateWidget extends IsoInput {
    constructor({
        min = DATE_DEFAULTS.min,
        max = DATE_DEFAULTS.max,
        placeholder = DATE_DEFAULTS.placeholder,
        invalidMessage = DATE_DEFAULTS.invalidMessage,
        minMessage = DATE_DEFAULTS.minMessage,
        maxMessage = DATE_DEFAULTS.maxMessage,
        value = "",
    } = {}) {
        super({
            type: "date", isValid: isValidIsoDate, className: "pth-date",
            messageClass: "pth-date-message", what: "DateWidget",
            min, max, minExclusive: false, maxExclusive: false, step: null,
            placeholder, invalidMessage, minMessage, maxMessage, value,
        });
    }
}


export class TimeWidget extends IsoInput {
    constructor({
        min = TIME_DEFAULTS.min,
        max = TIME_DEFAULTS.max,
        minExclusive = TIME_DEFAULTS.minExclusive,
        maxExclusive = TIME_DEFAULTS.maxExclusive,
        placeholder = TIME_DEFAULTS.placeholder,
        invalidMessage = TIME_DEFAULTS.invalidMessage,
        minMessage = TIME_DEFAULTS.minMessage,
        maxMessage = TIME_DEFAULTS.maxMessage,
        value = "",
    } = {}) {
        super({
            type: "time", isValid: isIsoTime, className: "pth-time",
            messageClass: "pth-time-message", what: "TimeWidget",
            min, max, minExclusive, maxExclusive, step: 1,
            placeholder, invalidMessage, minMessage, maxMessage, value,
        });
    }
}
