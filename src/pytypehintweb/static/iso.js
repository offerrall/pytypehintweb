const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;


export function isValidIsoDate(value) {
    if (typeof value !== "string" || !ISO_DATE.test(value)) {
        return false;
    }

    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    const day = Number(value.slice(8, 10));

    if (year < 1) {
        return false;
    }

    const date = new Date(Date.UTC(year, month - 1, day));

    date.setUTCFullYear(year);

    return date.getUTCFullYear() === year
        && date.getUTCMonth() === month - 1
        && date.getUTCDate() === day;
}
