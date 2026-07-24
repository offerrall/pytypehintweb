import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";


const [, , sourcePath, modulePath] = process.argv;

const html = readFileSync(sourcePath, "utf-8");
const start = html.indexOf("// demo-error-helpers-start");
const end = html.indexOf("// demo-error-helpers-end");

if (start === -1 || end === -1) {
    process.stdout.write(JSON.stringify({
        found: false,
        results: [],
    }));
    process.exit(0);
}

const helpers = html.slice(start, end);

writeFileSync(modulePath,
              `${helpers}\nexport { readBody, describeFailure };\n`,
              "utf-8");

const { readBody, describeFailure } = await import(pathToFileURL(modulePath));


function fakeResponse(status, statusText, text) {
    return { status, statusText, ok: status < 400, text: async () => text };
}


const CASES = [
    ["demo envelope", 200, "OK", JSON.stringify({ ok: false, error: "TypeError: bad" })],
    ["fastapi detail string", 404, "Not Found", JSON.stringify({ detail: "Unknown form" })],
    ["fastapi detail list", 422, "Unprocessable Entity",
     JSON.stringify({ detail: [{ loc: ["body"], msg: "field required" }] })],
    ["non json", 500, "Internal Server Error", "<html>boom</html>"],
    ["empty body", 502, "Bad Gateway", ""],
];

const results = [];

for (const [name, status, statusText, text] of CASES) {
    const response = fakeResponse(status, statusText, text);
    const body = await readBody(response);

    results.push({ name, message: describeFailure(response, body) });
}

process.stdout.write(JSON.stringify({ found: true, results }));
