"""Unit tests for the seeded `PRNG` wrapper.

Covers FR-002 determinism guarantees (same seed -> identical sequence) and
seed validation as a 32-bit unsigned integer in [0, 2^32-1].
"""

import random

import pytest

from gamemapgen import PRNG, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_sequence(prng, length=64):
    """Draw a deterministic mixed sequence of random values from a PRNG."""
    values = []
    for _ in range(length):
        op = values and len(values) % 4
        if op == 0:
            values.append(prng.randint(1, 100))
        elif op == 1:
            values.append(prng.random())
        elif op == 2:
            values.append(prng.uniform(-10.0, 10.0))
        else:
            values.append(prng.choice(["a", "b", "c", "d"]))
    return values


# ---------------------------------------------------------------------------
# Seed validation (FR-002 / FR-005)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 42, 2**31, 2**32 - 1])
def test_valid_seeds_accepted(seed):
    """Boundary values within [0, 2^32-1] are accepted."""
    prng = PRNG(seed=seed)
    assert isinstance(prng.random(), float)


@pytest.mark.parametrize("seed", [-1, -2**32, -(2**32)])
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


def test_different_seeds_produce_different_sequences():
    """Different seeds yield (very likely) different sequences."""
    prng_a = PRNG(seed=1)
    prng_b = PRNG(seed=2)
    assert _draw_sequence(prng_a, length=32) != _draw_sequence(prng_b, length=32)


def test_prng_is_independent_of_global_random():
    """PRNG determinism must not depend on or leak the global random state."""
    random.seed(999)
    expected = _draw_sequence(PRNG(seed=7), length=16)

    random.seed(12345)
    actual = _draw_sequence(PRNG(seed=7), length=16)

    assert actual == expected


def test_prng_does_not_mutate_global_random_state():
    """Using the seeded PRNG must leave the global `random` state untouched."""
    before = random.getstate()
    PRNG(seed=42).randint(1, 100)
    PRNG(seed=42).random()
    after = random.getstate()
    assert after == before


# ---------------------------------------------------------------------------
# State save / restore
# ---------------------------------------------------------------------------

def test_get_and_set_state_restore_sequence():
    """Save/restore via get_state/set_state resumes the identical stream."""
    prng = PRNG(seed=42)
    _draw_sequence(prng, length=8)
    state = prng.get_state()

    prng_expected = PRNG(seed=42)
    _draw_sequence(prng_expected, length=8)
    expected_next = _draw_sequence(prng_expected, length=8)

    actual_next = _draw_sequence(prng, length=8)
    assert actual_next != expected_next  # different position

    prng.set_state(state)
    resumed = _draw_sequence(prng, length=8)
    assert resumed == expected_next


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
    """shuffle and sample produce identical results for the same seed."""
    population = list(range(20))

    a = PRNG(seed=5)
    a.shuffle(population)
    shuffled_a = list(population)
    sample_a = PRNG(seed=5).sample(range(20), 6)

    population_b = list(range(20))
    b = PRNG(seed=5)
    b.shuffle(population_b)
    shuffled_b = list(population_b)
    sample_b = PRNG(seed=5).sample(range(20), 6)

    assert shuffled_a == shuffled_b
    assert sample_a == sample_b
