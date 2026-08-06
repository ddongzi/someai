# Contract: Tile Type Registry

**@since**: 1.0.0

## `TileTypeRegistry`

Central registry for tile type definitions. Enables validation, content constraints, and extensibility.

```python
class TileTypeRegistry:
    def register(self, name: str, glyph: str, description: str = "") -> None:
        """Register a new tile type.

        Args:
            name: Unique tile type name (e.g., "WALL").
            glyph: Single-character ASCII glyph for debug rendering.
            description: Optional human-readable description.

        Raises:
            ValidationError: If `name` is already registered or invalid.
        """

    def get(self, name: str) -> TileType:
        """Get a registered tile type by name.

        Raises:
            ValidationError: If `name` is not registered.
        """

    def is_registered(self, name: str) -> bool:
        """Check if a tile type name is registered."""

    def list(self) -> list[str]:
        """List all registered tile type names."""

    def glyph(self, name: str) -> str:
        """Get the ASCII glyph for a tile type (for to_ascii rendering)."""
```

---

## `TileType`

```python
@dataclass(frozen=True)
class TileType:
    name: str                      # e.g., "WALL"
    glyph: str                     # single char, e.g., "#"
    description: str = ""          # human-readable description
```

---

## Built-in Tile Types

| Name | Glyph | Description |
|------|-------|-------------|
| `WALL` | `#` | Solid wall / obstacle |
| `FLOOR` | `.` | Walkable floor |
| `WATER` | `~` | Water (impassable or requires bridge) |
| `LAVA` | `^` | Lava (hazardous) |
| `DOOR` | `D` | Door (passable when open) |
| `STAIRS` | `>` | Stairs (level transition) |
| `EMPTY` | ` ` | Empty / uninitialized |
| `GRASS` | `,` | Grass terrain |
| `ROAD` | `=` | Road / path |
| `BRIDGE` | `B` | Bridge over water |
| `TRAP` | `x` | Trap (hazardous) |

---

## Usage Example

```python
from gamemapgen import TileTypeRegistry

registry = TileTypeRegistry()

# Check built-in types
assert registry.is_registered("WALL")
assert registry.is_registered("FLOOR")

# Register a custom tile type
registry.register("ICE", glyph="i", description="Slippery ice tile")

# Use in generation
assert registry.is_registered("ICE")
assert registry.glyph("ICE") == "i"

# Validation: unknown tile types rejected
try:
    registry.get("UNKNOWN")
except ValidationError:
    print("Unknown tile type rejected")
```

---

## Extensibility

Consumers can register custom tile types at runtime. Custom types are preserved through serialization round-trips via registry-aware deserialization.

```python
# Custom tile type for a game-specific feature
registry.register("PORTAL", glyph="O", description="Teleportation portal")

# Generators can use custom types
gen = registry.create("dungeon", seed=42, width=50, height=50)
gen.register_tile_type("PORTAL")
```
