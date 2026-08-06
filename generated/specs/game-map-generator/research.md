# Research: Game Map Generation Component

**Phase 0 Output** | **Date**: 2026-08-05 | **Branch**: `game-map-generator`

This document resolves all `NEEDS CLARIFICATION` items from the Technical Context and documents best-practice decisions for the technology choices. Each entry follows the format: **Decision / Rationale / Alternatives considered**.

---

## 1. Language & Runtime

**Decision**: Python 3.11+ (standard library only for runtime).

**Rationale**: The existing codebase (`app/app.py`, `app/seed_manager.py`) is already Python. The constitution mandates "no external runtime dependencies beyond the standard library," which Python satisfies natively (`random`, `json`, `dataclasses`, `typing`, `abc`, `time`). Python's `random.Random` provides a deterministic, seedable PRNG. Dataclasses + `asdict`/`from_dict` give clean JSON round-trip serialization.

**Alternatives considered**:
- **Rust**: Excellent performance and determinism, but would require a full rewrite and contradicts the existing Python codebase.
- **TypeScript/Node**: Good ecosystem, but `Math.random()` is not seedable without a custom PRNG, and the existing code is Python.
- **C#**: Strong game ecosystem, but not aligned with the existing Python foundation.

---

## 2. Seeded PRNG Strategy

**Decision**: Use Python's `random.Random` wrapped in a dedicated `PRNG` class that is explicitly constructed with a 32-bit unsigned integer seed and passed into every generator. Never use module-level `random.*` functions.

**Rationale**: The constitution (Principle II) mandates a seeded PRNG passed explicitly, not global randomness. `random.Random(seed)` is deterministic across runs and platforms for the same seed. Wrapping it in a `PRNG` class:
- Enforces the 32-bit unsigned seed contract (FR-003).
- Provides a single injection point for determinism.
- Allows the same PRNG instance to be threaded through composite layers for reproducible multi-pass generation.

**Alternatives considered**:
- **`numpy.random.default_rng`**: Deterministic and fast, but adds an external runtime dependency (violates constitution).
- **Custom xorshift/PCG PRNG**: More control, but reinventing the wheel; `random.Random` (Mersenne Twister) is sufficient and battle-tested.

---

## 3. Map Generation Algorithms

### 3a. Dungeon Generation (BSP Room Splitting)

**Decision**: Binary Space Partitioning (BSP) with recursive room carving and corridor connection.

**Rationale**: BSP produces well-structured, non-overlapping rooms connected by corridors — the canonical dungeon layout. It is deterministic given a seeded PRNG, has documented `O(n log n)` complexity, and is a well-understood algorithm. The existing `RoomSplit` algorithm in `seed_manager.py` is a starting point but needs refinement to produce proper `Tile` objects with types (`WALL`, `FLOOR`, `DOOR`, `STAIRS`) and metadata.

**Alternatives considered**:
- **Cellular automata**: Good for caves, but produces organic blobs rather than structured dungeons.
- **Random room placement + connection**: Simpler but produces overlapping/irregular layouts.

### 3b. Maze Generation (Recursive Backtracking)

**Decision**: Recursive backtracking (depth-first) maze generation on an odd-sized grid.

**Rationale**: Produces perfect mazes (exactly one path between any two cells) with a single connected component. Deterministic with a seeded PRNG. The existing `RecursiveBacktrack` algorithm is a solid foundation. Complexity is `O(width × height)`.

**Alternatives considered**:
- **Kruskal's / Prim's algorithms**: Also produce perfect mazes but are more complex to implement and less intuitive for debugging.
- **Eller's algorithm**: Memory-efficient for streaming, but overkill for in-memory grids.

### 3c. Open-World Generation (Perlin Noise)

**Decision**: Value/Perlin noise-based heightmap with biome thresholding.

**Rationale**: Produces natural-looking terrain (grass, water, mountains) suitable for open-world maps. The existing `PerlinNoise` algorithm provides a simplified foundation. We'll implement a proper seeded Perlin noise with configurable octaves, frequency, and biome thresholds mapping noise values to tile types (`GRASS`, `WATER`, `ROAD`, `BRIDGE`, etc.).

**Alternatives considered**:
- **Simplex noise**: Better quality but more complex; Perlin is sufficient and well-documented.
- **Diamond-square**: Produces fractal terrain but with visible artifacts; Perlin is smoother.

---

## 4. Layered Configuration Pipeline (Presets / Overrides / Defaults)

