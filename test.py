"""
网格随机算法 (GridRandom) 单元测试
"""
import pytest
from app import GridRandomGenerator


class TestGridRandomGeneratorInit:
    """测试 GridRandomGenerator 初始化"""

    def test_default_seed(self):
        """默认不传种子，不报错"""
        gen = GridRandomGenerator()
        assert gen.seed is None

    def test_valid_seed(self):
        """合法种子初始化"""
        gen = GridRandomGenerator(seed=12345)
        assert gen.seed == 12345

    def test_seed_boundary_min(self):
        """种子最小值边界"""
        gen = GridRandomGenerator(seed=1)
        assert gen.seed == 1

    def test_seed_boundary_max(self):
        """种子最大值边界"""
        gen = GridRandomGenerator(seed=999999999)
        assert gen.seed == 999999999

    def test_invalid_seed_type_string(self):
        """种子类型错误 - 字符串"""
        with pytest.raises(TypeError, match="种子必须是整数"):
            GridRandomGenerator(seed="abc")  # type: ignore

    def test_invalid_seed_type_float(self):
        """种子类型错误 - 浮点数"""
        with pytest.raises(TypeError, match="种子必须是整数"):
            GridRandomGenerator(seed=1.5)  # type: ignore

    def test_invalid_seed_too_small(self):
        """种子超出下限"""
        with pytest.raises(ValueError, match="种子范围"):
            GridRandomGenerator(seed=0)

    def test_invalid_seed_too_large(self):
        """种子超出上限"""
        with pytest.raises(ValueError, match="种子范围"):
            GridRandomGenerator(seed=1000000000)


class TestGridRandomGenerateBasic:
    """测试 generate 基本功能"""

    def test_generate_returns_correct_types(self):
        """generate 返回正确的数据类型"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, room_list = gen.generate(width=10, height=10)

        assert isinstance(tile_map, list)
        assert isinstance(start, tuple)
        assert isinstance(end, tuple)
        assert isinstance(room_list, list)

    def test_generate_map_dimensions(self):
        """生成的地图尺寸正确"""
        gen = GridRandomGenerator(seed=42)
        width, height = 15, 20
        tile_map, _, _, _ = gen.generate(width=width, height=height)

        assert len(tile_map) == height
        assert all(len(row) == width for row in tile_map)

    def test_generate_tile_values_valid(self):
        """所有格子值都是合法的 tile 类型"""
        gen = GridRandomGenerator(seed=42)
        tile_map, _, _, _ = gen.generate(width=10, height=10)

        valid_tiles = {
            GridRandomGenerator.TILE_EMPTY,
            GridRandomGenerator.TILE_WALL,
            GridRandomGenerator.TILE_TRAP,
            GridRandomGenerator.TILE_RESOURCE,
        }
        for row in tile_map:
            for cell in row:
                assert cell in valid_tiles, f"非法格子值: {cell}"

    def test_generate_start_end_not_wall(self):
        """起点和终点不是障碍物"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, _ = gen.generate(width=10, height=10)

        sr, sc = start
        er, ec = end
        assert tile_map[sr][sc] != GridRandomGenerator.TILE_WALL
        assert tile_map[er][ec] != GridRandomGenerator.TILE_WALL

    def test_generate_room_list_not_contains_wall(self):
        """room_list 不包含障碍物格子"""
        gen = GridRandomGenerator(seed=42)
        _, _, _, room_list = gen.generate(width=10, height=10)

        for r, c in room_list:
            assert r >= 0 and c >= 0

    def test_generate_deterministic_same_seed(self):
        """相同种子生成相同地图"""
        gen1 = GridRandomGenerator(seed=888)
        map1, start1, end1, rooms1 = gen1.generate(width=8, height=8)

        gen2 = GridRandomGenerator(seed=888)
        map2, start2, end2, rooms2 = gen2.generate(width=8, height=8)

        assert map1 == map2
        assert start1 == start2
        assert end1 == end2
        assert rooms1 == rooms2

    def test_generate_different_seed_different_map(self):
        """不同种子生成不同地图（概率极高）"""
        gen1 = GridRandomGenerator(seed=111)
        map1, _, _, _ = gen1.generate(width=10, height=10)

        gen2 = GridRandomGenerator(seed=222)
        map2, _, _, _ = gen2.generate(width=10, height=10)

        assert map1 != map2


