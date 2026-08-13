# Tasks: Game Map Generation Component (GameMapGen)

**Input**: Design documents from `/specs/game-map-generator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE requested. The spec mandates ≥90% line coverage per generator, determinism tests (≥5 seeds), edge-case tests, serialization round-trip tests, and performance benchmarks. Tests are written FIRST and must FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User stories map directly to spec.md priorities.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Story Map (from spec.md)

| Story | Priority | Title | MVP |
|-------|----------|-------|-----|
| US1 | P1 | Generate a Playable Dungeon from a Preset | ✅ Core MVP |
| US2 | P1 | Reproduce the Same World with a Seed | ✅ Core MVP (determinism is non-negotiable) |
| US3 | P2 | Compose Complex Maps from Layers | |
| US4 | P2 | Customize Maps via Hooks | |
| US5 | P3 | Enforce Content Constraints | |

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

- [ ] T006 [P] Unit tests for `PRNG` determinism and seed validation in `tests/unit/test_prng.py` (same seed → identical sequence; out-of-range seed → `ValidationError`; seed validated as 32-bit unsigned per FR-002)
- [ ] T007 [P] Unit tests for `TileTypeRegistry` in `tests/unit/test_registry.py` (register/get/is_registered/list/glyph; duplicate and unknown type → `ValidationError`)
- [ ] T008 [P] Unit tests for typed errors in `tests/unit/test_errors.py` (hierarchy, catchability, actionable messages identifying offending parameter)

### Implementation for Foundational

- [ ] T009 [P] Implement typed error hierarchy in `src/gamemapgen/errors.py` (`GameMapGenError` base → `ValidationError`, `GenerationError`, `ConstraintViolationError`, `PresetNotFoundError`, `GeneratorNotFoundError`), each with actionable messages per Principle XII
- [ ] T010 [P] Implement `PRNG` class in `src/gamemapgen/prng.py` wrapping `random.Random` with 32-bit unsigned seed validation and methods `randint`, `random`, `uniform`, `choice`, `shuffle`, `sample`, `get_state`, `set_state`
- [ ] T011 [P] Implement `TileType` dataclass and `TileTypeRegistry` in `src/gamemapgen/registry.py` with 11 built-in tile types (WALL, FLOOR, WATER, LAVA, DOOR, STAIRS, EMPTY, GRASS, ROAD, BRIDGE, TRAP) and their glyphs (e.g., `#`, `.`, `~`)
- [ ] T012 [P] Implement `GeneratorRegistry` in `src/gamemapgen/registry.py` with `register`, `get`, `list`, `create` methods (auto-registers built-in generators)
- [ ] T013 [P] Implement `ComplexityEstimate` dataclass in `src/gamemapgen/models.py` (`time`, `space`, `expected_ms`)
- [ ] T014 Implement `BaseGenerator` abstract class in `src/gamemapgen/generators/base.py` with abstract `generate`, `validate_params`, `complexity_estimate` and concrete `to_ascii` helper (per Principle IX)
- [ ] T015 Implement `__init__.py` public API exports in `src/gamemapgen/__init__.py` (all public types, `__version__` following SemVer per Principle XI)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Generate a Playable Dungeon from a Preset (Priority: P1) 🎯 MVP

**Goal**: A game developer generates a complete, playable dungeon map with a single command using a built-in named preset (e.g., `"small_dungeon"`) and a seed, receiving a valid `MapData` with a fully-populated tile grid (walls, floors, at least one connected playable region) — with no generation logic required.

**Independent Test**: Invoke a generator with a named preset and a seed, then assert a valid `MapData` is returned containing a populated grid with WALL/FLOOR tiles and at least one connected playable region whose dimensions match the preset. An unknown preset name raises a clear actionable error listing available options (spec US1 acceptance 3).

### Tests for User Story 1 (written FIRST, must FAIL) ⚠️

