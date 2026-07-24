const FORBIDDEN_ATTRIBUTES =
    /^(?:on\w+|href|src|srcdoc|srcset|style|formaction|action|data|xlink:href)$/i;


class ClassList {
    constructor() {
        this.names = new Set();
    }

    add(...names) {
        for (const name of names) {
            this.names.add(name);
        }
    }

    remove(...names) {
        for (const name of names) {
            this.names.delete(name);
        }
    }

    contains(name) {
        return this.names.has(name);
    }
}


class FakeElement {
    constructor(tagName) {
        this.tagName = tagName.toUpperCase();
        this.children = [];
        this.parent = null;
        this.attributes = {};
        this.classList = new ClassList();
        this.listeners = new Map();
        this.textContent = "";
        this.className = "";
        this.value = "";
        this.type = "";
        this.id = "";
        this.hidden = false;
        this.disabled = false;
        this.checked = false;
    }

    append(...nodes) {
        for (const node of nodes) {
            node.parent = this;
            this.children.push(node);
        }
    }

    replaceChildren(...nodes) {
        this.children = [];
        this.append(...nodes);
    }

    remove() {
        if (this.parent === null) {
            return;
        }

        const index = this.parent.children.indexOf(this);

        if (index !== -1) {
            this.parent.children.splice(index, 1);
        }

        this.parent = null;
    }

    set innerHTML(value) {
        throw new Error(
            `innerHTML is not allowed: plan text must be inserted as text `
            + `(got ${JSON.stringify(String(value)).slice(0, 60)})`);
    }

    get innerHTML() {
        throw new Error("innerHTML is not allowed");
    }

    set outerHTML(value) {
        throw new Error("outerHTML is not allowed");
    }

    insertAdjacentHTML() {
        throw new Error("insertAdjacentHTML is not allowed");
    }

    setAttribute(name, value) {
        if (FORBIDDEN_ATTRIBUTES.test(name)) {
            throw new Error(`attribute is not allowed from plan text: ${name}`);
        }

        this.attributes[name] = value;
    }

    getAttribute(name) {
        return name in this.attributes ? this.attributes[name] : null;
    }

    hasAttribute(name) {
        return name in this.attributes;
    }

    removeAttribute(name) {
        delete this.attributes[name];
    }

    addEventListener(type, callback) {
        if (!this.listeners.has(type)) {
            this.listeners.set(type, new Set());
        }

        this.listeners.get(type).add(callback);
    }

    removeEventListener(type, callback) {
        const registered = this.listeners.get(type);

        if (registered !== undefined) {
            registered.delete(callback);
        }
    }

    dispatch(type) {
        for (const callback of [...(this.listeners.get(type) ?? [])]) {
            callback();
        }
    }

    dispatchEvent(event) {
        this.dispatch(event.type);
        return true;
    }
}


class FakeOption extends FakeElement {
    constructor(text, value) {
        super("option");
        this.text = text;
        this.value = value;
    }
}


globalThis.HTMLElement = FakeElement;
globalThis.Option = FakeOption;
globalThis.document = {
    createElement: (tagName) => new FakeElement(tagName),
    createElementNS: (_namespace, tagName) => new FakeElement(tagName),
};


export function type(widget, text) {
    widget.input.value = text;
    widget.input.dispatch("input");
}


export function select(widget, index) {
    widget.el.value = String(index);
    widget.el.dispatch("change");
}


export function walk(element) {
    const found = [element];

    for (const child of element.children) {
        found.push(...walk(child));
    }

    return found;
}


export function tagsIn(element) {
    return walk(element).map((node) => node.tagName);
}


export function texts(element, className) {
    const found = [];

    const walk = (node) => {
        if (node.className === className) {
            found.push(node.textContent);
        }

        for (const child of node.children) {
            walk(child);
        }
    };

    walk(element);

    return found;
}