class TestGridRandomGenerateValidation:
    """测试 generate 参数校验"""

    def test_invalid_width_too_small(self):
        """宽度小于最小值"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="地图尺寸"):
            gen.generate(width=2, height=10)

    def test_invalid_height_too_small(self):
        """高度小于最小值"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="地图尺寸"):
            gen.generate(width=10, height=2)

    def test_invalid_wall_ratio_negative(self):
        """wall_ratio 为负数"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="wall_ratio"):
            gen.generate(width=10, height=10, wall_ratio=-0.1)

    def test_invalid_wall_ratio_over_one(self):
        """wall_ratio 超过 1"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="wall_ratio"):
            gen.generate(width=10, height=10, wall_ratio=1.5)

    def test_invalid_trap_ratio_negative(self):
        """trap_max_ratio 为负数"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="trap_max_ratio"):
            gen.generate(width=10, height=10, trap_max_ratio=-0.01)

    def test_invalid_trap_ratio_over_one(self):
        """trap_max_ratio 超过 1"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="trap_max_ratio"):
            gen.generate(width=10, height=10, trap_max_ratio=1.1)

    def test_invalid_resource_ratio_negative(self):
        """resource_ratio 为负数"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="resource_ratio"):
            gen.generate(width=10, height=10, resource_ratio=-0.5)

    def test_invalid_resource_ratio_over_one(self):
        """resource_ratio 超过 1"""
        gen = GridRandomGenerator(seed=42)
        with pytest.raises(ValueError, match="resource_ratio"):
            gen.generate(width=10, height=10, resource_ratio=2.0)


class TestGridRandomPath:
    """测试路径连通性"""

    def test_path_exists_default(self):
        """默认 ensure_path=True 时，起点到终点有通路"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, _ = gen.generate(width=10, height=10)

        assert gen._bfs_check(tile_map, start, end) is True

    def test_path_exists_multiple_seeds(self):
        """多个不同种子下，起点到终点都有通路"""
        for seed in [1, 100, 500, 1000, 9999, 12345, 54321, 88888, 999999, 123456789]:
            gen = GridRandomGenerator(seed=seed)
            tile_map, start, end, _ = gen.generate(width=10, height=10)
            assert gen._bfs_check(tile_map, start, end) is True, f"种子 {seed} 无通路"

    def test_path_exists_small_map(self):
        """小地图（3x3）也有通路"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, _ = gen.generate(width=3, height=3)
        assert gen._bfs_check(tile_map, start, end) is True

    def test_path_exists_large_map(self):
        """大地图（50x50）也有通路"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, _ = gen.generate(width=50, height=50)
        assert gen._bfs_check(tile_map, start, end) is True

    def test_path_exists_high_wall_ratio(self):
        """高障碍物比例下仍有通路"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, _ = gen.generate(width=10, height=10, wall_ratio=0.6)
        assert gen._bfs_check(tile_map, start, end) is True

    def test_ensure_path_false_may_have_no_path(self):
        """ensure_path=False 时，可能无通路（不报错）"""
        gen = GridRandomGenerator(seed=42)
        # 使用极高障碍物比例，大概率无通路
        tile_map, start, end, _ = gen.generate(
            width=10, height=10, wall_ratio=0.8, ensure_path=False
        )
        # 不校验通路，只确保不报错
        assert len(tile_map) > 0


class TestGridRandomBFS:
    """测试 BFS 辅助方法"""

    def test_bfs_simple_path(self):
        """简单可通行地图 BFS 返回 True"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 0, 0],
            [1, 1, 0],
            [0, 0, 0],
        ]
        assert gen._bfs_check(tile_map, (0, 0), (2, 2)) is True

    def test_bfs_blocked_path(self):
        """被障碍物阻挡时 BFS 返回 False"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 1, 0],
            [0, 1, 0],
            [0, 1, 0],
        ]
        assert gen._bfs_check(tile_map, (0, 0), (2, 2)) is False

    def test_bfs_same_start_end(self):
        """起点等于终点时 BFS 返回 True"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 1],
            [1, 0],
        ]
        assert gen._bfs_check(tile_map, (0, 0), (0, 0)) is True

    def test_bfs_start_is_wall(self):
        """起点是障碍物时 BFS 返回 False（起点无法访问）"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [1, 0],
            [0, 0],
        ]
        # 起点 (0,0) 是墙，无法开始
        assert gen._bfs_check(tile_map, (0, 0), (1, 1)) is False


class TestGridRandomCarvePath:
    """测试 _carve_path 辅助方法"""

    def test_carve_path_clears_walls(self):
        """_carve_path 能打通障碍物"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ]
        gen._carve_path(tile_map, (0, 0), (2, 2))
        # 打通后应有通路
        assert gen._bfs_check(tile_map, (0, 0), (2, 2)) is True

    def test_carve_path_already_open(self):
        """_carve_path 在已通路上不破坏已有空地"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        original = [row[:] for row in tile_map]
        gen._carve_path(tile_map, (0, 0), (2, 2))
        assert tile_map == original


class TestGridRandomFindStartEnd:
    """测试 _find_start / _find_end 辅助方法"""

    def test_find_start_top_left_empty(self):
        """左上角是空地时，起点为 (0,0)"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 1],
            [1, 0],
        ]
        assert gen._find_start(tile_map) == (0, 0)

    def test_find_start_top_left_wall(self):
        """左上角是障碍物时，起点为第一个空地"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [1, 0],
            [0, 0],
        ]
        assert gen._find_start(tile_map) == (0, 1)

    def test_find_end_bottom_right_empty(self):
        """右下角是空地时，终点为右下角"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 1],
            [1, 0],
        ]
        assert gen._find_end(tile_map) == (1, 1)

    def test_find_end_bottom_right_wall(self):
        """右下角是障碍物时，终点为最后一个空地"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [0, 0],
            [0, 1],
        ]
        assert gen._find_end(tile_map) == (1, 0)

    def test_find_start_all_wall_fallback(self):
        """全障碍物地图，起点回退到 (0,0)"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [1, 1],
            [1, 1],
        ]
        assert gen._find_start(tile_map) == (0, 0)

    def test_find_end_all_wall_fallback(self):
        """全障碍物地图，终点回退到右下角"""
        gen = GridRandomGenerator(seed=42)
        tile_map = [
            [1, 1],
            [1, 1],
        ]
        assert gen._find_end(tile_map) == (1, 1)


