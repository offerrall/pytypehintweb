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


export function onSliderGrid(value, minimum, stride) {
    return (BigInt(value) - BigInt(minimum)) % BigInt(stride) === 0n;
}