- [ ] T016 [P] [US1] Unit tests for `MapData`, `Tile`, `Position`, `MapMetadata`, `Region`, `Rect`, `Entity`, `Layer`, `AdjacencyGraph`, `Edge` dataclasses in `tests/unit/test_models.py` (construction, `to_dict`/`from_dict`, validation rules, `to_ascii`)
- [ ] T017 [P] [US1] Unit tests for `GenerationParams` validation in `tests/unit/test_config.py` (type, range, consistency, dependency checks; invalid params → `ValidationError` with actionable message naming the offending parameter and valid range)
- [ ] T018 [P] [US1] Unit tests for `DungeonGenerator` in `tests/unit/generators/test_dungeon.py` (valid output with WALL/FLOOR/DOOR/STAIRS, connected region, edge cases: min/max size, single-tile, extreme aspect ratio, invalid params)
- [ ] T019 [P] [US1] Unit tests for `OpenWorldGenerator` in `tests/unit/generators/test_open_world.py` (valid output, edge cases, invalid params)
- [ ] T020 [P] [US1] Unit tests for `MazeGenerator` in `tests/unit/generators/test_maze.py` (valid output, odd-grid enforcement, edge cases, invalid params)
- [ ] T021 [P] [US1] Unit tests for preset resolution in `tests/unit/test_presets.py` (generate from `"small_dungeon"` preset → valid `MapData` with preset dimensions; unknown preset → `PresetNotFoundError` listing available presets; overrides take precedence)
- [ ] T022 [P] [US1] Contract test for serialization round-trip in `tests/contract/test_serialization.py` (MapData → JSON → MapData lossless for each generator)

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
- [ ] T032 [US1] Implement `max_iterations`/`timeout_ms` budget enforcement in `src/gamemapgen/generators/base.py` to prevent infinite loops (FR-012)

**Checkpoint**: User Story 1 fully functional and testable independently. This is the core MVP.

---

## Phase 4: User Story 2 - Reproduce the Same World with a Seed (Priority: P1) 🎯 MVP

**Goal**: A game developer reliably reproduces the identical world by reusing the same seed and parameters, for sharing worlds, debugging levels, and synchronizing multiplayer sessions. Same seed → byte-identical output; different seeds → different maps; no global/environment randomness leaks in.

**Independent Test**: Generate a map twice with the same seed and fixed parameters and assert the two outputs are byte-identical across every field (grid, regions, entities, metadata). Two different seeds with otherwise identical parameters produce differing outputs, proving the seed drives randomness.

### Tests for User Story 2 (written FIRST, must FAIL) ⚠️

- [ ] T033 [P] [US2] Unit tests for determinism in `tests/unit/test_determinism.py` (each generator run with ≥5 distinct seeds, two runs per seed → byte-identical `to_json` output; different seeds → different output, per SC-002)
- [ ] T034 [P] [US2] Contract test for byte-identical serialization determinism in `tests/contract/test_serialization.py` (serialized JSON of two same-seed runs is byte-identical; serialized JSON of different seeds differs)
- [ ] T035 [P] [US2] Integration test for cross-process/no-global-randomness determinism in `tests/integration/test_pipeline.py` (two separately-constructed registry+generator instances with same seed produce identical output; monkeypatch module-level `random` usage detection)

### Implementation for User Story 2

- [ ] T036 [P] [US2] Ensure each generator's `generate` uses ONLY the explicitly-passed seeded `PRNG` and never module-level `random.*` functions in `src/gamemapgen/generators/*.py` (audit + fix all randomness sources)
- [ ] T037 [P] [US2] Implement deterministic, byte-stable `MapData.to_json()` in `src/gamemapgen/models.py` (stable key ordering and formatting so identical maps serialize identically regardless of dict insertion order)
- [ ] T038 [P] [US2] Isolate PRNG state per generation call in `src/gamemapgen/prng.py` and `src/gamemapgen/generators/base.py` (fresh PRNG constructed from seed at start of each `generate`; `get_state`/`set_state` snapshots to prevent cross-run contamination)
- [ ] T039 [US2] Record full resolved parameters (seed + all params) in `MapMetadata.parameters` in `src/gamemapgen/models.py` so a map is fully reproducible from its metadata (spec FR metadata contract)

**Checkpoint**: User Stories 1 AND 2 (core MVP) both work independently.

---

## Phase 5: User Story 3 - Compose Complex Maps from Layers (Priority: P2)

**Goal**: A game developer layers multiple generators (e.g., terrain → roads → buildings → details) through a `CompositeGenerator` pipeline, where each layer consumes the previous layer's output and the final result is a single coherent multi-layer map.

**Independent Test**: Configure a `CompositeGenerator` with an ordered list of sub-generators and assert each layer receives the previous layer's output, the final result reflects all layers applied in the declared order, and `map_data.layers` preserves the documented order. A mid-pipeline layer failure rolls back to a consistent state or returns a partial result flagged `incomplete=True` — never corrupt data (FR-014).

### Tests for User Story 3 (written FIRST, must FAIL) ⚠️

- [ ] T040 [P] [US3] Unit tests for `CompositeGenerator` in `tests/unit/test_composite.py` (layer ordering, each layer receives prior output, determinism for fixed seed, layer failure handling → rollback or `incomplete=True` flag)
- [ ] T041 [P] [US3] Integration test for composite layered generation in `tests/integration/test_pipeline.py` (two-layer composition produces coherent map with both layers in documented order, e.g., terrain then roads)

