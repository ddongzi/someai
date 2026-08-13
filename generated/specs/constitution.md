# GameMapGen Constitution
<!-- Game Map Generation Component Constitution -->

## Project Overview

**GameMapGen** is a framework-agnostic, procedural game map generation component. It provides game developers with a reliable, deterministic, and extensible toolkit for generating diverse map types (dungeons, open worlds, mazes, etc.) as pure data, decoupled from any specific game engine or rendering stack.

**Vision**: To be the de-facto standard procedural map generation library for game developers, enabling anyone to create rich, varied, and reproducible game worlds with minimal effort.

**Target Users**:
- Indie game developers seeking quick, high-quality procedural content
- AAA studios needing deterministic, scalable generation pipelines
- Tooling/editor developers building map editors or level design tools
- Researchers prototyping procedural content algorithms

## Project Purpose & Scope

**GameMapGen** is a framework-agnostic, procedural game map generation component. Its purpose is to provide game developers with a reliable, deterministic, and extensible toolkit for generating diverse map types (dungeons, open worlds, mazes, etc.) as pure data, decoupled from any specific game engine or rendering stack.

**In Scope:**
- Procedural generation of map data (tile grids, regions, entities, layers, adjacency graphs)
- Deterministic, seed-based generation for reproducibility
- Configurable generation pipeline (presets, overrides, defaults)
- Generator composition and layering
- Validation, performance budgeting, and content constraints

**Out of Scope:**
- Rendering, drawing, or visualization of maps
- Game engine integration (Unity, Godot, etc.) — consumers handle this
- Networking, persistence, or save-game systems
- AI/pathfinding logic (only adjacency data is provided)

## Core Principles

### I. Modular Generator Architecture
Each map generator (dungeon, open-world, maze, etc.) MUST be implemented as a self-contained, independently testable module. Generators MUST NOT share mutable state; they communicate only through well-defined input/output contracts (generation parameters → map data). Each generator MUST be registered via a central `GeneratorRegistry` to enable discovery and composition. Rationale: Enables plug-and-play addition of new map types without modifying existing generators, and allows runtime discovery of available generators.

### II. Deterministic Generation with Seeding
All map generation MUST be deterministic given the same seed and parameters. Every generator MUST accept a `seed` parameter (integer, 32-bit unsigned). The same seed MUST always produce the identical map output. Generators MUST use a seeded pseudo-random number generator (PRNG) passed explicitly, not global `Math.random()` or equivalent. Rationale: Essential for reproducibility in game development (shared seeds, debugging, replays, networked sessions).

### III. Configurable Generation Pipeline
The generation pipeline MUST support a layered configuration model:
- **Presets**: Pre-defined named configurations (e.g., "small_dungeon", "epic_world")
- **Overrides**: User-supplied parameters that override preset values
- **Defaults**: Sensible fallback values for all parameters

All configuration parameters MUST be typed (with validation rules) and MUST have documentation strings. Rationale: Balances ease-of-use with flexibility for advanced users, and enables tooling (e.g., auto-generated config UIs).

### IV. Pure Data Output (No Rendering)
Generators MUST output pure data structures (e.g., tile grids, room/entity lists, adjacency graphs) and MUST NOT perform any rendering, drawing, or visualization. Rendering is the responsibility of downstream consumers. The output data MUST be serializable to JSON without loss of information. Rationale: Keeps the component framework-agnostic (works with Unity, Godot, custom engines, or CLI debug output) and enables easy debugging, saving, and network transmission.

### V. Validation-First (NON-NEGOTIABLE)
All generation parameters MUST be validated before generation begins. Invalid parameters MUST produce clear, actionable error messages specifying which parameter is invalid and what the valid range/values are. Validation MUST include:
- Type checks (e.g., integer vs string)
- Range checks (e.g., width between 10 and 1000)
- Consistency checks (e.g., room count must not exceed grid area)
- Dependency checks (e.g., if `use_corridors=true`, `corridor_width` must be ≥1)

Rationale: Prevents silent failures or corrupted map data that would be difficult to debug downstream.

