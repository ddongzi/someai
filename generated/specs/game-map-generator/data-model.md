# Data Model: Game Map Generation Component

**Phase 1 Output** | **Date**: 2026-08-05 | **Branch**: `game-map-generator`

This document defines the canonical data structures, entities, validation rules, and state transitions for GameMapGen. All structures are pure data (dataclasses) and JSON-serializable without loss.

---

## 1. Core Entities

### 1.1 `MapData` — Canonical Output

The top-level output of every generator. Pure data, JSON-serializable.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | `list[list[Tile]]` | ✅ | 2D array of tiles, indexed `grid[y][x]`. |
| `metadata` | `MapMetadata` | ✅ | Generation parameters, seed, version, timestamp. |
| `regions` | `list[Region]` | ⬜ | Named zones with bounds. |
| `entities` | `list[Entity]` | ⬜ | Placed objects (spawns, items, NPCs). |
| `layers` | `list[Layer]` | ⬜ | Ordered sub-maps for multi-layer maps. |
| `adjacency` | `AdjacencyGraph` | ⬜ | Graph for pathfinding/connectivity. |

**Validation rules**:
- `grid` must be non-empty and rectangular (all rows same length).
- `grid` dimensions must match `metadata.width` and `metadata.height`.
- Every `Tile` in `grid` must have a valid registered tile type.
- `regions` bounds must be within grid dimensions.
- `entities` positions must be within grid bounds.
- `metadata` must include `seed`, `generator_version`, and `timestamp`.

**State transitions**:
- `EMPTY` (uninitialized) → `GENERATING` (in-progress) → `COMPLETE` (valid output) or `INCOMPLETE` (flagged partial result).
- A `MapData` is only returned to consumers in `COMPLETE` state unless explicitly flagged `incomplete` in metadata (FR-019, FR-020).

### 1.2 `Tile` — Atomic Grid Cell

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | ✅ | Registered tile type name (e.g., `"WALL"`). |
| `position` | `Position` | ✅ | `{x: int, y: int}`. |
| `metadata` | `dict` | ✅ | Extensible properties (elevation, biome, temperature). |

**Validation rules**:
- `type` must be a registered tile type (via `TileTypeRegistry`).
- `position.x` and `position.y` must be non-negative integers.
- `metadata` must be JSON-serializable.

### 1.3 `Position`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `int` | ✅ | Column index (0-based). |
| `y` | `int` | ✅ | Row index (0-based). |

### 1.4 `MapMetadata`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parameters` | `dict` | ✅ | Full resolved generation parameters. |
| `seed` | `int` | ✅ | 32-bit unsigned seed used. |
| `generator_version` | `str` | ✅ | SemVer of the generator. |
| `timestamp` | `str` | ✅ | ISO 8601 timestamp. |
| `incomplete` | `bool` | ⬜ | `True` if partial result (default `False`). |
| `generator_name` | `str` | ✅ | Name of the generator that produced this map. |

### 1.5 `Region` — Named Zone

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | ✅ | Unique region name. |
| `bounds` | `Rect` | ✅ | Rectangular bounds. |
| `properties` | `dict` | ⬜ | Extensible region properties. |

**Validation**: `bounds` must be within grid dimensions.

### 1.6 `Rect`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `int` | ✅ | Left column. |
| `y` | `int` | ✅ | Top row. |
| `width` | `int` | ✅ | Width (≥1). |
| `height` | `int` | ✅ | Height (≥1). |

### 1.7 `Entity` — Placed Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | ✅ | Entity type (e.g., `"spawn"`, `"item"`, `"npc"`). |
| `position` | `Position` | ✅ | Placement position. |
| `properties` | `dict` | ⬜ | Extensible entity properties. |

**Validation**: `position` within grid bounds; `type` non-empty.

### 1.8 `Layer` — Sub-Map

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | ✅ | Layer name (e.g., `"terrain"`, `"objects"`). |
| `grid` | `list[list[Tile]]` | ✅ | Sub-map grid. |
| `metadata` | `dict` | ⬜ | Layer-specific metadata. |

### 1.9 `AdjacencyGraph` — Connectivity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodes` | `list[Position]` | ✅ | Node positions. |
| `edges` | `list[Edge]` | ✅ | Undirected edges between nodes. |

### 1.10 `Edge`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | `Position` | ✅ | Source node. |
| `to` | `Position` | ✅ | Target node. |
| `weight` | `float` | ⬜ | Edge weight (default `1.0`). |

---

## 2. Configuration Entities

### 2.1 `GenerationParams` — Typed Parameters

The resolved, validated parameter set passed to a generator. Fields vary per generator but share common ones:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `width` | `int` | ✅ | Grid width (range per generator, e.g., 1–1000). |
| `height` | `int` | ✅ | Grid height (range per generator). |
| `seed` | `int` | ✅ | 32-bit unsigned seed. |
| `max_iterations` | `int` | ⬜ | Retry/loop budget (default e.g., 100). |
| `content_constraints` | `list[ContentConstraint]` | ⬜ | Content safety rules. |
| `timeout_ms` | `int` | ⬜ | Optional time budget. |

**Generator-specific params** (examples):
- **Dungeon**: `room_min_size`, `room_max_size`, `room_count`, `corridor_width`, `use_corridors`.
- **Maze**: `cell_size` (odd grid enforcement).
- **OpenWorld**: `octaves`, `frequency`, `water_level`, `biome_thresholds`.

