# Contract: Content Constraints

**@since**: 1.0.0

## `ContentConstraint` (base)

```python
@dataclass
class ContentConstraint:
    type: str                      # constraint type discriminator
    message: str = ""              # custom error message
```

---

## `BannedTileType`

Forbids specific tile types from appearing in the output.

```python
@dataclass
class BannedTileType(ContentConstraint):
    type: str = "banned_tile"
    tile_types: list[str] = field(default_factory=list)
```

**Example**:
```python
constraint = BannedTileType(tile_types=["LAVA", "TRAP"])
```

---

## `BannedEntityType`

Forbids specific entity types from appearing in the output.

```python
@dataclass
class BannedEntityType(ContentConstraint):
    type: str = "banned_entity"
    entity_types: list[str] = field(default_factory=list)
```

**Example**:
```python
constraint = BannedEntityType(entity_types=["npc_villain"])
```

---

## `MaxDensity`

Limits the maximum fraction of the grid occupied by a specific tile type.

```python
@dataclass
class MaxDensity(ContentConstraint):
    type: str = "max_density"
    tile_type: str                 # tile type to limit
    max_ratio: float               # max fraction of grid (0.0-1.0)
```

**Example**:
```python
constraint = MaxDensity(tile_type="WATER", max_ratio=0.3)
# At most 30% of the grid may be WATER tiles
```

---

## `AgeRatingProfile`

Applies a pre-defined set of restrictions based on an age rating.

```python
@dataclass
class AgeRatingProfile(ContentConstraint):
    type: str = "age_rating"
    profile: str                   # e.g., "E", "T", "M"
    banned_tiles: list[str] = field(default_factory=list)
    banned_entities: list[str] = field(default_factory=list)
```

**Example**:
```python
constraint = AgeRatingProfile(
    profile="E",
    banned_tiles=["LAVA", "TRAP"],
    banned_entities=["npc_villain"],
)
```

---

## Enforcement

When a constraint is violated during generation, the generator MUST either:

1. **Retry** with adjusted parameters up to `max_iterations`, OR
2. **Fail** with a clear `ConstraintViolationError` identifying the offending constraint.

Generators MUST NOT silently produce content that violates an explicitly declared constraint.

```python
from gamemapgen import ConstraintViolationError

try:
    map_data = gen.generate()
except ConstraintViolationError as e:
    print(f"Constraint violated: {e}")  # identifies the offending constraint
```

---

## Usage Example

```python
from gamemapgen import GeneratorRegistry, BannedTileType, MaxDensity

registry = GeneratorRegistry()
gen = registry.create("open_world", seed=42, width=50, height=50)

gen.add_constraint(BannedTileType(tile_types=["LAVA"]))
gen.add_constraint(MaxDensity(tile_type="WATER", max_ratio=0.4))

map_data = gen.generate()

# Verify: no LAVA tiles, WATER ≤ 40% of grid
for row in map_data.grid:
    for tile in row:
        assert tile.type != "LAVA"
```
