"""Unit tests for the seeded `PRNG` wrapper.

Covers FR-002 determinism guarantees (same seed -> identical sequence),
FR-002/US2 seed-influence and cross-process reproducibility, the documented
output-range semantics of the prng.md contract, and seed validation as a
32-bit unsigned integer in [0, 2^32-1].
"""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from gamemapgen import PRNG, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_sequence(prng, length=64):
    """Draw a deterministic mixed sequence of random values from a PRNG."""
    values = []
    for _ in range(length):
        op = len(values) % 4
        if op == 0:
            values.append(prng.randint(1, 100))
        elif op == 1:
            values.append(prng.random())
        elif op == 2:
            values.append(prng.uniform(-10.0, 10.0))
        else:
            values.append(prng.choice(["a", "b", "c", "d"]))
    return values


def _package_root():
    """Directory from which the `gamemapgen` package is importable.

    Derived from the live module rather than a hardcoded ``src/`` layout so
    the subprocess PYTHONPATH stays correct whether the package is run from
    the repo's ``src/`` tree or installed into site-packages.
    """
    import gamemapgen

    return str(Path(gamemapgen.__file__).resolve().parent.parent)


# A self-contained script that draws a PRNG sequence in a separate process.
# It must mirror `_draw_sequence` exactly so cross-process results are
# directly comparable.
_SUBPROCESS_SCRIPT = (
    "import sys\n"
    "import json\n"
    "from gamemapgen import PRNG\n"
    "seed = int(sys.argv[1])\n"
    "prng = PRNG(seed=seed)\n"
    "values = []\n"
    "for i in range(64):\n"
    "    op = i % 4\n"
    "    if op == 0:\n"
    "        values.append(prng.randint(1, 100))\n"
    "    elif op == 1:\n"
    "        values.append(prng.random())\n"
    "    elif op == 2:\n"
    "        values.append(prng.uniform(-10.0, 10.0))\n"
    "    else:\n"
    "        values.append(prng.choice(['a', 'b', 'c', 'd']))\n"
    "print(json.dumps(values))\n"
)


# ---------------------------------------------------------------------------
# Seed validation (FR-002 / FR-005)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 42, 2**31, 2**32 - 1])
def test_valid_seeds_accepted(seed):
    """Boundary values within [0, 2^32-1] are accepted."""
    prng = PRNG(seed=seed)
    assert isinstance(prng.random(), float)


@pytest.mark.parametrize("seed", [-1, -(2**31), -(2**32)])
def test_negative_seed_raises_validation_error(seed):
    """Negative seeds are out of the 32-bit unsigned range."""
    with pytest.raises(ValidationError):
        PRNG(seed=seed)


@pytest.mark.parametrize("seed", [2**32, 2**32 + 1, 2**40])
def test_seed_above_upper_bound_raises_validation_error(seed):
    """Seeds greater than 2^32-1 are rejected."""
    with pytest.raises(ValidationError):
        PRNG(seed=seed)


@pytest.mark.parametrize("seed", [42.0, "42", None, [42], (42,), {"seed": 42}])
def test_non_integer_seed_raises_validation_error(seed):
    """Non-integer seed types are rejected."""
    with pytest.raises(ValidationError):
        PRNG(seed=seed)


def test_validation_error_message_identifies_seed_and_range():
    """The error message names the offending parameter and its valid range."""
    with pytest.raises(ValidationError) as excinfo:
        PRNG(seed=-1)
    message = str(excinfo.value)
    assert "seed" in message.lower()
    assert "0" in message
    assert "2^32" in message or "4294967295" in message or "2**32" in message


# ---------------------------------------------------------------------------
# Determinism (FR-002)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 42, 123456789, 2**32 - 1])
def test_same_seed_produces_identical_sequence(seed):
    """Two PRNGs initialized with the same seed draw identical sequences."""
    prng_a = PRNG(seed=seed)
    prng_b = PRNG(seed=seed)
    assert _draw_sequence(prng_a) == _draw_sequence(prng_b)


