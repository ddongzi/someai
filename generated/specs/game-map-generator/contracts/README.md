# Public API Contracts: Game Map Generation Component

**Phase 1 Output** | **Date**: 2026-08-05 | **Branch**: `game-map-generator`

This directory defines the public interface contracts for GameMapGen. As a Python library, the contracts are the public API surface exposed to consumers. Each contract documents the signature, types, behavior, and error semantics.

## Contract Files

| File | Contract |
|------|----------|
| [generator.md](./generator.md) | `BaseGenerator` abstract interface + `GeneratorRegistry` |
| [models.md](./models.md) | `MapData`, `Tile`, `Region`, `Entity`, `Layer`, `AdjacencyGraph` |
| [config.md](./config.md) | `GenerationParams`, `Preset`, `Override`, config resolution |
| [hooks.md](./hooks.md) | `HookManager`, `GenerationContext`, lifecycle points |
| [constraints.md](./constraints.md) | `ContentConstraint` types + enforcement |
| [errors.md](./errors.md) | Typed exception hierarchy |
| [prng.md](./prng.md) | `PRNG` seeded random interface |
| [tiles.md](./tiles.md) | `TileTypeRegistry` + built-in tile types |

## Versioning

All public APIs follow Semantic Versioning (MAJOR.MINOR.PATCH). Breaking changes only in MAJOR bumps with a migration guide. Public types/functions annotated with `@since` and `@deprecated` metadata.

## Stability Guarantees

- All public signatures are stable within a MAJOR version.
- Deprecated APIs retained for at least one MINOR release before removal.
- All public methods documented with at least one runnable usage example.
