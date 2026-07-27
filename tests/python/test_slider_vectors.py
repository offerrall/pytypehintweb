import json
from pathlib import Path

import pytest

from pytypehintweb.plan import _slider_reaches

FIXTURE = (Path(__file__).resolve().parents[1]
           / "fixtures" / "slider_cases.json")

CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _brute_reaches(minimum, maximum, step, multiple):
    # The maximum is a slider position in its own right, reachable even when the
    # stride does not divide the range evenly, so the walk covers the stride grid
    # and then the maximum.
    value = minimum

    while value <= maximum:
        if value % multiple == 0:
            return True
        value += step

    return maximum % multiple == 0


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_python_slider_reaches_matches_the_shared_vectors(case):
    assert _slider_reaches(
        case["minimum"], case["maximum"], case["step"], case["multipleOf"]
    ) is case["reachable"]


def test_the_shared_vectors_cover_the_documented_situations():
    reachable = [c for c in CASES if c["reachable"]]
    unreachable = [c for c in CASES if not c["reachable"]]

    # Both outcomes, negative ranges, a single point, and a huge safe range.
    assert reachable and unreachable
    assert any(c["minimum"] < 0 for c in CASES)
    assert any(c["minimum"] == c["maximum"] for c in CASES)
    assert any(c["maximum"] >= 2 ** 53 - 1 for c in CASES)

    # A maximum the stride cannot land on is still a position, so both outcomes
    # of the off-grid maximum are pinned.
    off_grid = [c for c in CASES
                if (c["maximum"] - c["minimum"]) % c["step"] != 0]

    assert any(c["first"] == c["maximum"] for c in off_grid)
    assert any(not c["reachable"] for c in off_grid)


def test_the_optimized_solver_matches_brute_force_on_small_ranges():
    checked = 0

    for minimum in range(-6, 7):
        for maximum in range(minimum, minimum + 13):
            for step in range(1, 7):
                for multiple in range(1, 7):
                    assert (
                        _slider_reaches(minimum, maximum, step, multiple)
                        == _brute_reaches(minimum, maximum, step, multiple)
                    ), f"min={minimum} max={maximum} step={step} mult={multiple}"
                    checked += 1

    assert checked > 5000
