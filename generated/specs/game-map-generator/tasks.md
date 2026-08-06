# Tasks: Game Map Generation Component (GameMapGen)

**Input**: Design documents from `/specs/game-map-generator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE requested. The spec mandates ≥90% line coverage per generator, determinism tests (≥5 seeds), edge-case tests, serialization round-trip tests, and performance benchmarks. Tests are written FIRST and must FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/gamemapgen/` (single Python library package)
- **Tests**: `tests/` (unit/, integration/, contract/, benchmarks/)
- **Docs**: `docs/` (getting-started guide, demos)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic package structure

- [ ] T001 Create `src/gamemapgen/` package structure with `__init__.py`, `errors.py`, `prng.py`, `models.py`, `registry.py`, `config.py`, `constraints.py`, `hooks.py`, `composite.py`, `presets.py`, and `generators/` subpackage per plan.md
- [ ] T002 Create `tests/` directory structure with `conftest.py`, `unit/`, `integration/`, `contract/`, `benchmarks/` subdirectories
- [ ] T003 [P] Create `pyproject.toml` with project metadata, Python 3.11+ requirement, and dev dependencies (`pytest`, `pytest-cov`)
- [ ] T004 [P] Create `docs/` directory for getting-started guide and demos
- [ ] T005 [P] Create `README.md` at repository root with project overview and quick-start pointer

**Checkpoint**: Package skeleton ready. No user story work can begin until Phase 2 completes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (written FIRST, must FAIL)

- [ ] T006 [P] Unit tests for `PRNG` determinism and seed validation in `tests/unit/test_prng.py` (same seed → identical sequence; out-of-range seed → `ValidationError`)
- [ ] T007 [P] Unit tests for `TileTypeRegistry` in `tests/unit/test_registry.py` (register/get/is_registered/list/glyph; duplicate and unknown type → `ValidationError`)
- [ ] T008 [P] Unit tests for typed errors in `tests/unit/test_errors.py` (hierarchy, catchability, actionable messages)

### Implementation for Foundational

- [ ] T009 [P] Implement typed error hierarchy in `src/gamemapgen/errors.py` (`GameMapGenError` base → `ValidationError`, `GenerationError`, `ConstraintViolationError`, `PresetNotFoundError`, `GeneratorNotFoundError`)
- [ ] T010 [P] Implement `PRNG` class in `src/gamemapgen/prng.py` wrapping `random.Random` with 32-bit unsigned seed validation and methods `randint`, `random`, `uniform`, `choice`, `shuffle`, `sample`, `get_state`, `set_state`
- [ ] T011 [P] Implement `TileType` dataclass and `TileTypeRegistry` in `src/gamemapgen/registry.py` with 11 built-in tile types (WALL, FLOOR, WATER, LAVA, DOOR, STAIRS, EMPTY, GRASS, ROAD, BRIDGE, TRAP) and their glyphs
- [ ] T012 [P] Implement `GeneratorRegistry` in `src/gamemapgen/registry.py` with `register`, `get`, `list`, `create` methods (auto-registers built-in generators)
- [ ] T013 [P] Implement `ComplexityEstimate` dataclass in `src/gamemapgen/models.py` (`time`, `space`, `expected_ms`)
- [ ] T014 Implement `BaseGenerator` abstract class in `src/gamemapgen/generators/base.py` with abstract `generate`, `validate_params`, `complexity_estimate` and concrete `to_ascii` helper
- [ ] T015 Implement `__init__.py` public API exports in `src/gamemapgen/__init__.py` (all public types, `__version__` following SemVer)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Generate a Deterministic Map from Parameters (Priority: P1) 🎯 MVP

**Goal**: A developer provides a seed and generation parameters (map type, dimensions, density) and receives a complete, valid `MapData` structure. The same seed + parameters always produce identical output.

**Independent Test**: Invoke generation with a fixed seed and parameters, invoke again with the same inputs, and assert the two outputs are byte-for-byte identical. Also verify different seeds produce different maps, and invalid params raise a clear `ValidationError` with no map produced.

### Tests for User Story 1 (written FIRST, must FAIL) ⚠️

