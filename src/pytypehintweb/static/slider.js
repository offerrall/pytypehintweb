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


export function firstSliderValue(minimum, maximum, stride, multipleOf) {
    const [start, end, step, factor] =
        [BigInt(minimum), BigInt(maximum), BigInt(stride), BigInt(multipleOf)];

    const divisor = gcd(step, factor);

    if (start % divisor === 0n) {
        const modulus = factor / divisor;
        const steps = modulus === 1n
            ? 0n
            : (((-start / divisor) % modulus) + modulus) % modulus
                * inverse(step / divisor, modulus) % modulus;

        const candidate = start + steps * step;

        if (candidate <= end) {
            return Number(candidate);
        }
    }

    return end % factor === 0n ? Number(end) : null;
}


export function sliderReaches(minimum, maximum, stride, multipleOf) {
    return firstSliderValue(minimum, maximum, stride, multipleOf) !== null;
}


function onStride(value, minimum, stride) {
    return (BigInt(value) - BigInt(minimum)) % BigInt(stride) === 0n;
}


export function sliderAligned(minimum, maximum, stride) {
    return onStride(maximum, minimum, stride);
}


export function onSliderGrid(value, minimum, maximum, stride) {
    return value === maximum || onStride(value, minimum, stride);
}


export function sliderLastIndex(minimum, maximum, stride) {
    const strides = (BigInt(maximum) - BigInt(minimum)) / BigInt(stride);

    return Number(sliderAligned(minimum, maximum, stride)
        ? strides
        : strides + 1n);
}


export function sliderValueAt(minimum, maximum, stride, index) {
    const value = BigInt(minimum) + BigInt(index) * BigInt(stride);

    return value < BigInt(maximum) ? Number(value) : maximum;
}


export function sliderIndexOf(minimum, maximum, stride, value) {
    return value === maximum
        ? sliderLastIndex(minimum, maximum, stride)
        : Number((BigInt(value) - BigInt(minimum)) / BigInt(stride));
}
