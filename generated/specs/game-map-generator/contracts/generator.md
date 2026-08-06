# Contract: Generator Interface & Registry

**@since**: 1.0.0 | **Date**: 2026-08-05

## `BaseGenerator` (abstract)

The abstract base class every generator implements. All generators are self-contained, independently testable modules.

```python
class BaseGenerator(ABC):
    name: str                      # unique generator name, e.g. "dungeon"
    version: str                   # SemVer of this generator, e.g. "1.0.0"

    @abstractmethod
    def generate(self, params: GenerationParams) -> MapData:
        """Generate a map from validated params.

        Args:
            params: Resolved and validated generation parameters.

        Returns:
            MapData: Complete, valid map data.

        Raises:
            ValidationError: If params are invalid (should not happen if
                validated via `validate_params` first).
            ConstraintViolationError: If content constraints cannot be
                satisfied within the iteration budget.
            GenerationError: If generation fails partway through.
        """

    @abstractmethod
    def validate_params(self, params: GenerationParams) -> None:
        """Validate params before generation.

        Raises:
            ValidationError: With a clear, actionable message identifying
                the invalid parameter and its valid range/values.
        """

    @abstractmethod
    def complexity_estimate(self, params: GenerationParams) -> ComplexityEstimate:
        """Return expected time/space cost before generation begins.

        Returns:
            ComplexityEstimate: {time: str, space: str, expected_ms: float}
        """

    def to_ascii(self, map_data: MapData) -> str:
        """Return a human-readable ASCII representation of the map.

        No external rendering dependency. Used for debugging and tests.
        """
```

### Usage Example

```python
from gamemapgen import GeneratorRegistry, GenerationParams

registry = GeneratorRegistry()
dungeon = registry.create("dungeon", seed=42, width=50, height=50)
map_data = dungeon.generate()
print(dungeon.to_ascii(map_data))
```

---

## `GeneratorRegistry`

Central registry for generator discovery and composition.

```python
class GeneratorRegistry:
    def register(self, generator_cls: type[BaseGenerator]) -> None:
        """Register a generator class by its `name` attribute.

        Raises:
            ValidationError: If a generator with the same name is already
                registered, or the class is not a BaseGenerator subclass.
        """

    def get(self, name: str) -> type[BaseGenerator]:
        """Get a registered generator class by name.

        Raises:
            GeneratorNotFoundError: If no generator with `name` is registered.
        """

    def list(self) -> list[str]:
        """List all registered generator names."""

    def create(self, name: str, **params) -> BaseGenerator:
        """Create a generator instance with the given params.

        Args:
            name: Registered generator name.
            **params: Generation parameters (seed, width, height, etc.).

        Returns:
            BaseGenerator: A configured generator instance.

        Raises:
            GeneratorNotFoundError: If `name` is not registered.
            ValidationError: If params are invalid.
        """
```

### Usage Example

```python
from gamemapgen import GeneratorRegistry

registry = GeneratorRegistry()
print(registry.list())  # ['dungeon', 'open_world', 'maze']

gen = registry.create("maze", seed=7, width=21, height=21)
map_data = gen.generate()
```

---

## `ComplexityEstimate`

```python
@dataclass
class ComplexityEstimate:
    time: str        # Big-O time, e.g. "O(n log n)"
    space: str       # Big-O space, e.g. "O(n)"
    expected_ms: float  # estimated generation time in ms
```