def test_same_seed_single_value_equality():
    """Individual method calls match for identical seeds."""
    prng_a = PRNG(seed=42)
    prng_b = PRNG(seed=42)
    assert prng_a.random() == prng_b.random()
    assert prng_a.randint(1, 100) == prng_b.randint(1, 100)
    assert prng_a.uniform(0.0, 1.0) == prng_b.uniform(0.0, 1.0)
    assert prng_a.choice([1, 2, 3]) == prng_b.choice([1, 2, 3])


@pytest.mark.parametrize(
    ("seed_a", "seed_b"),
    [(0, 1), (1, 2), (42, 43), (123456789, 987654321), (2**32 - 1, 2**32 - 2)],
)
def test_different_seeds_produce_different_sequences(seed_a, seed_b):
    """Different seeds with otherwise identical params differ (US2 acc. 2).

    This proves the seed actually influences randomness rather than being
    ignored.
    """
    seq_a = _draw_sequence(PRNG(seed=seed_a))
    seq_b = _draw_sequence(PRNG(seed=seed_b))
    assert seq_a != seq_b


def test_prng_is_independent_of_global_random():
    """PRNG determinism must not depend on or leak the global random state."""
    original_state = random.getstate()
    try:
        random.seed(999)
        expected = _draw_sequence(PRNG(seed=7), length=16)

        random.seed(12345)
        actual = _draw_sequence(PRNG(seed=7), length=16)
    finally:
        # Restore the module-level `random` state so this test does not
        # pollute global state for any subsequent test (test isolation).
        random.setstate(original_state)

    assert actual == expected


def test_prng_does_not_mutate_global_random_state():
    """Using the seeded PRNG must leave the global `random` state untouched."""
    before = random.getstate()
    PRNG(seed=42).randint(1, 100)
    PRNG(seed=42).random()
    after = random.getstate()
    assert after == before


@pytest.mark.parametrize("seed", [0, 42, 2**32 - 1])
def test_same_seed_identical_across_processes(seed):
    """Same seed reproduces an identical sequence in a separate process.

    Covers User Story 2 acceptance scenario 3: no global or environment
    randomness leaks in, so the output is byte-identical across separate
    generation runs/processes on the current host/Python build. Full
    cross-platform and cross-version determinism is inherited from CPython's
    documented ``random.Random`` guarantee; it cannot be exercised by a unit
    test running on a single machine and is therefore not re-asserted here.
    """
    local_seq = _draw_sequence(PRNG(seed=seed))

    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _package_root() + (os.pathsep + existing if existing else "")

    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT, str(seed)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    remote_seq = json.loads(proc.stdout)
    assert remote_seq == local_seq


# ---------------------------------------------------------------------------
# Output-range / semantics contract (prng.md)
# ---------------------------------------------------------------------------

def test_random_returns_float_in_unit_interval():
    """random returns a float in [0.0, 1.0)."""
    prng = PRNG(seed=1)
    for _ in range(200):
        value = prng.random()
        assert isinstance(value, float)
        assert 0.0 <= value < 1.0


def test_randint_returns_value_in_closed_range():
    """randint returns an int in [a, b] (inclusive)."""
    prng = PRNG(seed=1)
    for _ in range(200):
        value = prng.randint(1, 100)
        assert isinstance(value, int)
        assert 1 <= value <= 100


def test_uniform_returns_value_within_range():
    """uniform returns a float within [a, b] (CPython-inclusive semantics).

    ``PRNG.uniform`` delegates to ``random.Random.uniform``, whose documented
    behavior is ``a <= N <= b``. Floating-point rounding may yield exactly the
    upper bound, so the assertion is inclusive rather than a strict half-open
    ``[a, b)`` check (which could flakily fail on the delegate's output).
    """
    prng = PRNG(seed=1)
    for _ in range(200):
        value = prng.uniform(-10.0, 10.0)
        assert isinstance(value, float)
        assert -10.0 <= value <= 10.0


