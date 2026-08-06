# Contract: Configuration Pipeline

**@since**: 1.0.0

## `GenerationParams`

Typed, validated generation parameters passed to a generator.

```python
@dataclass
class GenerationParams:
    width: int
    height: int
    seed: int                       # 32-bit unsigned (0 to 2^32-1)
    max_iterations: int = 100       # retry/loop budget
    timeout_ms: int | None = None   # optional time budget
    content_constraints: list[ContentConstraint] = field(default_factory=list)
    # Generator-specific fields follow (e.g., room_min_size, octaves, etc.)
```

**Validation rules** (FR-004):
- Type checks: each field must be the correct type.
- Range checks: `width`/`height` within `[1, 1000]`; `seed` within `[0, 2^32-1]`.
- Consistency checks: e.g., `room_count` must not exceed grid area.
- Dependency checks: e.g., if `use_corridors=true`, `corridor_width ≥ 1`.

---

## `Preset`

A named, pre-defined configuration bundle.

```python
@dataclass
class Preset:
    name: str                       # unique, e.g. "small_dungeon"
    generator: str                  # target generator name
    params: dict                    # default parameter values
    description: str = ""           # human-readable description
```

---

## `Override`

User-supplied parameters that take precedence over preset values.

```python
# A plain dict: {param_name: value}
overrides: dict = {"width": 80, "room_count": 12}
```

---

## `ConfigResolver`

Resolves the layered configuration: `defaults < preset.params < overrides`.

```python
class ConfigResolver:
    def resolve(
        self,
        generator_name: str,
        preset_name: str | None = None,
        overrides: dict | None = None,
    ) -> GenerationParams:
        """Resolve and validate the final parameter set.

        Resolution order: defaults < preset.params < overrides.

        Args:
            generator_name: Target generator name.
            preset_name: Optional preset to apply.
            overrides: Optional user overrides.

        Returns:
            GenerationParams: Fully resolved and validated parameters.

        Raises:
            PresetNotFoundError: If `preset_name` is not registered.
            ValidationError: If any resolved parameter is invalid.
        """
```

### Usage Example

```python
from gamemapgen import ConfigResolver

resolver = ConfigResolver()
params = resolver.resolve(
    generator_name="dungeon",
    preset_name="small_dungeon",
    overrides={"width": 80, "room_count": 12},
)
# params.width == 80 (override wins)
# params.room_min_size == preset value (no override)
```

---

## Built-in Presets

| Preset | Generator | Description |
|--------|-----------|-------------|
| `small_dungeon` | `dungeon` | Compact 30x30 dungeon with 5-8 rooms |
| `epic_dungeon` | `dungeon` | Large 100x100 dungeon with 15-25 rooms |
| `tiny_maze` | `maze` | Small 21x21 maze |
| `large_maze` | `maze` | Large 101x101 maze |
| `island_world` | `open_world` | 100x100 island terrain with water borders |
| `continent_world` | `open_world` | 200x200 continental terrain |
