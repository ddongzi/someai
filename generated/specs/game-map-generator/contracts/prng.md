# Contract: Seeded PRNG

**@since**: 1.0.0

## `PRNG`

A wrapper around Python's `random.Random` that enforces the 32-bit unsigned seed contract and is explicitly passed to every generator.

```python
class PRNG:
    def __init__(self, seed: int):
        """Initialize with a 32-bit unsigned integer seed.

        Args:
            seed: Integer in range [0, 2^32-1].

        Raises:
            ValidationError: If seed is out of range or not an integer.
        """

    def randint(self, a: int, b: int) -> int:
        """Return a random integer in [a, b]."""

    def random(self) -> float:
        """Return a random float in [0.0, 1.0)."""

    def uniform(self, a: float, b: float) -> float:
        """Return a random float in [a, b)."""

    def choice(self, seq: Sequence) -> Any:
        """Return a random element from a non-empty sequence."""

    def shuffle(self, x: list) -> None:
        """Shuffle a list in place."""

    def sample(self, population: Sequence, k: int) -> list:
        """Return k unique random elements from a population."""

    def get_state(self) -> tuple:
        """Return the internal PRNG state (for save/restore)."""

    def set_state(self, state: tuple) -> None:
        """Restore the internal PRNG state."""
```

---

## Determinism Guarantee

The same seed always produces the identical sequence of random values:

```python
from gamemapgen import PRNG

prng_a = PRNG(seed=42)
prng_b = PRNG(seed=42)

assert prng_a.random() == prng_b.random()
assert prng_a.randint(1, 100) == prng_b.randint(1, 100)
```

---

## Usage in Generators

Generators MUST use the passed `PRNG` instance, never global `random.*` functions:

```python
class DungeonGenerator(BaseGenerator):
    def generate(self, params: GenerationParams) -> MapData:
        prng = PRNG(seed=params.seed)
        # Use prng for all randomness
        room_x = prng.randint(0, params.width - 1)
        # ...
```

---

## Threading Through Composite Layers

The same `PRNG` instance is threaded through composite layers to ensure reproducible multi-pass generation:

```python
class CompositeGenerator(BaseGenerator):
    def generate(self, params: GenerationParams) -> MapData:
        prng = PRNG(seed=params.seed)
        context = GenerationContext(
            map_data=MapData(...),
            prng=prng,
            params=params,
        )
        for layer in self.layers:
            context = layer.generate(context)
        return context.map_data
```