def test_sample_returns_k_unique_elements():
    """sample returns k unique elements drawn from the population."""
    prng = PRNG(seed=1)
    population = list(range(20))
    sample = prng.sample(population, 6)
    assert len(sample) == 6
    assert len(set(sample)) == 6
    assert all(item in population for item in sample)


def test_choice_requires_non_empty_sequence():
    """choice returns an element from a non-empty sequence."""
    prng = PRNG(seed=1)
    seq = ["a", "b", "c"]
    for _ in range(50):
        assert prng.choice(seq) in seq
    # prng.md only guarantees `choice` on a *non-empty* sequence; the exact
    # exception raised for an empty sequence is not part of the contract.
    # The delegate `random.choice` happens to raise IndexError, but pinning a
    # specific type here would over-constrain an unimplemented guarantee, so
    # we only assert that an empty input must fail rather than succeed.
    with pytest.raises(Exception):
        prng.choice([])


# ---------------------------------------------------------------------------
# State save / restore
# ---------------------------------------------------------------------------

def test_get_and_set_state_restore_sequence():
    """Save/restore via get_state/set_state resumes the identical stream."""
    prng = PRNG(seed=42)
    first = _draw_sequence(prng, length=8)
    state = prng.get_state()

    # A brand-new PRNG seeded the same way, after drawing the same 8 values,
    # must be exactly at the saved stream position.
    reference = PRNG(seed=42)
    assert _draw_sequence(reference, length=8) == first

    expected_next = _draw_sequence(reference, length=8)

    # The original `prng` has also drawn only 8 values, so its next 8 match.
    actual_next = _draw_sequence(prng, length=8)
    assert actual_next == expected_next

    # Restoring the saved state resumes exactly the same stream.
    prng.set_state(state)
    resumed = _draw_sequence(prng, length=8)
    assert resumed == expected_next


def test_get_set_state_round_trip_reproduces_exact_stream():
    """set_state(get_state()) reproduces the identical byte-level stream.

    The restored stream must be independent of the seed used to construct the
    receiving PRNG instance, proving get_state/set_state round-trips to an
    exact, reproducible internal state tuple.
    """
    prng_a = PRNG(seed=7)
    _draw_sequence(prng_a, length=16)
    state = prng_a.get_state()

    # Restore into a PRNG initialized with a *different* seed.
    prng_b = PRNG(seed=123)
    prng_b.set_state(state)

    # A fresh PRNG seeded 7, advanced 16 values, must continue identically.
    prng_c = PRNG(seed=7)
    _draw_sequence(prng_c, length=16)

    assert _draw_sequence(prng_b, length=32) == _draw_sequence(prng_c, length=32)


# ---------------------------------------------------------------------------
# API surface (per prng contract)
# ---------------------------------------------------------------------------

def test_methods_exposed():
    """PRNG exposes the documented random helpers."""
    prng = PRNG(seed=1)
    assert callable(prng.randint)
    assert callable(prng.random)
    assert callable(prng.uniform)
    assert callable(prng.choice)
    assert callable(prng.shuffle)
    assert callable(prng.sample)
    assert callable(prng.get_state)
    assert callable(prng.set_state)


def test_shuffle_and_sample_are_deterministic():
    """A single PRNG instance's combined shuffle+sample stream is deterministic.

    Uses the same threaded instance for both shuffle and sample so the
    combined stream (per the prng.md threaded-instance semantics) is verified.
    """
    def run_once():
        population = list(range(20))
        prng = PRNG(seed=5)
        prng.shuffle(population)
        shuffled = list(population)
        sample = prng.sample(range(20), 6)
        return shuffled, sample

    shuffled_a, sample_a = run_once()
    shuffled_b, sample_b = run_once()

    assert shuffled_a == shuffled_b
    assert sample_a == sample_b
