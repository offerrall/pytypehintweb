import { readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = join(HERE, "..", "..", "src", "pytypehintweb", "static");

export const MODULES = [
    "defaults.js",
    "slider.js",
    "iso.js",
    "normalize.js",
    "contract.js",
    "fields.js",
    "inputs.js",
    "form.js",
];

const EXPORT = /^export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z0-9_$]+)/gm;
const EXPORT_LIST = /^export\s*\{([^}]*)\}/gm;


function countExports(source) {
    const names = new Set();

    for (const match of source.matchAll(EXPORT)) {
        names.add(match[1]);
    }

    for (const match of source.matchAll(EXPORT_LIST)) {
        for (const part of match[1].split(",")) {
            const name = part.trim().split(/\s+as\s+/).pop().trim();

            if (name) {
                names.add(name);
            }
        }
    }

    return names.size;
}


export function measure() {
    const files = MODULES.map((name) => {
        const source = readFileSync(join(STATIC, name));
        const text = source.toString("utf8");

        return {
            name,
            raw: source.length,
            gzip: gzipSync(source, { level: 9 }).length,
            exports: countExports(text),
        };
    });

    const raw = files.reduce((sum, file) => sum + file.raw, 0);
    const gzip = files.reduce((sum, file) => sum + file.gzip, 0);

    return { files, raw, gzip };
}


function pad(value, width) {
    return String(value).padStart(width);
}


function main() {
    const { files, raw, gzip } = measure();

    console.log("module          raw   gzip  exports");
    console.log("------------  -----  -----  -------");

    for (const file of files) {
        console.log(
            `${file.name.padEnd(12)}  ${pad(file.raw, 5)}  `
            + `${pad(file.gzip, 5)}  ${pad(file.exports, 7)}`);
    }

    console.log("------------  -----  -----  -------");
    console.log(`${"total".padEnd(12)}  ${pad(raw, 5)}  ${pad(gzip, 5)}`);
}


if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main();
}
