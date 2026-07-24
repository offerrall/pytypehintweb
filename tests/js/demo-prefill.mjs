import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";


const [, , sourcePath, modulePath] = process.argv;

const html = readFileSync(sourcePath, "utf-8");
const start = html.indexOf("// demo-prefill-start");
const end = html.indexOf("// demo-prefill-end");

if (start === -1 || end === -1) {
    process.stdout.write(JSON.stringify({ found: false, results: [] }));
    process.exit(0);
}

const helper = html.slice(start, end);

writeFileSync(modulePath,
              `${helper}\nexport { prefillCandidates };\n`,
              "utf-8");

const { prefillCandidates } = await import(pathToFileURL(modulePath));


const CASES = [
    ["empty", ""],
    ["whitespace", "   "],
    ["integer", "12"],
    ["negative integer", "-5"],
    ["padded integer", " 7 "],
    ["malformed", "abc"],
    ["float-like", "1.5"],
];

const results = CASES.map(([name, raw]) => ({
    name,
    candidates: prefillCandidates(raw),
}));

process.stdout.write(JSON.stringify({ found: true, results }));