- [ ] T016 [P] [US1] Unit tests for `MapData`, `Tile`, `Position`, `MapMetadata`, `Region`, `Rect`, `Entity`, `Layer`, `AdjacencyGraph`, `Edge` dataclasses in `tests/unit/test_models.py` (construction, `to_dict`/`from_dict`, validation rules)
- [ ] T017 [P] [US1] Unit tests for `GenerationParams` validation in `tests/unit/test_config.py` (type, range, consistency, dependency checks; invalid params → `ValidationError` with actionable message)
- [ ] T018 [P] [US1] Unit tests for `DungeonGenerator` in `tests/unit/generators/test_dungeon.py` (valid output, determinism across ≥5 seeds, edge cases: min/max size, single-tile, extreme aspect ratio, invalid params)
- [ ] T019 [P] [US1] Unit tests for `OpenWorldGenerator` in `tests/unit/generators/test_open_world.py` (valid output, determinism across ≥5 seeds, edge cases, invalid params)
- [ ] T020 [P] [US1] Unit tests for `MazeGenerator` in `tests/unit/generators/test_maze.py` (valid output, odd-grid enforcement, determinism across ≥5 seeds, edge cases, invalid params)
- [ ] T021 [P] [US1] Contract test for serialization round-trip in `tests/contract/test_serialization.py` (MapData → JSON → MapData lossless for each generator)
- [ ] T022 [P] [US1] Integration test for deterministic generation pipeline in `tests/integration/test_pipeline.py` (registry.create → generate → byte-identical on repeat; different seed → different map)

### Implementation for User Story 1

- [ ] T023 [P] [US1] Implement `Position`, `Rect`, `Tile`, `MapMetadata`, `Region`, `Entity`, `Layer`, `Edge`, `AdjacencyGraph`, `MapData` dataclasses with `to_dict`/`from_dict`/`to_json`/`to_ascii` in `src/gamemapgen/models.py`
- [ ] T024 [P] [US1] Implement `GenerationParams` dataclass with validation logic in `src/gamemapgen/config.py` (type/range/consistency/dependency checks per data-model.md §2.1)
- [ ] T025 [P] [US1] Implement `DungeonGenerator` in `src/gamemapgen/generators/dungeon.py` (BSP room splitting + corridor connection, produces WALL/FLOOR/DOOR/STAIRS tiles, uses passed PRNG, `complexity_estimate` = O(n log n))
- [ ] T026 [P] [US1] Implement `OpenWorldGenerator` in `src/gamemapgen/generators/open_world.py` (Perlin noise heightmap + biome thresholding, produces GRASS/WATER/ROAD/BRIDGE tiles, uses passed PRNG, `complexity_estimate` = O(n × octaves))
- [ ] T027 [P] [US1] Implement `MazeGenerator` in `src/gamemapgen/generators/maze.py` (recursive backtracking on odd grid, produces WALL/FLOOR tiles, uses passed PRNG, `complexity_estimate` = O(n))
- [ ] T028 [US1] Implement `generators/__init__.py` in `src/gamemapgen/generators/__init__.py` exporting all three generators
- [ ] T029 [US1] Wire built-in generators into `GeneratorRegistry` auto-registration in `src/gamemapgen/registry.py` (dungeon, open_world, maze)
- [ ] T030 [US1] Implement `ConfigResolver` in `src/gamemapgen/config.py` (resolution order: defaults < preset.params < overrides; raises `PresetNotFoundError`/`ValidationError`)
- [ ] T031 [US1] Implement built-in presets in `src/gamemapgen/presets.py` (small_dungeon, epic_dungeon, tiny_maze, large_maze, island_world, continent_world per config.md)
- [ ] T032 [US1] Implement `max_iterations`/`timeout_ms` budget enforcement in `src/gamemapgen/generators/base.py` to prevent infinite loops (FR-010)

**Checkpoint**: User Story 1 fully functional and testable independently. This is the MVP.

---

## Phase 4: User Story 2 - Compose Multiple Generators into a Layered Map (Priority: P2)

**Goal**: A developer builds a complex map by layering multiple generators (e.g., base terrain, then road network, then building placement). Each layer consumes the previous layer's output, and the final result is a single coherent map.

**Independent Test**: Define a two-layer composition (e.g., terrain then roads) and assert the output contains both layers' contributions in the correct order, with each layer receiving the prior layer's output as input. Verify determinism for a fixed seed.

### Tests for User Story 2 (written FIRST, must FAIL) ⚠️

