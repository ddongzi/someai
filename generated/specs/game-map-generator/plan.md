# Implementation Plan: Game Map Generation Component

**Branch**: `game-map-generator` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/game-map-generator/spec.md`

## Summary

Build **GameMapGen**, a framework-agnostic, procedural game map generation library in Python. The component generates deterministic, seed-driven map data (tile grids, regions, entities, layers, adjacency graphs) as pure, JSON-serializable data structures. It supports multiple modular generators (dungeon, open-world, maze), a layered configuration pipeline (presets → overrides → defaults), generator composition via a `CompositeGenerator`, lifecycle hooks for custom logic injection, and content constraints for safety/compliance. The library has no external runtime dependencies, exposes typed errors, and ships with a getting-started guide, example presets, and runnable demos.

The existing `app/seed_manager.py` provides a legacy `SeedManager` with basic algorithms (GridRandom, RoomSplit, RecursiveBacktrack, PerlinNoise) and seed management. This feature refactors and extends that foundation into a constitution-compliant, modular library.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase is Python; standard library only)

**Primary Dependencies**: Standard library only (`random`, `json`, `dataclasses`, `typing`, `abc`, `time`). Dev/test: `pytest`, `pytest-cov`.

**Storage**: N/A (pure in-memory data structures; JSON serialization for persistence)

**Testing**: `pytest` with `pytest-cov` (≥90% line coverage per generator), determinism tests (≥5 seeds), edge-case tests, serialization round-trip tests, performance benchmarks.

**Target Platform**: Cross-platform library (framework-agnostic; no game engine coupling)

**Project Type**: Library (Python package)

**Performance Goals**: Standard 100x100 grid generated in <100ms on reference hardware (SC-001); no regression >10% in benchmarks (SC-008).

**Constraints**: No external runtime dependencies; output JSON-serializable without loss; deterministic given seed+params; validation-first; typed errors; Semantic Versioning.

**Scale/Scope**: Multiple built-in generators (dungeon, open-world, maze), composite layering, hook system, content constraints, presets/overrides.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate (Constitution Principle) | Status |
|---|-------------------------------|--------|
| I | Modular Generator Architecture (registry, self-contained modules) | ✅ PASS |
| II | Deterministic Generation with Seeding (seeded PRNG passed explicitly) | ✅ PASS |
| III | Configurable Generation Pipeline (presets/overrides/defaults) | ✅ PASS |
| IV | Pure Data Output (no rendering, JSON serializable) | ✅ PASS |
| V | Validation-First (NON-NEGOTIABLE) | ✅ PASS |
| VI | Performance Budget & Scalability (Big-O, max_iterations, complexity_estimate) | ✅ PASS |
| VII | Extensibility via Hooks (chainable lifecycle hooks) | ✅ PASS |
| VIII | Composition & Layering (CompositeGenerator) | ✅ PASS |
| IX | Debug & Visualization Support (to_ascii/debug_render) | ✅ PASS |
| X | Content Safety & Constraints (content_constraints) | ✅ PASS |
| XI | API Stability & Semantic Versioning | ✅ PASS |
| XII | Error Handling & Graceful Degradation (typed errors) | ✅ PASS |
| XIII | Documentation & Developer Experience | ✅ PASS |

All gates pass. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/game-map-generator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by this command)
```

### Source Code (repository root)

```text
src/gamemapgen/
├── __init__.py          # Public API exports, version
├── errors.py            # Typed errors (GenerationError, ValidationError, ConstraintViolationError)
├── prng.py              # Seeded PRNG wrapper (explicitly passed)
├── models.py            # MapData, Tile, Region, Entity, AdjacencyGraph, Layer
├── registry.py          # GeneratorRegistry, TileTypeRegistry
├── config.py            # Preset, Override, layered config resolution + validation
├── constraints.py       # ContentConstraint definitions + enforcement
├── hooks.py             # Hook system (lifecycle points, chaining)
├── composite.py         # CompositeGenerator (layering)
├── generators/
│   ├── __init__.py
│   ├── base.py          # BaseGenerator abstract class
│   ├── dungeon.py       # DungeonGenerator
│   ├── open_world.py    # OpenWorldGenerator
│   └── maze.py          # MazeGenerator
└── presets.py           # Built-in presets (small_dungeon, epic_world, etc.)

tests/
├── conftest.py
├── unit/
│   ├── test_models.py
│   ├── test_registry.py
│   ├── test_config.py
│   ├── test_constraints.py
│   ├── test_hooks.py
│   ├── test_composite.py
│   ├── test_prng.py
│   └── generators/
│       ├── test_dungeon.py
│       ├── test_open_world.py
│       └── test_maze.py
├── integration/
│   └── test_pipeline.py
├── contract/
│   └── test_serialization.py
└── benchmarks/
    └── bench_generation.py
```

**Structure Decision**: Single Python library package under `src/gamemapgen/` with a flat public API surface (models, errors, registry, config, hooks, composite) and a `generators/` subpackage for modular generator modules. Tests are organized by unit/integration/contract/benchmark layers. This structure directly maps to the constitution's modular architecture and the spec's requirement for self-contained, independently testable generator modules.

## Complexity Tracking

> No constitution violations to justify. All gates pass.
