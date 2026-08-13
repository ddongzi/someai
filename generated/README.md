# GameMapGen

A framework-agnostic, procedural **game map generation** library in Python. It generates deterministic, seed-driven map data (tile grids, regions, entities, layers, adjacency graphs) as pure, JSON-serializable data structures.

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

```python
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
gen = registry.create("dungeon", seed=42, width=50, height=50)

map_data = gen.generate()
print(map_data.to_ascii())
```

## Project Layout

```text
src/gamemapgen/          # Library source package
tests/                   # unit / integration / contract / benchmarks
specs/game-map-generator # Feature specs, plan, data model, quickstart
```

## Documentation

- [Quickstart](./specs/game-map-generator/quickstart.md) — runnable validation scenarios
- [Plan](./specs/game-map-generator/plan.md) — implementation plan and architecture
- [Data Model](./specs/game-map-generator/data-model.md) — entity definitions and validation rules

## License

See repository for license details.
