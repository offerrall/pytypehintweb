import test from "node:test";
import assert from "node:assert/strict";

import { MODULES, measure } from "./size-report.mjs";

// The budget catches accidental bloat (a copied library, embedded demo content),
// not legitimate feature growth. Adding the date and time scalars — two node
// checks, two widgets over a shared IsoInput base, their validators and
// defaults — grew the runtime proportionately, so the ceilings were raised to
// keep roughly one scalar type of headroom. See CHANGELOG (date/time slice).
// The per-file ceiling was raised again for the StrWidget colour assistant
// (Color/Email slice): a picker element, its sync, and the opt-in constant.
// Raised once more for the file slice (the last vocabulary piece): a FileWidget
// with its three states, its node check and default, and the file defaults. The
// per-file ceiling was raised again when the file field grew a `multiple` mode
// (list[File] as one widget) and a setValue "current file" display.
// Raised a final time when the file field's presentation grew to the accumulate
// UX: per-file cards with sizes, the + button, per-file removal and drag & drop
// (all presentation over the same value contract).
// Nudged once more for showErrors() across every widget (the submit-time reveal)
// plus the file field's current-file Replace control and its touched gating.
// And again for the current-file ↺ restore (stash the replaced reference and
// undo back to it).
// Nudged once more for the reserved field-name safety fixes: object
// value()/read() and plan defaults write keys as own data properties
// (putKey/ownValue) so a field literally named "__proto__" survives transport
// instead of hitting the prototype setter, and normalizeField rejects the
// transport-reserved "$type"/"$value" names. Both are small correctness fixes,
// not bloat.
// Only the gzip ceiling was nudged, for iso.js: a date is now validated as a
// real calendar date rather than by shape alone, and the check lives in its own
// dependency-free leaf so the plan validator and DateWidget share one
// implementation instead of two regexes that can drift. Measured with LF
// endings, that shared guarantee cost raw 133_813 -> 135_517 (+1_704: the new
// module 1_580, its imports and the predicate swap 124) and gzip 29_986 ->
// 30_879 (+893). The increase is the date validation itself, not a line-ending
// conversion — .gitattributes pins *.js and *.css to LF, so these totals are
// identical on Windows, Linux and macOS whatever core.autocrlf a checkout uses.
// The raw ceiling still holds unchanged; only gzip needed the room.
// Nudged again for two guards that stop a control holding a value nobody asked
// for: FloatWidget refuses a number JavaScript only prints as an exponent
// (1e-7 would land as text its own grammar rejects), and a slider refuses a
// value off its grid or outside its bounds instead of letting the browser snap
// or clamp it silently. The grid rule moved into slider.js as onSliderGrid, so
// checkPlan and the widget read one implementation, and enum/file normalizers
// now copy their arrays instead of aliasing the input. Measured with LF: raw
// 135_517 -> 138_059 (+2_542) and gzip 30_879 -> 31_657 (+778), spread over
// inputs.js (+2_015), slider.js (+372), normalize.js (+147) and contract.js (+8).
// Nudged once more for the 0.0.1 release pass: containers reject setValue()
// plainly instead of leaking "_check", the mode navigator keeps focus reachable
// at the extremes, a null Field description mints nothing, an uncompilable
// StrWidget pattern throws at construction (dropping the dead patternError path),
// and the file add/remove buttons carry distinguishable accessible names. All in
// fields.js (+1_523) and inputs.js (+725). Measured with LF: raw 138_059 ->
// 140_307 and gzip 31_657 -> 32_413.
// Nudged for 0.0.2: a minted file reference now leads with the chosen file's own
// name, compressed to bare ASCII and capped at 15 characters (asciiSlug plus
// mintFileReference, the small folding table included), so a storage listing
// reads as names rather than as bare hashes. All in inputs.js. Measured with LF:
// raw 140_307 -> 141_195 (+888) and gzip 32_413 -> 32_802 (+389).
// Nudged again for uploads(): a widget now reports the local files a host still
// has to upload, as { reference, file, complete }. FileWidget pairs the refs it
// already mints with the Files it already holds and remembers which ones a host
// confirmed; the containers aggregate their children's, so a host never walks
// the plan looking for file nodes. Measured with LF: raw 141_195 -> 143_130
// (+1_935, spread over inputs.js +862, fields.js +1_005 and form.js +68) and
// gzip 32_802 -> 33_337 (+535).
// Lowered for the comment strip: the shipped modules carry no comments at all,
// because they are served as they are, with no build step, so every explanatory
// line was download weight on every page. The reasoning they held lives in
// docs/, which is where a reader looks for it. Nothing else changed — same
// tokens, same behaviour, whole suite green. Measured with LF: raw 143_130 ->
// 116_829 (-26_301) and gzip 33_337 -> 21_939 (-11_398). The ceilings drop with
// them, keeping roughly the same headroom as before so the budget still catches
// bloat instead of quietly absorbing it.
const RAW_CEILING = 118_000;
const GZIP_CEILING = 22_400;
const PER_FILE_RAW_CEILING = 45_000;


test("the runtime ships exactly the expected modules", () => {
    const { files } = measure();

    assert.deepEqual(files.map((file) => file.name), MODULES);
});


test("no single module is unexpectedly large", () => {
    const { files } = measure();
    const offenders = files.filter((file) => file.raw > PER_FILE_RAW_CEILING);

    assert.deepEqual(offenders.map((file) => file.name), [],
                     "a module grew past its ceiling; check for a copied "
                     + "library or embedded demo content");
});


test("the runtime total stays within a generous budget", () => {
    const { raw, gzip } = measure();

    assert.ok(raw < RAW_CEILING,
              `raw total ${raw} exceeded ${RAW_CEILING}`);
    assert.ok(gzip < GZIP_CEILING,
              `gzip total ${gzip} exceeded ${GZIP_CEILING}`);
});


test("every module exports at least one symbol", () => {
    const { files } = measure();
    const silent = files.filter((file) => file.exports === 0);

    assert.deepEqual(silent.map((file) => file.name), []);
});
