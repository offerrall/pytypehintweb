import "./dom.mjs";

import { COLOR_PATTERN } from "../../src/pytypehintweb/static/inputs.js";


// Print the runtime value of the JS mirror constant so a Python test can pin it
// equal to pytypehintweb.COLOR_PATTERN. Comparing the exported value, not a
// regex over the source, keeps the pin from drifting on formatting.
process.stdout.write(JSON.stringify({ colorPattern: COLOR_PATTERN }));