- [ ] T033 [P] [US2] Unit tests for `CompositeGenerator` in `tests/unit/test_composite.py` (layer ordering, each layer receives prior output, determinism, layer failure handling → rollback or `incomplete=True` flag)
- [ ] T034 [P] [US2] Integration test for composite layered generation in `tests/integration/test_pipeline.py` (two-layer composition produces coherent map with both layers in documented order)

### Implementation for User Story 2

- [ ] T035 [P] [US2] Implement `CompositeGenerator` in `src/gamemapgen/composite.py` (holds ordered `(name, generator)` layers; each layer receives previous `MapData`; threads same seeded PRNG through layers; `complexity_estimate` = O(k × n))
- [ ] T036 [US2] Implement graceful layer-failure handling in `src/gamemapgen/composite.py` (rollback to consistent state with `GenerationError`, or return partial result flagged `incomplete=True` per FR-012)
- [ ] T037 [US2] Register `CompositeGenerator` as a composable generator in `src/gamemapgen/registry.py` (FR-013)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Customize Generation via Hooks and Content Constraints (Priority: P3)

**Goal**: A developer injects custom logic at lifecycle points (e.g., placing quest items after room placement) and restricts generated content (e.g., banning tile types or enforcing an age-rating profile) without modifying core generator code.

**Independent Test**: Register a hook that places a marker entity after room placement and assert the marker appears in the output. Set a content constraint that bans a tile type and assert no banned tile appears in the output.

### Tests for User Story 3 (written FIRST, must FAIL) ⚠️

- [ ] T038 [P] [US3] Unit tests for `HookManager` and `GenerationContext` in `tests/unit/test_hooks.py` (registration order, chaining, unknown lifecycle point → `ValidationError`, hook exception → wrapped `GenerationError`, snapshot capture)
- [ ] T039 [P] [US3] Unit tests for content constraints in `tests/unit/test_constraints.py` (`BannedTileType`, `BannedEntityType`, `MaxDensity`, `AgeRatingProfile`; enforcement via retry-with-adjustment up to `max_iterations`; unresolved → `ConstraintViolationError` identifying offending constraint)
- [ ] T040 [P] [US3] Integration test for hooks + constraints in `tests/integration/test_pipeline.py` (register hook placing marker entity, add `BannedTileType`, verify marker appears and no banned tile exists)

### Implementation for User Story 3

- [ ] T041 [P] [US3] Implement `GenerationContext` dataclass in `src/gamemapgen/hooks.py` (`map_data`, `prng`, `params`, `snapshots`)
- [ ] T042 [P] [US3] Implement `HookManager` in `src/gamemapgen/hooks.py` (`register`, `unregister`, `run`, `list_hooks`; chainable hooks in registration order; snapshot capture at each lifecycle point)
- [ ] T043 [P] [US3] Implement `ContentConstraint` base and concrete types (`BannedTileType`, `BannedEntityType`, `MaxDensity`, `AgeRatingProfile`) in `src/gamemapgen/constraints.py`
- [ ] T044 [P] [US3] Implement constraint enforcement engine in `src/gamemapgen/constraints.py` (validate generated `MapData` against constraints; retry-with-adjustment up to `max_iterations`; raise `ConstraintViolationError` if unresolved)
- [ ] T045 [US3] Integrate `HookManager` and constraint enforcement into `BaseGenerator.generate` lifecycle in `src/gamemapgen/generators/base.py` (before_generation → after_room_placement → after_corridor_connection → post_process; constraint check before finalize)
- [ ] T046 [US3] Add `register_hook` and `add_constraint` convenience methods to `BaseGenerator` in `src/gamemapgen/generators/base.py`

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Debug and Inspect Generated Maps (Priority: P3)

**Goal**: A developer inspects a generated map as a human-readable text representation and reviews intermediate state at each hook point, without needing a game engine or rendering stack.

**Independent Test**: Generate a small map and assert a human-readable text representation is produced without any external rendering dependency, and that intermediate snapshots are available at documented hook points.

### Tests for User Story 4 (written FIRST, must FAIL) ⚠️

- [ ] T047 [P] [US4] Unit tests for `to_ascii` rendering in `tests/unit/test_models.py` (human-readable string, correct glyphs per tile type, no external rendering dependency)
- [ ] T048 [P] [US4] Unit tests for snapshot capture in `tests/unit/test_hooks.py` (snapshots available at each documented hook point: `before_generation`, `post_process`, etc.)