### VI. Performance Budget & Scalability
Each generator MUST document its time/space complexity using Big-O notation. Generation for a "standard" map (e.g., 100x100 grid) MUST complete within 100ms on reference hardware. Generators MUST support a `max_iterations` or `timeout_ms` parameter to prevent infinite loops. Generators SHOULD provide a `complexity_estimate(params)` method that returns expected time/space cost before generation begins. Rationale: Game developers need predictable generation times for runtime/procedural content and need to make informed trade-offs.

### VII. Extensibility via Hooks/Events
Generators MUST expose lifecycle hooks (e.g., `before_generation`, `after_room_placement`, `post_process`) that allow consumers to inject custom logic without modifying generator code. Hooks MUST follow a consistent signature: `hook(context: GenerationContext) → GenerationContext`. Multiple hooks of the same type MUST be chainable. Rationale: Enables game-specific customization (e.g., placing quest items, applying biome rules, adding decorative elements) while keeping the core generator clean and reusable.

### VIII. Composition & Layering
Generators MUST support composition via a `CompositeGenerator` that can layer multiple generators (e.g., base terrain → road network → building placement → detail decoration). Each layer MUST receive the output of the previous layer as input. Layer ordering MUST be explicit and documented. Rationale: Realistic game maps require multiple generation passes; composition enables complex maps from simple building blocks.

### IX. Debug & Visualization Support
Generators MUST include a `to_ascii()` or `debug_render()` method that outputs a human-readable string representation of the generated map. This method MUST NOT depend on any external rendering library. Generators SHOULD also expose intermediate state snapshots at each hook point for debugging. Rationale: Essential for development debugging, unit test assertions, and CI pipeline validation without a full game engine.

### X. Content Safety & Constraints
Generators MUST support a `content_constraints` parameter that allows consumers to restrict generated content (e.g., banned tile types, forbidden entity types, maximum violence/decoration density, age-rating profiles). When a constraint is violated during generation, the generator MUST either (a) retry with adjusted parameters up to `max_iterations`, or (b) fail with a clear, actionable error identifying the offending constraint. Generators MUST NOT silently produce content that violates an explicitly declared constraint. Rationale: Game maps may be used in age-rated or moderated environments; enforcing constraints at generation time prevents costly manual curation and protects brand/legal compliance.

### XI. API Stability & Semantic Versioning
The public API (generator interfaces, `MapData`/`Tile` structures, configuration schema, and hook signatures) MUST follow Semantic Versioning (MAJOR.MINOR.PATCH). Breaking changes to any public interface MUST only occur in a MAJOR version bump and MUST be accompanied by a documented migration guide. Deprecated APIs MUST be marked and retained for at least one MINOR release before removal. All public types and functions MUST be annotated with `@since` (introduced version) and `@deprecated` (if applicable) metadata. Rationale: GameMapGen is a library consumed by external game projects; predictable API evolution prevents breaking downstream builds and enables teams to plan upgrades safely.

### XII. Error Handling & Graceful Degradation
Generators MUST handle mid-generation failures gracefully. If generation fails partway through, the generator MUST either (a) roll back to a valid, consistent state and return a clear error, or (b) return a partial result explicitly flagged as `incomplete` in the output metadata. Generators MUST NEVER return a `MapData` object that appears valid but contains partially-initialized or inconsistent data (e.g., a grid with missing rows, or regions referencing out-of-bounds tiles). All errors MUST be typed and catchable (e.g., `GenerationError`, `ValidationError`, `ConstraintViolationError`). Rationale: In a live game, a failed generation must not corrupt the game state or crash silently; predictable, typed failures enable consumers to implement retry, fallback, or user-facing error messaging.

### XIII. Documentation & Developer Experience
All public APIs MUST be documented with at least one runnable usage example per method. The component MUST ship with a getting-started guide covering installation, the generation pipeline, and the hook system. Each built-in generator MUST include a documented example preset and a runnable demo. Documentation MUST be kept in sync with code via automated doc-generation checks in CI. Rationale: A well-documented component reduces onboarding time, encourages correct usage, and lowers the support burden — critical for a library meant to be adopted across many game projects.

## Output Contract

