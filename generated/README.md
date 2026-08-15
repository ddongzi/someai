# GameMapGen

A framework-agnostic, procedural **game map generation** library in Python. It generates deterministic, seed-driven map data (tile grids, regions, entities, layers, adjacency graphs) as pure, JSON-serializable data structures.

Built on top of the legacy `SeedManager` (GridRandom / RoomSplit / RecursiveBacktrack / PerlinNoise), GameMapGen refactors and extends it into a constitution-compliant, modular library — no rendering, no runtime dependencies, fully serializable.

## Features

- **Multiple modular generators** — dungeon, open-world, maze
- **Deterministic generation** — identical seed + parameters always produce identical output
- **Configurable pipeline** — layered configuration (presets → overrides → defaults)
- **Generator composition** — `CompositeGenerator` for layering generators
- **Lifecycle hooks** — chainable hooks for custom logic injection
- **Content constraints** — safety/compliance enforcement (e.g., banned tile types)
- **Pure data output** — no rendering, fully JSON-serializable
- **No external runtime dependencies** — Python standard library only
- **Typed errors** — clear, typed error classes
- **Debug support** — ASCII visualization and intermediate snapshots

## Requirements

- **Python 3.11+**
- **Runtime**: standard library only
- **Dev**: `pytest`, `pytest-cov`

```bash
pip install pytest pytest-cov
```

## Quick Start

Generate a dungeon map in a few lines:

```python
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
gen = registry.create("dungeon", seed=42, width=50, height=50)

map_data = gen.generate()
print(map_data.to_ascii())
```

> 🔗 **Quick-Start Pointer**: for a step-by-step, runnable walkthrough with validation scenarios covering all public APIs (registry, config, hooks, constraints, serialization), see
> [**Quickstart Guide → `specs/game-map-generator/quickstart.md`**](./specs/game-map-generator/quickstart.md)

## Project Layout

```text
src/gamemapgen/          # Library source package
tests/                   # unit / integration / contract / benchmarks
specs/game-map-generator # Feature specs, plan, data model, quickstart
```

## Documentation

- [Quickstart](./specs/game-map-generator/quickstart.md) — runnable validation scenarios & getting-started pointer
- [Plan](./specs/game-map-generator/plan.md) — implementation plan and architecture
- [Data Model](./specs/game-map-generator/data-model.md) — entity definitions and validation rules
- [Spec](./specs/game-map-generator/spec.md) — feature specification and user stories

## License

See repository for license details.