**Decision**: A three-tier resolution model: `defaults < presets < overrides`. A `ConfigResolver` merges these tiers in order, then validates the merged result against a typed parameter schema.

**Rationale**: The constitution (Principle III) mandates this exact layered model. Each parameter is typed with validation rules (range, type, consistency). Resolution order guarantees: overrides always win, then presets, then defaults. Unknown preset names raise a clear `ValidationError` (User Story 2, acceptance 3).

**Alternatives considered**:
- **Single flat config dict**: Simpler but loses the preset/override distinction and makes defaults implicit.
- **Deep merge of nested dicts**: More flexible but harder to validate and document.

---

## 5. Hook System (Lifecycle Hooks)

**Decision**: A `HookManager` that registers callables against named lifecycle points (`before_generation`, `after_room_placement`, `post_process`, etc.). Each hook has signature `hook(context: GenerationContext) -> GenerationContext`. Hooks of the same type execute in registration order (chainable). Intermediate state snapshots are captured at each hook point for debugging (FR-027).

**Rationale**: The constitution (Principle VII) mandates this exact signature and chaining behavior. The `GenerationContext` carries the in-progress `MapData` and PRNG, allowing hooks to read/modify state. Returning a modified context ensures subsequent steps use the hook's changes (User Story 4, acceptance 3).

**Alternatives considered**:
- **Event emitter / pub-sub**: More decoupled but harder to guarantee ordering and return-value propagation.
- **Decorator-based registration**: Cleaner syntax but less flexible for runtime registration and chaining.

---

## 6. Content Constraint Enforcement

**Decision**: A `ContentConstraint` model with types: `BannedTileType`, `BannedEntityType`, `MaxDensity`, `AgeRatingProfile`. Constraints are validated against the generated `MapData`. On violation, the generator retries with adjusted parameters up to `max_iterations`; if still unsatisfied, raises a typed `ConstraintViolationError` identifying the offending constraint.

**Rationale**: The constitution (Principle X) mandates either retry-with-adjustment or clear failure. The retry loop is bounded by `max_iterations` (FR-017) to prevent infinite loops. Each constraint type has a clear, actionable error message (FR-006).

**Alternatives considered**:
- **Post-hoc filtering only**: Simpler but can leave holes/inconsistencies in the map.
- **Hard rejection without retry**: Simpler but fails more often; retry improves success rate within budget.

---

## 7. Composite Generation (Layering)

**Decision**: A `CompositeGenerator` that holds an ordered list of `(name, generator)` layers. Each layer receives the previous layer's `MapData` as input and produces the next. Layer ordering is explicit and documented. The composite is itself a `Generator` (registered in the registry) and is deterministic given the same seed and layer order.

**Rationale**: The constitution (Principle VIII) mandates this exact composition model. Each layer is a self-contained generator, so composition is trivial and testable. Determinism is preserved because each layer uses the same seeded PRNG threaded through the context.

**Alternatives considered**:
- **Pipeline of functions**: Less structured; loses the generator abstraction and registry integration.
- **Nested generators**: Harder to reason about ordering and to document.

---

## 8. JSON Serialization Round-Trip

**Decision**: `MapData` and all nested structures (`Tile`, `Region`, `Entity`, `Layer`, `AdjacencyGraph`) are dataclasses. Provide `to_dict()` / `from_dict()` methods (or use `dataclasses.asdict` + a custom `from_dict`) that guarantee lossless JSON round-trip (MapData → JSON → MapData).

**Rationale**: The constitution (Principle IV) mandates JSON-serializable output without loss. Dataclasses give clean, typed structures; explicit `to_dict`/`from_dict` methods ensure the round-trip is lossless and validated (SC-005). Metadata includes parameters, seed, generator version, and timestamp (FR-030).

**Alternatives considered**:
- **Plain dicts**: Simpler but lose type safety and validation.
- **Pydantic**: Excellent validation but adds an external runtime dependency (violates constitution).

---

## 9. Performance Budget & Complexity

**Decision**: Each generator documents Big-O time/space complexity. A `complexity_estimate(params)` method returns expected cost before generation. A `max_iterations`/`timeout_ms` parameter bounds generation. Benchmarks (pytest-benchmark or a simple timing harness) verify the 100x100 grid <100ms budget (SC-001) and guard against >10% regression (SC-008).

**Rationale**: The constitution (Principle VI) mandates Big-O documentation, `max_iterations`, and `complexity_estimate`. The 100ms budget for a 100x100 grid is achievable with pure-Python algorithms (BSP, recursive backtracking, Perlin noise all run in well under 100ms for 10k tiles).