### Implementation for User Story 3

- [ ] T042 [P] [US3] Implement `CompositeGenerator` in `src/gamemapgen/composite.py` (holds ordered `(name, generator)` layers; each layer receives previous `MapData`; threads same seeded PRNG through layers; `complexity_estimate` = O(k × n))
- [ ] T043 [US3] Implement graceful layer-failure handling in `src/gamemapgen/composite.py` (rollback to consistent state with `GenerationError`, or return partial result flagged `incomplete=True` per FR-014)
- [ ] T044 [US3] Register `CompositeGenerator` as a composable generator in `src/gamemapgen/registry.py` (FR-007) and expose `layers` list on resulting `MapData`

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Customize Maps via Hooks (Priority: P2)

**Goal**: A game developer injects custom logic at documented lifecycle points (e.g., `after_room_placement`, `post_process`) to tailor maps (quest items, biome rules, decorations) without modifying generator source. Hooks receive a valid `GenerationContext` and are chainable in registration order.

**Independent Test**: Register a custom hook at a documented lifecycle point and assert it is invoked with a valid `GenerationContext` whose returned context is used by subsequent steps. Multiple hooks of the same type execute in registration order, chainable (each output feeds the next), and mutations are reflected in the final `MapData` (spec US4 acceptance 3).

### Tests for User Story 4 (written FIRST, must FAIL) ⚠️

- [ ] T045 [P] [US4] Unit tests for `HookManager` and `GenerationContext` in `tests/unit/test_hooks.py` (registration order, chaining, unknown lifecycle point → `ValidationError`, hook exception → wrapped `GenerationError`, snapshot capture)
- [ ] T046 [P] [US4] Integration test for hooks in `tests/integration/test_pipeline.py` (register hook placing a marker entity after room placement → marker appears in final output)

### Implementation for User Story 4

- [ ] T047 [P] [US4] Implement `GenerationContext` dataclass in `src/gamemapgen/hooks.py` (`map_data`, `prng`, `params`, `snapshots`)
- [ ] T048 [P] [US4] Implement `HookManager` in `src/gamemapgen/hooks.py` (`register`, `unregister`, `run`, `list_hooks`; chainable hooks in registration order; snapshot capture at each lifecycle point per Principle IX)
- [ ] T049 [US4] Integrate `HookManager` into `BaseGenerator.generate` lifecycle in `src/gamemapgen/generators/base.py` (before_generation → after_room_placement → after_corridor_connection → post_process; snapshots populated per FR)
- [ ] T050 [US4] Add `register_hook` convenience method and expose `snapshots` on `BaseGenerator` in `src/gamemapgen/generators/base.py` (populated from `GenerationContext.snapshots` after generation)

**Checkpoint**: User Stories 1–4 all work independently.

---

## Phase 7: User Story 5 - Enforce Content Constraints (Priority: P3)

**Goal**: A game developer shipping to age-rated/moderation-gated platforms restricts generated content (banned tile/entity types, density limits, age-rating profiles) so worlds automatically comply. Violations trigger retry-with-adjustment up to `max_iterations`, else a clear `ConstraintViolationError` — never silent violations.

**Independent Test**: Declare a constraint (e.g., `BannedTileType(tile_types=["LAVA"])`) and assert the generated map contains zero violating content OR generation retries within `max_iterations` to satisfy it; if unsatisfiable, a clear `ConstraintViolationError` identifies the offending constraint and its parameters. Output metadata records that the constraint was enforced (spec US5 acceptance 3).

### Tests for User Story 5 (written FIRST, must FAIL) ⚠️

- [ ] T051 [P] [US5] Unit tests for content constraints in `tests/unit/test_constraints.py` (`BannedTileType`, `BannedEntityType`, `MaxDensity`, `AgeRatingProfile`; enforcement via retry-with-adjustment up to `max_iterations`; unresolved → `ConstraintViolationError` identifying offending constraint; metadata records enforcement)
- [ ] T052 [P] [US5] Integration test for constraints in `tests/integration/test_pipeline.py` (add `BannedTileType`, verify no banned tile appears; declare unsatisfiable constraint → clean `ConstraintViolationError`)

### Implementation for User Story 5

- [ ] T053 [P] [US5] Implement `ContentConstraint` base and concrete types (`BannedTileType`, `BannedEntityType`, `MaxDensity`, `AgeRatingProfile`) in `src/gamemapgen/constraints.py` per data-model.md §3
- [ ] T054 [P] [US5] Implement constraint enforcement engine in `src/gamemapgen/constraints.py` (validate generated `MapData` against constraints; retry-with-adjustment up to `max_iterations`; raise `ConstraintViolationError` if unresolved; record enforcement in metadata)
- [ ] T055 [US5] Integrate constraint enforcement into `BaseGenerator.generate` lifecycle in `src/gamemapgen/generators/base.py` (constraint check before finalize, retry loop bounded by `max_iterations` per FR-009)
- [ ] T056 [US5] Add `add_constraint` convenience method and `content_constraints` param threading on `BaseGenerator` in `src/gamemapgen/generators/base.py` and `src/gamemapgen/config.py`

