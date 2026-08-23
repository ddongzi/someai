"""Unit tests for ``TileTypeRegistry``.

Covers: register / get / is_registered / list / glyph, as well as
validation failures (duplicate registration and unknown type lookups must
raise ``ValidationError``).
"""

import pytest

from gamemapgen import TileType, TileTypeRegistry, ValidationError


# Built-in tile types from the tiles.md contract.
BUILTIN_TILES = {
    "WALL": "#",
    "FLOOR": ".",
    "WATER": "~",
    "LAVA": "^",
    "DOOR": "D",
    "STAIRS": ">",
    "EMPTY": " ",
    "GRASS": ",",
    "ROAD": "=",
    "BRIDGE": "B",
    "TRAP": "x",
}


@pytest.fixture
def registry():
    """A fresh ``TileTypeRegistry`` pre-loaded with built-in tile types."""
    return TileTypeRegistry()


class TestTileTypeRegistryBuiltins:
    def test_all_builtin_types_are_registered(self, registry):
        for name in BUILTIN_TILES:
            assert registry.is_registered(name)

    def test_list_contains_all_builtin_types(self, registry):
        names = registry.list()
        for name in BUILTIN_TILES:
            assert name in names

    def test_builtin_glyphs(self, registry):
        for name, glyph in BUILTIN_TILES.items():
            assert registry.glyph(name) == glyph

    def test_builtin_tile_get(self, registry):
        tile = registry.get("WALL")
        assert tile.name == "WALL"
        assert tile.glyph == "#"


class TestTileTypeRegistryRegister:
    def test_register_and_get(self, registry):
        registry.register("ICE", glyph="i", description="Slippery ice")
        tile = registry.get("ICE")
        assert isinstance(tile, TileType)
        assert tile.name == "ICE"
        assert tile.glyph == "i"
        assert tile.description == "Slippery ice"

    def test_register_default_description(self, registry):
        registry.register("PORTAL", glyph="O")
        tile = registry.get("PORTAL")
        assert tile.name == "PORTAL"
        assert tile.glyph == "O"
        assert tile.description == ""

    def test_register_makes_registered(self, registry):
        assert not registry.is_registered("ICE")
        registry.register("ICE", glyph="i")
        assert registry.is_registered("ICE")

    def test_register_appears_in_list(self, registry):
        registry.register("ICE", glyph="i")
        assert "ICE" in registry.list()

    def test_duplicate_registration_raises(self, registry):
        registry.register("ICE", glyph="i")
        with pytest.raises(ValidationError):
            registry.register("ICE", glyph="I")

    def test_duplicate_builtin_registration_raises(self, registry):
        with pytest.raises(ValidationError):
            registry.register("WALL", glyph="#")


class TestTileTypeRegistryGet:
    def test_get_returns_frozen_tile_type(self, registry):
        registry.register("ICE", glyph="i", description="Slippery ice")
        tile = registry.get("ICE")
        with pytest.raises(AttributeError):
            tile.name = "OTHER"
        with pytest.raises(AttributeError):
            tile.glyph = "x"
        with pytest.raises(AttributeError):
            tile.description = "Changed"

    def test_get_unknown_raises(self, registry):
        with pytest.raises(ValidationError):
            registry.get("UNKNOWN")

    def test_get_unknown_after_unregistered_raises(self, registry):
        assert not registry.is_registered("ICE")
        with pytest.raises(ValidationError):
            registry.get("ICE")


class TestTileTypeRegistryIsRegistered:
    def test_unknown_not_registered(self, registry):
        assert not registry.is_registered("UNKNOWN")

    def test_registered(self, registry):
        registry.register("ICE", glyph="i")
        assert registry.is_registered("ICE")

    def test_does_not_raise_for_unknown(self, registry):
        # is_registered is a query, not a lookup; it must not raise.
        assert registry.is_registered("UNKNOWN") is False


class TestTileTypeRegistryList:
    def test_list_returns_names(self, registry):
        names = registry.list()
        assert isinstance(names, list)
        for name in names:
            assert isinstance(name, str)

    def test_list_includes_custom_after_register(self, registry):
        registry.register("ICE", glyph="i")
        assert "ICE" in registry.list()

    def test_list_no_duplicates(self, registry):
        names = registry.list()
        assert len(names) == len(set(names))


class TestTileTypeRegistryGlyph:
    def test_glyph_custom(self, registry):
        registry.register("ICE", glyph="i")
        assert registry.glyph("ICE") == "i"

    def test_glyph_builtin(self, registry):
        assert registry.glyph("FLOOR") == "."

    def test_glyph_unknown_raises(self, registry):
        with pytest.raises(ValidationError):
            registry.glyph("UNKNOWN")


class TestTileTypeRegistryValidation:
    def test_register_empty_name_raises(self, registry):
        with pytest.raises(ValidationError):
            registry.register("", glyph="#")

    def test_get_empty_name_raises(self, registry):
        with pytest.raises(ValidationError):
            registry.get("")
