# Contract: Data Structures (MapData, Tile, etc.)

**@since**: 1.0.0 | **Date**: 2026-08-05

All data structures are pure dataclasses, JSON-serializable without loss. Each implements `to_dict()` and `from_dict()`.

## `MapData`

```python
@dataclass
class MapData:
    grid: list[list[Tile]]          # grid[y][x]
    metadata: MapMetadata
    regions: list[Region] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    adjacency: AdjacencyGraph | None = None

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "MapData": ...
    def to_ascii(self) -> str:
        """ASCII representation using tile glyphs."""
    def to_json(self) -> str:
        """JSON string (lossless round-trip)."""
```

### Usage Example

```python
from gamemapgen import MapData

json_str = map_data.to_json()
restored = MapData.from_dict(json.loads(json_str))
assert restored == map_data  # lossless
```

---

## `Tile`

```python
@dataclass
class Tile:
    type: str                       # registered tile type, e.g. "WALL"
    position: Position
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "Tile": ...
```

---

## `Position`

```python
@dataclass(frozen=True)
class Position:
    x: int
    y: int
```

---

## `MapMetadata`

```python
@dataclass
class MapMetadata:
    parameters: dict                # resolved generation params
    seed: int                       # 32-bit unsigned seed
    generator_version: str          # SemVer
    timestamp: str                  # ISO 8601
    generator_name: str
    incomplete: bool = False        # True if partial result
```

---

## `Region`

```python
@dataclass
class Region:
    name: str
    bounds: Rect
    properties: dict = field(default_factory=dict)
```

---

## `Rect`

```python
@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int
```

---

## `Entity`

```python
@dataclass
class Entity:
    type: str
    position: Position
    properties: dict = field(default_factory=dict)
```

---

## `Layer`

```python
@dataclass
class Layer:
    name: str
    grid: list[list[Tile]]
    metadata: dict = field(default_factory=dict)
```

---

## `AdjacencyGraph`

```python
@dataclass
class AdjacencyGraph:
    nodes: list[Position]
    edges: list[Edge]
```

---

## `Edge`

```python
@dataclass
class Edge:
    from_pos: Position
    to_pos: Position
    weight: float = 1.0
```

---

## Serialization Guarantee

Every structure round-trips losslessly:

```
MapData → to_json() → str → json.loads → from_dict() → MapData (identical)
```

- `metadata.timestamp` preserved as ISO 8601 string.
- `metadata.parameters` preserved exactly.
- Nested structures all round-trip.