**Alternatives considered**:
- **NumPy vectorization**: Faster but adds an external runtime dependency.
- **Cython/C extensions**: Faster but complex and not standard-library-only.

---

## 10. Error Handling & Typed Errors

**Decision**: A hierarchy of typed exceptions: `GameMapGenError` (base) → `ValidationError`, `GenerationError`, `ConstraintViolationError`, `PresetNotFoundError`, `GeneratorNotFoundError`. All are catchable and carry actionable messages identifying the offending parameter/constraint.

**Rationale**: The constitution (Principle XII) mandates typed, catchable errors. A clear hierarchy lets consumers catch specific failure modes (retry on constraint violation, fallback on generation failure) while a common base allows broad handling.

**Alternatives considered**:
- **Single generic exception**: Simpler but loses the ability to distinguish failure modes.
- **Return-code / result objects**: More verbose; exceptions are idiomatic Python.

---

## 11. Tile Type Registry

**Decision**: A `TileTypeRegistry` that maps string names to `TileType` definitions. Built-in types: `WALL`, `FLOOR`, `WATER`, `LAVA`, `DOOR`, `STAIRS`, `EMPTY`, `GRASS`, `ROAD`, `BRIDGE`, `TRAP` (FR-028). Consumers can register custom tile types.

**Rationale**: The constitution mandates extensible tile types via a registry. Centralizing tile type definitions enables validation (unknown tile types rejected), content constraints (banned types), and extensibility.

**Alternatives considered**:
- **Hardcoded string constants**: Simpler but not extensible and harder to validate.
- **Enum**: Type-safe but not extensible at runtime.

---

## 12. Generator Registry

**Decision**: A `GeneratorRegistry` that maps generator names to generator classes/factories. Built-in generators (`dungeon`, `open_world`, `maze`) are auto-registered. Consumers can register custom generators. The registry enables discovery (list available generators) and composition (composite layers reference registered generators).

**Rationale**: The constitution (Principle I) mandates a central `GeneratorRegistry`. This enables plug-and-play addition of new map types and runtime discovery.

**Alternatives considered**:
- **Direct imports**: Simpler but no discovery or runtime registration.
- **Entry-points plugin system**: More flexible but adds complexity and packaging requirements.

---

## 13. Debug Rendering (`to_ascii`)

**Decision**: Each generator (and `MapData`) provides a `to_ascii()` method returning a human-readable string using single-character glyphs per tile type (e.g., `#`=WALL, `.`=FLOOR, `~`=WATER). No external rendering dependency.

**Rationale**: The constitution (Principle IX) mandates `to_ascii()`/`debug_render()` without external libraries. This enables unit-test assertions, CI validation, and CLI debugging.

**Alternatives considered**:
- **Rich/color output**: Nicer but adds a dependency.
- **Image rendering (PIL)**: Violates "no rendering" and adds a dependency.

---

## 14. Semantic Versioning & API Stability

**Decision**: Public API versioned via `__version__` following SemVer. All public types/functions annotated with `@since` and `@deprecated` metadata. Breaking changes only in MAJOR bumps with a migration guide.

**Rationale**: The constitution (Principle XI) mandates SemVer and metadata annotations. This protects downstream consumers.

**Alternatives considered**: None — this is a hard constitution requirement.

---

## Summary of Resolved Decisions

| Topic | Decision |
|-------|----------|
| Language | Python 3.11+, stdlib only |
| PRNG | `random.Random` wrapped in `PRNG` class, passed explicitly |
| Dungeon | BSP room splitting + corridors |
| Maze | Recursive backtracking |
| Open-world | Perlin noise + biome thresholding |
| Config | defaults < presets < overrides, validated |
| Hooks | `HookManager`, `hook(ctx)->ctx`, chainable |
| Constraints | retry-with-adjustment up to `max_iterations`, else typed error |
| Composition | `CompositeGenerator` with ordered layers |
| Serialization | dataclasses + `to_dict`/`from_dict`, lossless |
| Performance | Big-O docs, `complexity_estimate`, `max_iterations`, benchmarks |
| Errors | typed hierarchy: `ValidationError`, `GenerationError`, `ConstraintViolationError` |
| Tile types | `TileTypeRegistry`, 11 built-in types |
| Generators | `GeneratorRegistry`, auto-registered built-ins |
| Debug | `to_ascii()` per generator and `MapData` |
| Versioning | SemVer, `@since`/`@deprecated` annotations |