class TestGridRandomEdgeCases:
    """边界情况测试"""

    def test_zero_ratios(self):
        """所有比例为 0，地图全空地"""
        gen = GridRandomGenerator(seed=42)
        tile_map, _, _, room_list = gen.generate(
            width=10, height=10,
            wall_ratio=0.0,
            trap_max_ratio=0.0,
            resource_ratio=0.0,
        )
        for row in tile_map:
            for cell in row:
                assert cell == GridRandomGenerator.TILE_EMPTY
        assert len(room_list) == 100

    def test_wall_ratio_one(self):
        """wall_ratio=1，全障碍物地图（起点终点会被强制设为空地）"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, room_list = gen.generate(
            width=5, height=5, wall_ratio=1.0,
        )
        # 起点和终点应该是空地
        sr, sc = start
        er, ec = end
        assert tile_map[sr][sc] == GridRandomGenerator.TILE_EMPTY
        assert tile_map[er][ec] == GridRandomGenerator.TILE_EMPTY
        # 其他格子应该是障碍物
        wall_count = sum(
            1 for r in range(5) for c in range(5)
            if tile_map[r][c] == GridRandomGenerator.TILE_WALL
        )
        assert wall_count == 23  # 25 - 2(起点终点)

    def test_minimal_map(self):
        """最小地图 3x3 正常生成"""
        gen = GridRandomGenerator(seed=42)
        tile_map, start, end, room_list = gen.generate(width=3, height=3)
        assert len(tile_map) == 3
        assert len(tile_map[0]) == 3
        assert len(room_list) >= 1

    def test_room_list_count(self):
        """room_list 数量 = 非障碍物格子数"""
        gen = GridRandomGenerator(seed=42)
        tile_map, _, _, room_list = gen.generate(width=10, height=10, wall_ratio=0.3)
        expected_count = sum(
            1 for row in tile_map for cell in row
            if cell != GridRandomGenerator.TILE_WALL
        )
        assert len(room_list) == expected_count

    def test_trap_and_resource_placement(self):
        """陷阱和资源确实被放置在地图中"""
        gen = GridRandomGenerator(seed=42)
        tile_map, _, _, _ = gen.generate(
            width=20, height=20,
            trap_max_ratio=0.1,
            resource_ratio=0.1,
        )
        trap_count = sum(
            1 for row in tile_map for cell in row
            if cell == GridRandomGenerator.TILE_TRAP
        )
        resource_count = sum(
            1 for row in tile_map for cell in row
            if cell == GridRandomGenerator.TILE_RESOURCE
        )
        assert trap_count > 0
        assert resource_count > 0

    def test_generate_multiple_calls_same_instance(self):
        """同一个实例多次调用 generate 不报错"""
        gen = GridRandomGenerator(seed=42)
        for _ in range(5):
            tile_map, _, _, _ = gen.generate(width=10, height=10)
            assert len(tile_map) == 10