### Implementation for User Story 4

- [ ] T049 [P] [US4] Implement `MapData.to_ascii()` in `src/gamemapgen/models.py` using `TileTypeRegistry.glyph()` (single-character glyphs per tile type, no external rendering library)
- [ ] T050 [P] [US4] Implement `BaseGenerator.to_ascii(map_data)` in `src/gamemapgen/generators/base.py` delegating to `MapData.to_ascii()`
- [ ] T051 [US4] Expose `snapshots` on generator instances in `src/gamemapgen/generators/base.py` (populated from `GenerationContext.snapshots` after generation, per FR-027)

**Checkpoint**: All user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T052 [P] Create getting-started guide in `docs/getting-started.md` covering installation, generation pipeline, and hook system (constitution Principle XIII)
- [ ] T053 [P] Create runnable demo scripts in `docs/demos/` for each built-in generator (dungeon, open_world, maze) with example presets
- [ ] T054 [P] Create performance benchmark harness in `tests/benchmarks/bench_generation.py` verifying 100x100 grid <100ms (SC-001) and no regression >10% (SC-008)
- [ ] T055 [P] Add `@since`/`@deprecated` metadata annotations to all public types and functions in `src/gamemapgen/` (constitution Principle XI)
- [ ] T056 [P] Add docstrings with at least one runnable usage example per public method in `src/gamemapgen/` (constitution Principle XIII)
- [ ] T057 [P] Add edge-case tests for empty maps, single-tile maps, max-size maps, extreme aspect ratios, boundary seeds (0 and 2^32-1), and iteration-budget exhaustion in `tests/unit/` (spec Edge Cases)
- [ ] T058 [P] Add serialization round-trip tests for custom/unknown tile and entity types via registry-aware deserialization in `tests/contract/test_serialization.py` (SC-005)
- [ ] T059 Run quickstart.md validation scenarios as tests in `tests/integration/test_quickstart.py` (all 6 scenarios from quickstart.md)
- [ ] T060 Run full test suite with coverage: `pytest tests/ -v --cov=gamemapgen --cov-report=term-missing` and verify ≥90% line coverage per generator module
- [ ] T061 Verify no external runtime dependencies beyond standard library (audit imports in `src/gamemapgen/`)
- [ ] T062 Verify no hardcoded magic numbers (all tunable values are parameters with defaults) across `src/gamemapgen/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1's `MapData`/generators but is independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1's `BaseGenerator` lifecycle but is independently testable
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Depends on US1's `MapData.to_ascii` and US3's snapshot capture but is independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for models in tests/unit/test_models.py"
Task: "Unit tests for GenerationParams validation in tests/unit/test_config.py"
Task: "Unit tests for DungeonGenerator in tests/unit/generators/test_dungeon.py"
Task: "Unit tests for OpenWorldGenerator in tests/unit/generators/test_open_world.py"
Task: "Unit tests for MazeGenerator in tests/unit/generators/test_maze.py"
Task: "Contract test for serialization in tests/contract/test_serialization.py"
Task: "Integration test for deterministic pipeline in tests/integration/test_pipeline.py"

# Launch all models for User Story 1 together:
Task: "Implement models in src/gamemapgen/models.py"
Task: "Implement GenerationParams in src/gamemapgen/config.py"
Task: "Implement DungeonGenerator in src/gamemapgen/generators/dungeon.py"
Task: "Implement OpenWorldGenerator in src/gamemapgen/generators/open_world.py"
Task: "Implement MazeGenerator in src/gamemapgen/generators/maze.py"
```

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Unit tests for HookManager in tests/unit/test_hooks.py"
Task: "Unit tests for content constraints in tests/unit/test_constraints.py"
Task: "Integration test for hooks + constraints in tests/integration/test_pipeline.py"

# Launch all implementation for User Story 3 together:
Task: "Implement GenerationContext in src/gamemapgen/hooks.py"
Task: "Implement HookManager in src/gamemapgen/hooks.py"
Task: "Implement ContentConstraint types in src/gamemapgen/constraints.py"
Task: "Implement constraint enforcement in src/gamemapgen/constraints.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (determinism, validation, serialization)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- The existing `app/seed_manager.py` provides legacy algorithms (GridRandom, RoomSplit, RecursiveBacktrack, PerlinNoise) that serve as reference implementations for the new generators but are NOT reused directly
