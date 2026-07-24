/*
 * Canonical ISO date validation, shared by the plan validator and the widget.
 *
 * A canonical date is a real calendar date written exactly as YYYY-MM-DD. The
 * shape alone is not enough: 2026-02-31 and 2026-13-01 match it and no calendar
 * holds them, and a native date input silently blanks itself when such a value
 * is assigned — so the value is refused before it reaches the control.
 *
 * Single implementation for normalize.js / contract.js (plans) and inputs.js
 * (DateWidget), so the two layers cannot drift apart.
 */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;


export function isValidIsoDate(value) {
    if (typeof value !== "string" || !ISO_DATE.test(value)) {
        return false;
    }

    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    const day = Number(value.slice(8, 10));

    // 0001 is the first date of the four-digit domain; the shape bounds the top.
    if (year < 1) {
        return false;
    }

    // Date.UTC maps years 0..99 onto 1900+year, so the year is restated before
    // reading anything back: without it 0001-01-01 returns as 1901 and a real
    // date would be refused. UTC throughout, so no local zone shifts the day.
    const date = new Date(Date.UTC(year, month - 1, day));

    date.setUTCFullYear(year);

    // An impossible date normalizes (2026-02-31 -> 2026-03-03), so a component
    // coming back changed means the input was never a real date.
    return date.getUTCFullYear() === year
        && date.getUTCMonth() === month - 1
        && date.getUTCDate() === day;
}