### MapData Structure
Every generator MUST output a `MapData` object containing:
- `grid`: 2D array of `Tile` objects (each with `type`, `position(x,y)`, `metadata: dict`)
- `metadata`: Generation parameters used, seed, generator version, timestamp (ISO 8601)
- `regions`: Optional list of named regions/zones with bounds (rect or polygon)
- `entities`: Optional list of placed entities (spawn points, items, NPCs, etc.) with `type`, `position`, `properties`
- `layers`: Optional ordered list of sub-maps for multi-layer maps (e.g., terrain layer, object layer, fog-of-war layer)
- `adjacency`: Optional graph representation (nodes + edges) for pathfinding or connectivity queries

### Tile Structure
Each `Tile` MUST contain:
- `type`: One of the supported tile types (string enum)
- `position`: `{x: int, y: int}`
- `metadata`: Dictionary for extensible properties (e.g., `{"elevation": 0.5, "biome": "forest", "temperature": 25}`)

### Supported Tile Types (extensible via registry)
- `WALL`, `FLOOR`, `WATER`, `LAVA`, `DOOR`, `STAIRS`, `EMPTY`, `GRASS`, `ROAD`, `BRIDGE`, `TRAP`

## Development Workflow

### Test Coverage Requirements
- **Unit tests**: REQUIRED for every generator module (≥90% line coverage)
- **Determinism tests**: Every generator MUST have tests proving same seed → same output (run with at least 5 different seeds)
- **Edge case tests**: Empty maps, single-tile maps, max-size maps, invalid parameters, extreme aspect ratios
- **Performance benchmarks**: MUST be included and run as part of CI; regression MUST fail the build
- **Serialization round-trip tests**: MapData → JSON → MapData MUST preserve all data

### Quality Gates
1. All tests pass (unit + determinism + edge cases + serialization)
2. Performance benchmarks within documented budget (no regression >10%)
3. No hardcoded magic numbers (all tunable values MUST be parameters with defaults)
4. Public API fully documented with at least one usage example per method
5. Type hints/annotations REQUIRED for all public interfaces
6. No external runtime dependencies beyond standard library (dev/test dependencies allowed)

## Terminology & Glossary

| Term | Definition |
|------|-----------|
| **Generator** | A self-contained module that produces a `MapData` output from typed parameters and a seed. |
| **Preset** | A named, pre-defined configuration bundle (e.g., `"small_dungeon"`). |
| **Override** | User-supplied parameters that take precedence over preset values. |
| **Seed** | A 32-bit unsigned integer that deterministically drives all randomness in generation. |
| **PRNG** | Pseudo-Random Number Generator; must be seeded and passed explicitly. |
| **Hook** | A lifecycle callback point where consumers can inject custom logic. |
| **Layer** | A single generation pass within a `CompositeGenerator`; layers compose sequentially. |
| **MapData** | The canonical pure-data output structure of any generator. |
| **Tile** | The atomic cell of a map grid; has a type, position, and metadata. |
| **CompositeGenerator** | A generator that layers multiple sub-generators in a defined order. |
| **Content Constraint** | A rule restricting generated content (tile types, entities, density, age-rating). |

## Governance

This constitution supersedes all ad-hoc development practices. Amendments require documented rationale, team approval, and a migration plan for existing generators. All PRs MUST verify compliance with these principles via automated linting/checks.

### Amendment Process
1. **Proposal**: Any contributor drafts a proposed amendment with clear rationale and impact analysis.
2. **Review**: The amendment is reviewed by maintainers for consistency with existing principles and scope.
3. **Approval**: Requires majority approval from maintainers; breaking changes require unanimous consent.
4. **Migration**: A migration plan MUST accompany any amendment that changes public APIs or output contracts.
5. **Recording**: Approved amendments update `CONSTITUTION_VERSION` (MAJOR for breaking, MINOR for additive, PATCH for clarifications) and `LAST_AMENDED_DATE`.

### Compliance Enforcement
- Automated linting/checks in CI MUST verify that all generators conform to the principles herein.
- New generators MUST pass a constitution-compliance review before merge.
- Violations MUST be fixed or explicitly waived (with documented rationale) before release.

**Version**: 2.7.0 | **Ratified**: 2025-07-16 | **Last Amended**: 2026-08-01
