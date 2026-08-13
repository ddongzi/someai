# Contract: Hook System

**@since**: 1.0.0

## `GenerationContext`

The mutable context threaded through generation and passed to hooks.

```python
@dataclass
class GenerationContext:
    map_data: MapData              # in-progress map
    prng: PRNG                     # seeded PRNG instance
    params: GenerationParams       # resolved parameters
    snapshots: dict[str, MapData] = field(default_factory=dict)
    # Intermediate state snapshots at each hook point (FR-027)
```

---

## `Hook`

A callable with signature `hook(context: GenerationContext) -> GenerationContext`.

```python
Hook = Callable[[GenerationContext], GenerationContext]
```

Hooks of the same type execute in registration order (chainable). Each hook receives the context returned by the previous hook.

---

## Lifecycle Points

Extensible set of named lifecycle points:

| Point | Description |
|-------|-------------|
| `before_generation` | Before any generation logic runs. |
| `after_room_placement` | After rooms/regions are placed. |
| `after_corridor_connection` | After corridors/connections are made. |
| `post_process` | After all generation, before finalization. |

---

## `HookManager`

```python
class HookManager:
    def register(self, point: str, hook: Hook) -> None:
        """Register a hook at a lifecycle point.

        Args:
            point: Lifecycle point name (e.g., "before_generation").
            hook: Callable with signature (ctx) -> ctx.

        Raises:
            ValidationError: If `point` is not a known lifecycle point.
        """

    def unregister(self, point: str, hook: Hook) -> None:
        """Remove a previously registered hook."""

    def run(self, point: str, context: GenerationContext) -> GenerationContext:
        """Execute all hooks at a lifecycle point in registration order.

        Args:
            point: Lifecycle point name.
            context: Current generation context.

        Returns:
            GenerationContext: The (possibly modified) context.

        Raises:
            GenerationError: If a hook raises an exception (wrapped).
        """

    def list_hooks(self, point: str) -> list[Hook]:
        """List all hooks registered at a lifecycle point."""
```

---

## Usage Example

```python
from gamemapgen import (
    GeneratorRegistry, GenerationContext, Entity, Position,
)

def place_quest_item(ctx: GenerationContext) -> GenerationContext:
    ctx.map_data.entities.append(
        Entity(type="quest_item", position=Position(10, 10))
    )
    return ctx

def add_ambient_light(ctx: GenerationContext) -> GenerationContext:
    for row in ctx.map_data.grid:
        for tile in row:
            tile.metadata["ambient"] = 0.5
    return ctx

gen = registry.create("dungeon", seed=42, width=50, height=50)
gen.register_hook("after_room_placement", place_quest_item)
gen.register_hook("post_process", add_ambient_light)

map_data = gen.generate()
# Both hooks executed in registration order
```

---

## Intermediate Snapshots

At each hook point, the `HookManager` captures a snapshot of the current `MapData` into `context.snapshots[point]`. This enables debugging and inspection (User Story 4).

```python
gen = registry.create("dungeon", seed=42, width=50, height=50)
map_data = gen.generate()

# Inspect intermediate state
for point, snapshot in gen.snapshots.items():
    print(f"{point}: {len(snapshot.grid)}x{len(snapshot.grid[0])}")
```