**Checkpoint**: All 5 user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T057 [P] Create getting-started guide in `docs/getting-started.md` covering installation, generation pipeline, and hook system (Principle XIII, FR-015)
- [ ] T058 [P] Create runnable demo scripts in `docs/demos/` for each built-in generator (dungeon, open_world, maze) with example presets (Principle XIII)
- [ ] T059 [P] Create performance benchmark harness in `tests/benchmarks/bench_generation.py` verifying 100x100 grid <100ms (SC-001) and no regression >10% (SC-008)
- [ ] T060 [P] Add `@since`/`@deprecated` metadata annotations to all public types and functions in `src/gamemapgen/` (Principle XI)
- [ ] T061 [P] Add docstrings with at least one runnable usage example per public method in `src/gamemapgen/` (Principle XIII, SC-004)
- [ ] T062 [P] Add edge-case tests for empty maps, single-tile maps, max-size maps, extreme aspect ratios, boundary seeds (0 and 2^32-1), and iteration-budget exhaustion in `tests/unit/` (spec Edge Cases)
- [ ] T063 [P] Add serialization round-trip tests for custom/unknown tile and entity types via registry-aware deserialization in `tests/contract/test_serialization.py` (SC-005)
- [ ] T064 Run quickstart.md validation scenarios as tests in `tests/integration/test_quickstart.py` (all 6 scenarios from quickstart.md)
- [ ] T065 Run full test suite with coverage: `pytest tests/ -v --cov=gamemapgen --cov-report=term-missing` and verify ≥90% line coverage per generator module
- [ ] T066 Verify no external runtime dependencies beyond standard library (audit imports in `src/gamemapgen/`)
- [ ] T067 Verify no hardcoded magic numbers (all tunable values are parameters with defaults) across `src/gamemapgen/`

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
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Builds on US1's generators and `MapData.to_json` but is independently testable (determinism of the same generators)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses US1's generators as layers but is independently testable via `CompositeGenerator`
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Integrates into US1's `BaseGenerator.generate` lifecycle but is independently testable
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Integrates into US1's `BaseGenerator.generate` lifecycle but is independently testable

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
Task: "Unit tests for preset resolution in tests/unit/test_presets.py"
Task: "Contract test for serialization in tests/contract/test_serialization.py"

# Launch all models for User Story 1 together:
Task: "Implement models in src/gamemapgen/models.py"
Task: "Implement GenerationParams in src/gamemapgen/config.py"
Task: "Implement DungeonGenerator in src/gamemapgen/generators/dungeon.py"
Task: "Implement OpenWorldGenerator in src/gamemapgen/generators/open_world.py"
Task: "Implement MazeGenerator in src/gamemapgen/generators/maze.py"
```

## Parallel Example: User Story 4 (Hooks)

```bash
# Launch all tests for User Story 4 together:
Task: "Unit tests for HookManager in tests/unit/test_hooks.py"
Task: "Integration test for hooks in tests/integration/test_pipeline.py"

# Launch all implementation for User Story 4 together:
Task: "Implement GenerationContext in src/gamemapgen/hooks.py"
Task: "Implement HookManager in src/gamemapgen/hooks.py"
```

## Parallel Example: User Story 5 (Constraints)

```bash
# Launch all tests for User Story 5 together:
Task: "Unit tests for content constraints in tests/unit/test_constraints.py"
Task: "Integration test for constraints in tests/integration/test_pipeline.py"

# Launch all implementation for User Story 5 together:
Task: "Implement ContentConstraint types in src/gamemapgen/constraints.py"
Task: "Implement constraint enforcement engine in src/gamemapgen/constraints.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 - both are P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2 (determinism is a P1 non-negotiable requirement)
5. **STOP and VALIDATE**: Test US1 + US2 independently (preset generation, determinism, validation, serialization)
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently
3. Add User Story 2 → Test independently → Deploy/Demo (MVP!)
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (+2, both P1)
   - Developer B: User Story 3
   - Developer C: User Story 4
   - Developer D: User Story 5
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
- `to_ascii()`/snapshot debugging (Principle IX) is a cross-cutting concern: `to_ascii` is delivered in US1 (T023/T014), snapshots in US4 (T048/T049); no dedicated debug user story in the current spec