**Validation rules** (FR-006):
- Type checks: each param must be the correct type.
- Range checks: `width`/`height` within `[1, 1000]`; `seed` within `[0, 2^32-1]`.
- Consistency checks: `room_count` must not exceed grid area; `room_min_size ≤ room_max_size`.
- Dependency checks: if `use_corridors=true`, `corridor_width ≥ 1`.

### 2.2 `Preset` — Named Config Bundle

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | ✅ | Unique preset name (e.g., `"small_dungeon"`). |
| `generator` | `str` | ✅ | Target generator name. |
| `params` | `dict` | ✅ | Default parameter values. |
| `description` | `str` | ⬜ | Human-readable description. |

### 2.3 `Override` — User-Supplied Params

A `dict` of parameter name → value that takes precedence over preset values. Validated against the generator's parameter schema.

**Resolution order**: `defaults < preset.params < overrides`.

---

## 3. Constraint Entities

### 3.1 `ContentConstraint` (base)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | ✅ | Constraint type discriminator. |
| `message` | `str` | ⬜ | Custom error message. |

### 3.2 `BannedTileType`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"banned_tile"` | ✅ | Discriminator. |
| `tile_types` | `list[str]` | ✅ | Tile types to forbid. |

### 3.3 `BannedEntityType`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"banned_entity"` | ✅ | Discriminator. |
| `entity_types` | `list[str]` | ✅ | Entity types to forbid. |

### 3.4 `MaxDensity`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"max_density"` | ✅ | Discriminator. |
| `tile_type` | `str` | ✅ | Tile type to limit. |
| `max_ratio` | `float` | ✅ | Max fraction of grid (0.0–1.0). |

### 3.5 `AgeRatingProfile`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"age_rating"` | ✅ | Discriminator. |
| `profile` | `str` | ✅ | e.g., `"E"`, `"T"`, `"M"`. |
| `banned_tiles` | `list[str]` | ✅ | Tiles forbidden for this rating. |
| `banned_entities` | `list[str]` | ✅ | Entities forbidden for this rating. |

---

## 4. Hook & Context Entities

### 4.1 `GenerationContext`

The mutable context threaded through generation and passed to hooks.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `map_data` | `MapData` | ✅ | In-progress map. |
| `prng` | `PRNG` | ✅ | Seeded PRNG instance. |
| `params` | `GenerationParams` | ✅ | Resolved parameters. |
| `snapshots` | `dict[str, MapData]` | ⬜ | Intermediate state snapshots at each hook point (FR-027). |

### 4.2 `Hook`

A callable with signature `hook(context: GenerationContext) -> GenerationContext`. Registered against a named lifecycle point.

**Lifecycle points** (extensible):
- `before_generation`
- `after_room_placement`
- `after_corridor_connection`
- `post_process`

---

## 5. Registry Entities

### 5.1 `GeneratorRegistry`

Maps generator name → generator factory/class. Built-ins: `dungeon`, `open_world`, `maze`. Supports `register()`, `get()`, `list()`, `create()`.

### 5.2 `TileTypeRegistry`

Maps tile type name → `TileType` definition. Built-ins: `WALL`, `FLOOR`, `WATER`, `LAVA`, `DOOR`, `STAIRS`, `EMPTY`, `GRASS`, `ROAD`, `BRIDGE`, `TRAP`. Supports `register()`, `get()`, `is_registered()`.

---

## 6. State Transitions

### 6.1 Generation Lifecycle

```
[Validate params] → [Resolve config] → [before_generation hook]
    → [Generate core structure] → [after_room_placement hook]
    → [Connect/refine] → [after_corridor_connection hook]
    → [Enforce constraints (retry loop)] → [post_process hook]
    → [Finalize MapData + metadata]
```

- **Validation failure** → raise `ValidationError` (no generation starts).
- **Constraint violation after retries** → raise `ConstraintViolationError`.
- **Mid-generation failure** → roll back to consistent state and raise `GenerationError`, OR return `MapData` flagged `incomplete=True` (FR-019).
- **Hook exception** → propagate as `GenerationError` wrapping the hook error (edge case).

### 6.2 MapData State

- `EMPTY` → `GENERATING` → `COMPLETE` (returned to consumer)
- `GENERATING` → `INCOMPLETE` (flagged partial, returned with `incomplete=True`)
- `GENERATING` → `FAILED` (rolled back, `GenerationError` raised)

---

## 7. Serialization Contract

All entities implement `to_dict()` and `from_dict()` (or equivalent) guaranteeing lossless JSON round-trip:

```
MapData → to_dict() → json.dumps → json.loads → from_dict() → MapData (identical)
```

- `metadata.timestamp` preserved as ISO 8601 string.
- `metadata.parameters` preserved exactly.
- Nested structures (`Tile`, `Region`, `Entity`, `Layer`, `AdjacencyGraph`) all round-trip losslessly.
- Unknown/custom tile types and entity types preserved via registry-aware deserialization.

---

## 8. Complexity Documentation (Big-O)

| Generator | Time | Space |
|-----------|------|-------|
| Dungeon (BSP) | `O(n log n)` where n = grid cells | `O(n)` |
| Maze (recursive backtrack) | `O(n)` | `O(n)` (recursion stack) |
| OpenWorld (Perlin) | `O(n × octaves)` | `O(n)` |
| Composite (k layers) | `O(k × n)` | `O(k × n)` |

Each generator exposes `complexity_estimate(params) -> ComplexityEstimate` returning expected time/space before generation (FR-026).
