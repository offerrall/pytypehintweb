import tempfile
from contextlib import asynccontextmanager
from dataclasses import is_dataclass
from inspect import getsource
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from pytypehint import signature_of, struct_of
from pytypehintweb import STATIC, decode, plan_of
from pytypehintweb.demo.examples import CONFIGS, SECTIONS


def _schema(obj):
    if is_dataclass(obj):
        return struct_of(obj)
    return signature_of(obj)


def _source(obj, extra):
    return "\n\n".join(getsource(part).strip()
                       for part in (*extra, obj))


def _unique(forms):
    seen = set()

    for form in forms:
        if form[0] in seen:
            raise ValueError(f"duplicate demo form id: {form[0]}")
        seen.add(form[0])

    return forms


FORMS = _unique([form for _, _, _, forms in SECTIONS for form in forms])

SCHEMAS = {form[0]: _schema(form[3]) for form in FORMS}

PLANS = [
    {
        "id": section_id,
        "title": section_title,
        "what": section_what,
        "forms": [
            {
                "id": form_id,
                "title": title,
                "what": what,
                "source": _source(obj, extra),
                "plan": plan_of(SCHEMAS[form_id], config=CONFIGS.get(form_id)),
            }
            for form_id, title, what, obj, extra in forms
        ],
    }
    for section_id, section_title, section_what, forms in SECTIONS
]

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pytypehintweb demo</title>
<link rel="stylesheet" href="/static/widgets.css">
<style>
  /* Demo chrome, theme-aware. The widgets style themselves through widgets.css;
     these variables keep the surrounding page in step. The palette is defined
     once as --l-* / --d-* and mapped to --demo-* per theme: automatic through
     prefers-color-scheme, manual through [data-theme] set by the toggle. */
  :root {
    --l-bg: #ffffff; --d-bg: #0f1115;
    --l-fg: #111827; --d-fg: #e5e7eb;
    --l-muted: #64748b; --d-muted: #9ca3af;
    --l-card: #ffffff; --d-card: #1a1c22;
    --l-panel: #f8fafc; --d-panel: #14161b;
    --l-border: #e2e8f0; --d-border: #2a2f3a;
    --l-border-strong: #cbd5e1; --d-border-strong: #384152;
    --l-out-bg: #f4f4f5; --d-out-bg: #16181d;
    --l-accent: #2563eb; --d-accent: #60a5fa;
    --l-ok: #15803d; --d-ok: #4ade80;
    --l-bad: #b91c1c; --d-bad: #f87171;
    --l-send-bg: #334155; --d-send-bg: #475569;
    --l-hover: #f1f5f9; --d-hover: #21252e;
  }
  :root, :root[data-theme="light"] {
    --demo-bg: var(--l-bg); --demo-fg: var(--l-fg); --demo-muted: var(--l-muted);
    --demo-card: var(--l-card); --demo-panel: var(--l-panel);
    --demo-border: var(--l-border); --demo-border-strong: var(--l-border-strong);
    --demo-out-bg: var(--l-out-bg); --demo-accent: var(--l-accent);
    --demo-ok: var(--l-ok); --demo-bad: var(--l-bad);
    --demo-send-bg: var(--l-send-bg); --demo-hover: var(--l-hover);
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --demo-bg: var(--d-bg); --demo-fg: var(--d-fg); --demo-muted: var(--d-muted);
      --demo-card: var(--d-card); --demo-panel: var(--d-panel);
      --demo-border: var(--d-border); --demo-border-strong: var(--d-border-strong);
      --demo-out-bg: var(--d-out-bg); --demo-accent: var(--d-accent);
      --demo-ok: var(--d-ok); --demo-bad: var(--d-bad);
      --demo-send-bg: var(--d-send-bg); --demo-hover: var(--d-hover);
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --demo-bg: var(--d-bg); --demo-fg: var(--d-fg); --demo-muted: var(--d-muted);
    --demo-card: var(--d-card); --demo-panel: var(--d-panel);
    --demo-border: var(--d-border); --demo-border-strong: var(--d-border-strong);
    --demo-out-bg: var(--d-out-bg); --demo-accent: var(--d-accent);
    --demo-ok: var(--d-ok); --demo-bad: var(--d-bad);
    --demo-send-bg: var(--d-send-bg); --demo-hover: var(--d-hover);
    color-scheme: dark;
  }
  body { font-family: system-ui, sans-serif; max-width: 940px; margin: 2rem auto; padding: 0 1rem; color: var(--demo-fg); background: var(--demo-bg); }
  h1 { color: var(--demo-fg); }
  details { border: 1px solid var(--demo-border); border-radius: 8px; margin-bottom: .75rem; background: var(--demo-card); }
  details[open] { box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  summary { cursor: pointer; padding: .7rem 1rem; font-weight: 600; }
  summary .what { display: block; font-weight: 400; color: var(--demo-muted); font-size: .85rem; margin-top: .15rem; }
  .body { padding: 0 1rem 1rem; }
  .columns { display: flex; gap: 1rem; align-items: flex-start; flex-wrap: wrap; }
  .columns > * { flex: 1 1 340px; min-width: 0; }
  .source { background: #1e293b; color: #e2e8f0; border-radius: 6px; padding: .6rem .8rem; font: .78rem/1.5 ui-monospace, monospace; white-space: pre; overflow-x: auto; margin: 0 0 .8rem; }
  .out { background: var(--demo-out-bg); border: 1px solid var(--demo-border); border-radius: 6px; padding: .5rem .8rem; font: .78rem/1.5 ui-monospace, monospace; white-space: pre-wrap; color: var(--demo-fg); }
  .ok { color: var(--demo-ok); }
  .bad { color: var(--demo-bad); }
  button.send { margin: .5rem .4rem .5rem 0; padding: .35rem .8rem; cursor: pointer; border-radius: 5px; border: 1px solid transparent; background: var(--demo-send-bg); color: #fff; font-weight: 600; }
  button.send.ready { background: var(--demo-ok); border-color: var(--demo-ok); }
  button.send.pending { background: var(--demo-bad); border-color: var(--demo-bad); }
  button.reset { margin: .5rem 0; padding: .35rem .8rem; cursor: pointer; border-radius: 5px; border: 1px solid var(--demo-border-strong); background: var(--demo-card); color: var(--demo-fg); }
  button.reset:hover { background: var(--demo-hover); }
  details.section { border: 1px solid var(--demo-border-strong); border-radius: 10px; margin-bottom: 1rem; background: var(--demo-panel); scroll-margin-top: 1rem; }
  details.section > summary.section-title { font-size: 1.05rem; padding: .9rem 1rem; }
  details.section[open] > summary.section-title { border-bottom: 1px solid var(--demo-border); margin-bottom: .75rem; }
  details.section > details { margin: 0 .75rem .75rem; }
  details.plan { margin: 0 0 .8rem; background: var(--demo-panel); }
  details.plan > summary { font-size: .8rem; font-weight: 500; padding: .4rem .6rem; }
  details.plan pre { margin: 0; padding: .6rem .8rem; font: .75rem/1.45 ui-monospace, monospace; white-space: pre; overflow-x: auto; color: var(--demo-fg); }
  nav.index { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1.5rem; }
  nav.index a { padding: .3rem .7rem; border: 1px solid var(--demo-border); border-radius: 999px; font-size: .85rem; text-decoration: none; color: var(--demo-fg); background: var(--demo-card); }
  nav.index a:hover { background: var(--demo-hover); }
  p.legend { color: var(--demo-muted); font-size: .9rem; margin: 0 0 1.5rem; }
  header.page { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
  button.theme-toggle { flex-shrink: 0; padding: .4rem .8rem; cursor: pointer; border-radius: 999px; border: 1px solid var(--demo-border-strong); background: var(--demo-card); color: var(--demo-fg); font-size: .85rem; font-weight: 600; }
  button.theme-toggle:hover { background: var(--demo-hover); }
  /* Focus ring for the demo's own chrome only. Widget controls keep the
     focus indicator from widgets.css, so this must not reach inside them. */
  button.theme-toggle:focus-visible,
  nav.index a:focus-visible,
  button.send:focus-visible,
  button.reset:focus-visible,
  summary:focus-visible { outline: 2px solid var(--demo-accent); outline-offset: 2px; }
</style>
</head>
<body>

<header class="page">
  <h1>pytypehintweb demo</h1>
  <button id="theme-toggle" type="button" class="theme-toggle" aria-label="Toggle dark mode">◐ Theme</button>
</header>
<p class="legend">Each case shows the model source, the plan it generates, the
form mounted from that plan, its live state and what the core answers when it
receives the transport object.</p>

<div id="root"></div>

<script type="module">
  import { compileForm } from "/static/form.js";
  import { FileWidget } from "/static/inputs.js";

  const root = document.getElementById("root");

  const SAMPLE_RECORDS = {
    "file-edit": { name: "Ada Lovelace", avatar: "avatars/ada-lovelace.jpg" },
    "file-list-edit": {
      title: "Summer 2011",
      photos: ["albums/summer/beach.jpg", "albums/summer/sunset.jpg"],
    },
  };

  document.getElementById("theme-toggle").addEventListener("click", () => {
    const el = document.documentElement;
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const current = el.getAttribute("data-theme") ?? (dark ? "dark" : "light");
    el.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  });

  // demo-error-helpers-start
  async function readBody(response) {
    const text = await response.text();

    try {
      return { text, data: JSON.parse(text) };
    } catch {
      return { text, data: null };
    }
  }

  function describeFailure(response, body) {
    const data = body.data;

    if (data !== null && typeof data === "object") {
      if (typeof data.error === "string") {
        return data.error;
      }

      if (data.detail !== undefined) {
        return typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail, null, 2);
      }
    }

    const trimmed = body.text.trim();

    if (trimmed !== "") {
      return `HTTP ${response.status}: ${trimmed.slice(0, 500)}`;
    }

    return `HTTP ${response.status} ${response.statusText}`;
  }
  // demo-error-helpers-end

  async function uploadFile(file, reference) {
    const body = new FormData();
    body.append("reference", reference);
    body.append("file", file);

    const response = await fetch("/upload", { method: "POST", body });

    if (!response.ok) {
      throw new Error(`upload failed: HTTP ${response.status}`);
    }
  }

  const wiredUploads = new WeakSet();
  const uploaded = new WeakMap();
  const uploading = new WeakMap();

  function eachFileWidget(widget, visit) {
    if (widget instanceof FileWidget) {
      visit(widget);
      return;
    }

    if (widget.widget) eachFileWidget(widget.widget, visit);
    for (const child of widget.children ?? []) eachFileWidget(child.widget, visit);
    for (const item of widget.items ?? []) eachFileWidget(item.widget, visit);
    for (const branch of widget.branches ?? []) eachFileWidget(branch.widget, visit);
  }

  function currentPairs(widget) {
    const value = widget.value();
    if (value === null) return [];

    if (widget.multiple) {
      const files = widget.files();
      if (files.length !== value.length) return [];
      return files.map((file, i) => ({ file, reference: value[i] }));
    }

    const file = widget.file();
    return file === null ? [] : [{ file, reference: value }];
  }

  function uploadsSettled(form) {
    let settled = true;

    for (const field of form.fields) {
      eachFileWidget(field.widget, (widget) => {
        if ((uploading.get(widget) ?? 0) > 0) { settled = false; return; }

        const stored = uploaded.get(widget) ?? new Set();
        if (currentPairs(widget).some(({ reference }) => !stored.has(reference))) {
          settled = false;
        }
      });
    }

    return settled;
  }

  function wireUploads(form, onSettleChange) {
    for (const field of form.fields) {
      eachFileWidget(field.widget, (widget) => {
        if (wiredUploads.has(widget)) return;
        wiredUploads.add(widget);

        widget.onChange(async () => {
          const stored = uploaded.get(widget) ?? new Set();
          uploaded.set(widget, stored);

          for (const { file, reference } of currentPairs(widget)) {
            if (stored.has(reference)) continue;

            uploading.set(widget, (uploading.get(widget) ?? 0) + 1);
            onSettleChange();

            try {
              await uploadFile(file, reference);
              stored.add(reference);
            } catch {
            } finally {
              uploading.set(widget, (uploading.get(widget) ?? 1) - 1);
              onSettleChange();
            }
          }
        });
      });
    }
  }

  // demo-prefill-start
  function prefillCandidates(raw) {
    if (raw.trim() === "") {
      return [];
    }

    const candidates = [raw];

    if (/^-?\d+$/.test(raw.trim())) {
      candidates.push(Number(raw.trim()));
    }

    return candidates;
  }
  // demo-prefill-end

  function renderPlan(plan, body) {
    const box = document.createElement("details");
    box.className = "plan";

    const summary = document.createElement("summary");
    summary.textContent = "Plan";
    box.append(summary);

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(plan, null, 2);
    box.append(pre);

    body.append(box);
  }

  function paint(form, output, send) {
    const value = form.fields.map((field) => [field.name, field.widget.value()]);
    const ready = form.isReady();
    const settled = uploadsSettled(form);
    const canSend = ready && settled;

    send.className = `send ${canSend ? "ready" : "pending"}`;
    send.disabled = !canSend;

    output.textContent =
      `ready    = ${ready}\n`
      + `uploaded = ${settled}\n`
      + `hasError = ${form.hasError()}\n\n`
      + `value:\n${JSON.stringify(Object.fromEntries(value), null, 2)}\n\n`
      + `read:\n${JSON.stringify(form.read(), null, 2)}`;
  }

  function mountForm(entry, host, output, send) {
    const form = compileForm(entry.plan, { prefix: entry.id });

    host.replaceChildren();

    if (form.description !== null) {
      const doc = document.createElement("p");
      doc.className = "what";
      doc.textContent = form.description;
      host.append(doc);
    }

    for (const field of form.fields) host.append(field.widget.el);

    const record = SAMPLE_RECORDS[entry.id];
    if (record !== undefined) {
      for (const field of form.fields) {
        if (field.name in record) {
          try {
            field.widget.widget.setValue(record[field.name]);
          } catch {
          }
        }
      }
    }

    const params = new URLSearchParams(location.search);
    for (const field of form.fields) {
      if (!params.has(field.name)) continue;

      for (const candidate of prefillCandidates(params.get(field.name))) {
        try {
          field.widget.widget.setValue(candidate);
          break;
        } catch {
        }
      }
    }

    const repaint = () => paint(form, output, send);
    wireUploads(form, repaint);

    const releasePaint = form.onChange(repaint);
    const releaseWire = form.onChange(() => wireUploads(form, repaint));
    repaint();

    return {
      form,
      release: () => { releasePaint(); releaseWire(); },
    };
  }

  function renderCase(entry, position, group) {
    const box = document.createElement("details");
    box.id = `case-${entry.id}`;

    const summary = document.createElement("summary");
    summary.textContent = `${position}  ${entry.title}`;

    const what = document.createElement("span");
    what.className = "what";
    what.textContent = entry.what;
    summary.append(what);
    box.append(summary);

    const body = document.createElement("div");
    body.className = "body";
    box.append(body);

    const source = document.createElement("pre");
    source.className = "source";
    source.textContent = entry.source;
    body.append(source);

    renderPlan(entry.plan, body);

    const columns = document.createElement("div");
    columns.className = "columns";
    body.append(columns);

    const left = document.createElement("div");
    const right = document.createElement("div");
    columns.append(left, right);

    const output = document.createElement("div");
    output.className = "out";

    const send = document.createElement("button");
    send.type = "button";
    send.className = "send";
    send.textContent = "Send to the core";

    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "reset";
    reset.textContent = "Reset";

    const answer = document.createElement("div");
    answer.className = "out";
    answer.setAttribute("role", "status");
    answer.setAttribute("aria-live", "polite");

    right.append(output, send, reset, answer);

    let mounted = mountForm(entry, left, output, send);

    send.addEventListener("click", async () => {
      try {
        const response = await fetch(`/build/${entry.id}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(mounted.form.read()),
        });

        const body = await readBody(response);
        const ok = response.ok && body.data !== null && body.data.ok === true;

        answer.className = `out ${ok ? "ok" : "bad"}`;
        answer.textContent = ok
          ? body.data.built
          : describeFailure(response, body);
      } catch (error) {
        answer.className = "out bad";
        answer.textContent = `Network error: ${error.message}`;
      }
    });

    reset.addEventListener("click", () => {
      mounted.release();
      mounted = mountForm(entry, left, output, send);
      answer.className = "out";
      answer.textContent = "";
    });

    group.append(box);
  }

  function renderSection(section, position, index) {
    const group = document.createElement("details");
    group.className = "section";
    group.id = section.id;
    root.append(group);

    const heading = document.createElement("summary");
    heading.className = "section-title";
    heading.textContent =
      `${position}. ${section.title}  ·  ${section.forms.length} cases`;

    const intro = document.createElement("span");
    intro.className = "what";
    intro.textContent = section.what;
    heading.append(intro);
    group.append(heading);

    const anchor = document.createElement("a");
    anchor.href = `#${section.id}`;
    anchor.textContent = `${section.title} (${section.forms.length})`;
    anchor.addEventListener("click", () => { group.open = true; });
    index.append(anchor);

    section.forms.forEach((entry, i) => {
      renderCase(entry, `${position}.${i + 1}`, group);
    });
  }

  async function loadSections() {
    const response = await fetch("/plans");

    if (!response.ok) {
      throw new Error(`/plans returned ${response.status}`);
    }

    return response.json();
  }

  try {
    const sections = await loadSections();

    const index = document.createElement("nav");
    index.className = "index";
    root.append(index);

    sections.forEach((section, i) => renderSection(section, i + 1, index));

    const openTo = (hash) => {
      if (!hash) return;

      const target = document.getElementById(hash.slice(1));
      if (target === null) return;

      for (let el = target; el !== null; el = el.parentElement) {
        if (el.tagName === "DETAILS") el.open = true;
      }

      target.scrollIntoView();
    };

    addEventListener("hashchange", () => openTo(location.hash));
    openTo(location.hash);
  } catch (error) {
    const failure = document.createElement("div");
    failure.className = "out bad";
    failure.setAttribute("role", "alert");
    failure.textContent = `Could not load the plans: ${error.message}`;
    root.append(failure);
  }
</script>
</body>
</html>
"""

ON_STARTUP = []


@asynccontextmanager
async def lifespan(_app):
    for hook in ON_STARTUP:
        hook()

    yield


app = FastAPI(title="pytypehintweb demo", lifespan=lifespan)

NO_CACHE = {"Cache-Control": "no-store, max-age=0"}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(HTML, headers=NO_CACHE)


@app.get("/plans")
def plans():
    return JSONResponse(PLANS, headers=NO_CACHE)


@app.post("/build/{form_id}")
async def build(form_id: str, data: dict):
    schema = SCHEMAS.get(form_id)

    if schema is None:
        return JSONResponse({"ok": False, "error": "Unknown form"},
                            status_code=404, headers=NO_CACHE)

    # Demo infrastructure only: a real host defines its own error policy. Here
    # any build failure becomes a readable envelope instead of an opaque 500,
    # while `except Exception` still lets BaseException propagate.
    try:
        resolved = schema.build(decode(schema, data))
        return JSONResponse({"ok": True, "built": repr(resolved)},
                            headers=NO_CACHE)
    except Exception as e:  # noqa: BLE001 - demo endpoint, isolated on purpose
        return JSONResponse({"ok": False, "error": f"{type(e).__name__}: {e}"},
                            headers=NO_CACHE)


UPLOADS = Path(tempfile.gettempdir()) / "pytypehintweb-demo-uploads"


@app.post("/upload")
async def upload(reference: str = Form(...), file: UploadFile = File(...)):
    # Demo infrastructure only: a toy channel standing in for the host's own. The
    # widget already minted the reference; the host stores the bytes labelled
    # with it. A real host owns storage, size limits, auth and how far it trusts
    # a client-supplied reference — `Path(...).name` is all this one does.
    UPLOADS.mkdir(parents=True, exist_ok=True)
    (UPLOADS / Path(reference).name).write_bytes(await file.read())

    return JSONResponse({"ok": True}, headers=NO_CACHE)


MEDIA_TYPES = {
    ".js": "text/javascript",
    ".css": "text/css",
}


@app.get("/static/{name}")
def static(name: str):
    path = (STATIC / name).resolve()
    media_type = MEDIA_TYPES.get(path.suffix)

    if (path.parent != Path(STATIC).resolve()
            or media_type is None
            or not path.is_file()):
        return Response("not found", status_code=404)

    return Response(
        path.read_text(encoding="utf-8"),
        media_type=media_type,
        headers=NO_CACHE,
    )
