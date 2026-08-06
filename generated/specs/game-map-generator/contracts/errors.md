# Contract: Typed Errors

**@since**: 1.0.0

## Exception Hierarchy

```
GameMapGenError (base)
├── ValidationError
├── GenerationError
├── ConstraintViolationError
├── PresetNotFoundError
└── GeneratorNotFoundError
```

All errors are catchable and carry actionable messages identifying the offending parameter, constraint, or generator.

---

## `GameMapGenError` (base)

```python
class GameMapGenError(Exception):
    """Base class for all GameMapGen errors."""
```

---

## `ValidationError`

Raised when generation parameters are invalid. The message identifies the invalid parameter and its valid range/values.

```python
class ValidationError(GameMapGenError):
    """Raised when generation parameters fail validation.

    Example message:
        "Invalid parameter 'width': expected int in range [1, 1000], got 0"
    """
```

**Usage**:
```python
from gamemapgen import ValidationError

try:
    registry.create("dungeon", seed=42, width=0, height=50)
except ValidationError as e:
    print(e)  # "Invalid parameter 'width': expected int in range [1, 1000], got 0"
```

---

## `GenerationError`

Raised when generation fails partway through. The generator either rolls back to a consistent state or returns a partial result flagged `incomplete=True`.

```python
class GenerationError(GameMapGenError):
    """Raised when generation fails mid-process.

    The generator MUST NOT return a MapData that appears valid but
    contains inconsistent data (FR-012).
    """
```

---

## `ConstraintViolationError`

Raised when content constraints cannot be satisfied within the iteration budget.

```python
class ConstraintViolationError(GameMapGenError):
    """Raised when content constraints cannot be satisfied.

    The message identifies the offending constraint.
    """
```

**Usage**:
```python
from gamemapgen import ConstraintViolationError

try:
    map_data = gen.generate()
except ConstraintViolationError as e:
    print(f"Constraint violated: {e}")
```

---

## `PresetNotFoundError`

Raised when a preset name is not registered.

```python
class PresetNotFoundError(GameMapGenError):
    """Raised when a preset name is not found in the registry."""
```

---

## `GeneratorNotFoundError`

Raised when a generator name is not registered.

```python
class GeneratorNotFoundError(GameMapGenError):
    """Raised when a generator name is not found in the registry."""
```

---

## Usage Example

```python
from gamemapgen import (
    GameMapGenError, ValidationError, GenerationError,
    ConstraintViolationError, PresetNotFoundError, GeneratorNotFoundError,
)

try:
    gen = registry.create("unknown_generator", seed=42)
except GeneratorNotFoundError:
    print("Generator not found")

try:
    gen = registry.create("dungeon", seed=42, width=0)
except ValidationError as e:
    print(f"Validation failed: {e}")

try:
    map_data = gen.generate()
except ConstraintViolationError as e:
    print(f"Constraint violated: {e}")
except GenerationError as e:
    print(f"Generation failed: {e}")
except GameMapGenError as e:
    print(f"Other error: {e}")
```
