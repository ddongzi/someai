# Quickstart: Game Map Generation Component

**Phase 1 Output** | **Date**: 2026-08-05 | **Branch**: `game-map-generator`

This guide provides runnable validation scenarios that prove the feature works end-to-end. Each scenario maps to a User Story from the [spec](./spec.md) and can be executed as a test or script.

---

## Prerequisites

- Python 3.11+
- No external runtime dependencies (standard library only)
- Dev dependencies: `pytest`, `pytest-cov`

```bash
pip install pytest pytest-cov
```

---

## Scenario 1: Deterministic Map Generation (User Story 1)

**Goal**: Verify that the same seed + parameters always produce identical output.

```python
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
gen = registry.create("dungeon", seed=42, width=50, height=50)

map_a = gen.generate()
map_b = gen.generate()

assert map_a.to_json() == map_b.to_json()  # byte-identical
```

**Expected outcome**: Both `map_a` and `map_b` are byte-for-byte identical.

**Also verify**:
- Different seed → different map:
  ```python
  gen2 = registry.create("dungeon", seed=43, width=50, height=50)
  assert gen2.generate().to_json() != map_a.to_json()
  ```
- Invalid params → clear error, no map produced:
  ```python
  from gamemapgen import ValidationError
  try:
      registry.create("dungeon", seed=42, width=0, height=50)
  except ValidationError as e:
      assert "width" in str(e)  # identifies the invalid parameter
  ```

---

## Scenario 2: Composite Layered Generation (User Story 2)

**Goal**: Verify that multiple generators compose into a single coherent map.

```python
from gamemapgen import CompositeGenerator, GeneratorRegistry

registry = GeneratorRegistry()
composite = CompositeGenerator(
    layers=[
        ("terrain", registry.create("open_world", seed=42, width=50, height=50)),
        ("roads", registry.create("dungeon", seed=42, width=50, height=50)),
    ]
)

map_data = composite.generate()
assert len(map_data.layers) == 2
assert map_data.layers[0].name == "terrain"
assert map_data.layers[1].name == "roads"
```

**Expected outcome**: The composite output contains both layers in documented order, and is deterministic for a fixed seed.

---

## Scenario 3: Hooks and Content Constraints (User Story 3)

**Goal**: Verify that custom hooks execute at lifecycle points and constraints are enforced.

```python
from gamemapgen import (
    GeneratorRegistry, GenerationContext, BannedTileType,
)

registry = GeneratorRegistry()

# Register a hook that places a marker entity after room placement
def place_marker(ctx: GenerationContext) -> GenerationContext:
    from gamemapgen import Entity, Position
    ctx.map_data.entities.append(
        Entity(type="quest_marker", position=Position(5, 5))
    )
    return ctx

gen = registry.create("dungeon", seed=42, width=50, height=50)
gen.register_hook("after_room_placement", place_marker)

# Add a content constraint banning LAVA tiles
constraint = BannedTileType(tile_types=["LAVA"])
gen.add_constraint(constraint)

map_data = gen.generate()

# Verify hook effect
assert any(e.type == "quest_marker" for e in map_data.entities)

# Verify constraint enforcement
for row in map_data.grid:
    for tile in row:
        assert tile.type != "LAVA"
```

**Expected outcome**: The marker entity appears in the output, and no LAVA tiles exist.

---

## Scenario 4: Debug and Inspection (User Story 4)

**Goal**: Verify human-readable ASCII output and intermediate snapshots.

```python
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
gen = registry.create("maze", seed=7, width=21, height=21)

map_data = gen.generate()

# ASCII representation (no external rendering)
ascii_str = map_data.to_ascii()
print(ascii_str)
assert isinstance(ascii_str, str)
assert len(ascii_str) > 0

# Intermediate snapshots at hook points
assert "before_generation" in gen.snapshots
assert "post_process" in gen.snapshots
```

**Expected outcome**: A human-readable ASCII string is produced without any rendering library, and snapshots are available at documented hook points.

---

## Scenario 5: Serialization Round-Trip

**Goal**: Verify lossless JSON round-trip.

```python
import json
from gamemapgen import GeneratorRegistry, MapData

registry = GeneratorRegistry()
gen = registry.create("open_world", seed=99, width=30, height=30)
map_data = gen.generate()

json_str = map_data.to_json()
restored = MapData.from_dict(json.loads(json_str))

assert restored == map_data  # lossless
```

**Expected outcome**: The restored `MapData` is identical to the original.

---

## Scenario 6: Performance Budget

**Goal**: Verify a 100x100 grid generates in under 100ms.

```python
import time
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
gen = registry.create("dungeon", seed=42, width=100, height=100)

start = time.perf_counter()
map_data = gen.generate()
elapsed_ms = (time.perf_counter() - start) * 1000

assert elapsed_ms < 100, f"Generation took {elapsed_ms:.1f}ms (budget: 100ms)"
```

**Expected outcome**: Generation completes in under 100ms on reference hardware.

---

## Running All Scenarios as Tests

Save each scenario as a test function in `tests/` and run:

```bash
pytest tests/ -v --cov=gamemapgen --cov-report=term-missing
```

---

## References

- [Data Model](./data-model.md) — Entity definitions and validation rules
- [Contracts](./contracts/README.md) — Public API contracts
- [Plan](./plan.md) — Implementation plan and architecture
