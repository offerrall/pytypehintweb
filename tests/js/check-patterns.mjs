import { readFileSync } from "node:fs";


const patterns = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const failed = [];

for (const pattern of patterns) {
    try {
        new RegExp(`^(?:${pattern})$`, "u");
    } catch (error) {
        failed.push({ pattern, error: error.message });
    }
}

process.stdout.write(JSON.stringify({ checked: patterns.length, failed }));
