/*
 * Slider position arithmetic, shared by the plan validator and the widget.
 *
 * A slider lands on minimum + k * stride for whole k >= 0. When a multipleOf
 * is present, only the positions that are also a multiple of it are valid.
 * Finding the first such position is a linear congruence, solved with the
 * gcd / CRT arithmetic below rather than by scanning, so a range spanning the
 * whole safe-integer space is answered in constant time instead of ~9e15
 * iterations.
 *
 * This is the single mathematical implementation for both sliderReaches()
 * (used by contract.js) and firstSliderValue() (used by inputs.js).
 */


function gcd(a, b) {
    while (b !== 0n) {
        [a, b] = [b, a % b];
    }

    return a < 0n ? -a : a;
}


function inverse(value, modulus) {
    let [old, current] = [value % modulus, modulus];
    let [oldCoefficient, coefficient] = [1n, 0n];

    while (current !== 0n) {
        const quotient = old / current;
        [old, current] = [current, old - quotient * current];
        [oldCoefficient, coefficient] =
            [coefficient, oldCoefficient - quotient * coefficient];
    }

    return ((oldCoefficient % modulus) + modulus) % modulus;
}


// The first reachable slider position minimum + k * stride, k >= 0, that is a
// multiple of multipleOf and does not pass maximum. Returns that safe integer,
// or null when no reachable position satisfies the multiple. All arithmetic is
// exact BigInt; the result lies within [minimum, maximum], so it is a safe
// integer and is converted back before returning.
export function firstSliderValue(minimum, maximum, stride, multipleOf) {
    const [start, end, step, factor] =
        [BigInt(minimum), BigInt(maximum), BigInt(stride), BigInt(multipleOf)];

    const divisor = gcd(step, factor);

    if (start % divisor !== 0n) {
        return null;
    }

    const modulus = factor / divisor;
    const steps = modulus === 1n
        ? 0n
        : (((-start / divisor) % modulus) + modulus) % modulus
            * inverse(step / divisor, modulus) % modulus;

    const candidate = start + steps * step;

    if (candidate > end) {
        return null;
    }

    return Number(candidate);
}


export function sliderReaches(minimum, maximum, stride, multipleOf) {
    return firstSliderValue(minimum, maximum, stride, multipleOf) !== null;
}


// Whether a value sits on the grid minimum + k * stride. The distance can exceed
// the safe integer range, so it is measured in BigInt. One rule for both sides:
// checkPlan applies it to a slider default, the widget before writing a value.
export function onSliderGrid(value, minimum, stride) {
    return (BigInt(value) - BigInt(minimum)) % BigInt(stride) === 0n;
}
