"""
网格随机算法 (GridRandom) 单元测试

测试覆盖：
1. 参数边界极值测试（最大/最小/0值）
2. 种子一致性回归测试
3. 四算法独立生成测试（GridRandom）
4. 校验失败重试测试（BFS 重试）
5. 模板保存加载测试
6. 超大地图性能测试
7. 压测：1000 次连续生成稳定性
8. 非法参数容错测试
"""

import os
import sys
import json
import time
import pytest
from typing import List, Tuple

# 将被测代码所在目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generated.app import (
    GridRandom,
    GeneratorFactory,
    AlgorithmTypeEnum,
    TileType,
    GenerateResult,
    Room,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def default_generator():
    """返回一个使用默认参数的 GridRandom 实例"""
    return GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)


# ============================================================
# 1. 参数边界极值测试（最大/最小/0值）
# ============================================================

class TestParameterBoundaries:
    """参数边界极值测试"""

    @pytest.mark.parametrize("rows,cols", [
        (1, 1),       # 最小尺寸
        (1, 100),     # 单行
        (100, 1),     # 单列
        (2, 2),       # 最小有效地图
        (100, 100),   # 较大尺寸
        (200, 200),   # 边界大尺寸
    ])
    def test_map_size_boundaries(self, rows, cols):
        """测试地图尺寸边界值"""
        gen = GridRandom(rows=rows, cols=cols, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)
        result = gen.generate()
        assert len(result.tile_map) == rows
        assert len(result.tile_map[0]) == cols
        assert result.start is not None
        assert result.end is not None

    @pytest.mark.parametrize("wall_ratio", [
        0.0,    # 无墙壁
        0.01,   # 极小墙壁比例
        0.5,    # 中等墙壁比例
        0.8,    # 高墙壁比例
        0.99,   # 极高墙壁比例（接近全墙）
    ])
    def test_wall_ratio_boundaries(self, wall_ratio):
        """测试墙壁比例边界值"""
        gen = GridRandom(rows=10, cols=10, wall_ratio=wall_ratio, trap_max_ratio=0.1, seed=42)
        result = gen.generate()
        # 统计墙壁数量
        wall_count = sum(
            1 for row in result.tile_map for cell in row
            if cell == TileType.WALL.value
        )
        total_cells = 10 * 10
        # 墙壁比例应在合理范围内（由于起点终点占位，实际比例可能略低）
        actual_ratio = wall_count / total_cells
        # 允许 ±5% 的浮动
        assert actual_ratio <= wall_ratio + 0.05, f"wall_ratio={wall_ratio}, actual={actual_ratio:.3f}"

    @pytest.mark.parametrize("trap_max_ratio", [
        0.0,    # 无陷阱
        0.01,   # 极小陷阱比例
        0.2,    # 中等陷阱比例
        0.4,    # 较高陷阱比例
        0.5,    # 最大陷阱比例
    ])
    def test_trap_ratio_boundaries(self, trap_max_ratio):
        """测试陷阱比例边界值"""
        gen = GridRandom(rows=10, cols=10, wall_ratio=0.2, trap_max_ratio=trap_max_ratio, seed=42)
        result = gen.generate()
        trap_count = sum(
            1 for row in result.tile_map for cell in row
            if cell == TileType.TRAP.value
        )
        total_cells = 10 * 10
        actual_ratio = trap_count / total_cells
        # 陷阱比例不应超过设定的最大比例（允许少量浮动）
        assert actual_ratio <= trap_max_ratio + 0.02, f"trap_max_ratio={trap_max_ratio}, actual={actual_ratio:.3f}"

    def test_zero_wall_and_trap(self):
        """测试 wall_ratio=0 且 trap_max_ratio=0 的极端情况"""
        gen = GridRandom(rows=5, cols=5, wall_ratio=0.0, trap_max_ratio=0.0, seed=42)
        result = gen.generate()
        for row in result.tile_map:
            for cell in row:
                assert cell in (TileType.EMPTY.value, TileType.START.value, TileType.END.value), \
                    f"Unexpected tile type: {cell}"


# ============================================================
# 2. 种子一致性回归测试
# ============================================================

class TestSeedConsistency:
    """种子一致性回归测试"""

    def test_same_seed_produces_same_result(self):
        """相同种子应生成完全相同的地图"""
        gen1 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=12345)
        gen2 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=12345)

        result1 = gen1.generate()
        result2 = gen2.generate()

        # 地图数据应完全一致
        assert result1.tile_map == result2.tile_map
        assert result1.start == result2.start
        assert result1.end == result2.end

    def test_different_seed_produces_different_result(self):
        """不同种子应生成不同的地图（极大概率）"""
        gen1 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=11111)
        gen2 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=99999)

        result1 = gen1.generate()
        result2 = gen2.generate()

        # 两个地图不太可能完全相同
        assert result1.tile_map != result2.tile_map, "不同种子生成了相同的地图"

    def test_seed_none_produces_different_results(self):
        """seed=None 时每次生成应不同"""
        gen1 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=None)
        gen2 = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=None)

        result1 = gen1.generate()
        result2 = gen2.generate()

        # 极大概率不同
        assert result1.tile_map != result2.tile_map, "seed=None 时生成了相同的地图"

    def test_seed_regression_fixed_result(self):
        """回归测试：固定种子 42 的已知输出结构"""
        gen = GridRandom(rows=5, cols=5, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)
        result = gen.generate()

        # 验证基本结构
        assert len(result.tile_map) == 5
        assert len(result.tile_map[0]) == 5
        assert result.start == (0, 0)
        assert result.end == (4, 4)
        assert result.tile_map[0][0] == TileType.START.value
        assert result.tile_map[4][4] == TileType.END.value

        # 验证起点终点不是墙壁
        assert result.tile_map[0][0] != TileType.WALL.value
        assert result.tile_map[4][4] != TileType.WALL.value


# ============================================================
# 3. 四算法独立生成测试（GridRandom）
# ============================================================

class TestGridRandomAlgorithm:
    """GridRandom 算法独立生成测试"""

    def test_generate_returns_correct_type(self, default_generator):
        """generate() 应返回 GenerateResult 类型"""
        result = default_generator.generate()
        assert isinstance(result, GenerateResult)

    def test_generate_result_contains_required_fields(self, default_generator):
        """生成结果应包含所有必要字段"""
        result = default_generator.generate()
        assert hasattr(result, "tile_map")
        assert hasattr(result, "start")
        assert hasattr(result, "end")
        assert hasattr(result, "room_list")
        assert hasattr(result, "algorithm")

    def test_algorithm_name_is_correct(self, default_generator):
        """算法名称应为 GridRandom"""
        result = default_generator.generate()
        assert result.algorithm == "GridRandom"

    def test_tile_map_dimensions(self, default_generator):
        """地图尺寸应与初始化参数一致"""
        result = default_generator.generate()
        assert len(result.tile_map) == 10
        assert len(result.tile_map[0]) == 10

    def test_start_and_end_positions(self, default_generator):
        """起点应为 (0,0)，终点应为 (rows-1, cols-1)"""
        result = default_generator.generate()
        assert result.start == (0, 0)
        assert result.end == (9, 9)

    def test_tile_types_are_valid(self, default_generator):
        """所有瓦片类型应在 TileType 枚举范围内"""
        result = default_generator.generate()
        valid_types = {t.value for t in TileType}
        for row in result.tile_map:
            for cell in row:
                assert cell in valid_types, f"Invalid tile type: {cell}"

    def test_start_end_not_wall(self, default_generator):
        """起点和终点不应是墙壁"""
        result = default_generator.generate()
        sr, sc = result.start
        er, ec = result.end
        assert result.tile_map[sr][sc] != TileType.WALL.value
        assert result.tile_map[er][ec] != TileType.WALL.value

    def test_room_list_not_empty(self, default_generator):
        """room_list 不应为空"""
        result = default_generator.generate()
        assert len(result.room_list) > 0

    def test_factory_creates_grid_random(self):
        """工厂模式应能正确创建 GridRandom 实例"""
        gen = GeneratorFactory.create_generator(
            AlgorithmTypeEnum.GridRandom,
            rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=42
        )
        assert isinstance(gen, GridRandom)
        result = gen.generate()
        assert result.algorithm == "GridRandom"


# ============================================================
# 4. 校验失败重试测试（BFS 重试）
# ============================================================

class TestBFSRetry:
    """校验失败重试测试"""

    def test_path_is_always_reachable(self, default_generator):
        """生成的地图起点到终点必须可达"""
        result = default_generator.generate()
        assert self._bfs_check(result.tile_map, result.start, result.end), "起点到终点不可达"

    def test_high_wall_ratio_still_reachable(self):
        """高墙壁比例下仍应保证通路可达"""
        gen = GridRandom(rows=10, cols=10, wall_ratio=0.6, trap_max_ratio=0.05, seed=42)
        result = gen.generate()
        assert self._bfs_check(result.tile_map, result.start, result.end), "高墙壁比例下不可达"

    def test_very_high_wall_ratio_still_reachable(self):
        """极高墙壁比例下仍应保证通路可达（可能触发重试）"""
        gen = GridRandom(rows=8, cols=8, wall_ratio=0.75, trap_max_ratio=0.0, seed=42)
        result = gen.generate()
        assert self._bfs_check(result.tile_map, result.start, result.end), "极高墙壁比例下不可达"

    def test_retry_does_not_raise_exception(self):
        """多次重试不应抛出异常"""
        for seed in range(20):
            gen = GridRandom(rows=6, cols=6, wall_ratio=0.5, trap_max_ratio=0.1, seed=seed)
            try:
                result = gen.generate()
                assert self._bfs_check(result.tile_map, result.start, result.end)
            except RecursionError:
                pytest.fail(f"seed={seed} 触发了递归错误")

    @staticmethod
    def _bfs_check(tile_map: List[List[int]], start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """BFS 检查起点到终点是否可达"""
        from collections import deque
        rows, cols = len(tile_map), len(tile_map[0])
        visited = [[False] * cols for _ in range(rows)]
        queue = deque()
        queue.append(start)
        visited[start[0]][start[1]] = True

        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        while queue:
            r, c = queue.popleft()
            if (r, c) == end:
                return True
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                    if tile_map[nr][nc] != TileType.WALL.value:
                        visited[nr][nc] = True
                        queue.append((nr, nc))
        return False


# ============================================================
# 5. 模板保存加载测试
# ============================================================

class TestTemplateSaveLoad:
    """模板保存加载测试"""

    @pytest.fixture
    def temp_json_path(self, tmp_path):
        """返回一个临时 JSON 文件路径"""
        return tmp_path / "test_map_template.json"

    def test_save_result_to_json(self, default_generator, temp_json_path):
        """生成结果应能保存为 JSON 文件"""
        result = default_generator.generate()
        data = {
            "algorithm": result.algorithm,
            "rows": len(result.tile_map),
            "cols": len(result.tile_map[0]),
            "tile_map": result.tile_map,
            "start": list(result.start),
            "end": list(result.end),
            "rooms": [
                {
                    "room_id": r.room_id,
                    "x": r.x,
                    "y": r.y,
                    "width": r.width,
                    "height": r.height,
                    "room_type": r.room_type,
                }
                for r in result.room_list
            ],
        }
        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        assert temp_json_path.exists()
        assert temp_json_path.stat().st_size > 0

    def test_load_result_from_json(self, default_generator, temp_json_path):
        """从 JSON 文件加载的数据应与保存前一致"""
        result = default_generator.generate()

        # 保存
        data = {
            "algorithm": result.algorithm,
            "rows": len(result.tile_map),
            "cols": len(result.tile_map[0]),
            "tile_map": result.tile_map,
            "start": list(result.start),
            "end": list(result.end),
            "rooms": [
                {
                    "room_id": r.room_id,
                    "x": r.x,
                    "y": r.y,
                    "width": r.width,
                    "height": r.height,
                    "room_type": r.room_type,
                }
                for r in result.room_list
            ],
        }
        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 加载
        with open(temp_json_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        # 验证
        assert loaded_data["algorithm"] == result.algorithm
        assert loaded_data["rows"] == len(result.tile_map)
        assert loaded_data["cols"] == len(result.tile_map[0])
        assert loaded_data["tile_map"] == result.tile_map
        assert tuple(loaded_data["start"]) == result.start
        assert tuple(loaded_data["end"]) == result.end
        assert len(loaded_data["rooms"]) == len(result.room_list)

    def test_save_load_round_trip(self, default_generator, temp_json_path):
        """保存后再加载，重新构建的地图应与原图一致"""
        result = default_generator.generate()

        # 保存
        data = {
            "tile_map": result.tile_map,
            "start": list(result.start),
            "end": list(result.end),
        }
        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # 加载
        with open(temp_json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        # 重建
        reconstructed_map = loaded["tile_map"]
        reconstructed_start = tuple(loaded["start"])
        reconstructed_end = tuple(loaded["end"])

        assert reconstructed_map == result.tile_map
        assert reconstructed_start == result.start
        assert reconstructed_end == result.end


# ============================================================
# 6. 超大地图性能测试
# ============================================================

class TestLargeMapPerformance:
    """超大地图性能测试"""

    @pytest.mark.parametrize("rows,cols,timeout", [
        (50, 50, 2.0),
        (100, 100, 5.0),
        (200, 200, 10.0),
    ])
    def test_large_map_generation_time(self, rows, cols, timeout):
        """超大地图生成应在规定时间内完成"""
        gen = GridRandom(rows=rows, cols=cols, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)
        start_time = time.time()
        result = gen.generate()
        elapsed = time.time() - start_time

        assert elapsed < timeout, f"生成 {rows}x{cols} 地图耗时 {elapsed:.3f}s，超过 {timeout}s"
        assert len(result.tile_map) == rows
        assert len(result.tile_map[0]) == cols

    def test_large_map_path_reachable(self):
        """超大地图起点到终点仍应可达"""
        gen = GridRandom(rows=100, cols=100, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)
        result = gen.generate()
        assert TestBFSRetry._bfs_check(result.tile_map, result.start, result.end), "超大地图不可达"


# ============================================================
# 7. 压测：1000 次连续生成稳定性
# ============================================================

class TestStressTest:
    """压测：1000 次连续生成稳定性"""

    @pytest.mark.slow
    def test_1000_consecutive_generations(self):
        """连续生成 1000 次，验证稳定性和正确性"""
        for i in range(1000):
            gen = GridRandom(
                rows=10, cols=10,
                wall_ratio=0.3, trap_max_ratio=0.1,
                seed=i  # 每次使用不同种子
            )
            result = gen.generate()

            # 基本正确性校验
            assert len(result.tile_map) == 10
            assert len(result.tile_map[0]) == 10
            assert result.start == (0, 0)
            assert result.end == (9, 9)
            assert result.tile_map[0][0] == TileType.START.value
            assert result.tile_map[9][9] == TileType.END.value

            # 通路校验
            assert TestBFSRetry._bfs_check(result.tile_map, result.start, result.end), \
                f"seed={i} 生成的地图不可达"

    @pytest.mark.slow
    def test_1000_generations_performance(self):
        """1000 次连续生成的总耗时应在合理范围内"""
        start_time = time.time()
        for i in range(1000):
            gen = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=i)
            gen.generate()
        elapsed = time.time() - start_time
        # 每次生成平均不超过 0.1 秒
        assert elapsed < 100.0, f"1000 次生成总耗时 {elapsed:.3f}s，平均每次 {elapsed/1000:.3f}s"


# ============================================================
# 8. 非法参数容错测试
# ============================================================

class TestInvalidParameters:
    """非法参数容错测试"""

    @pytest.mark.parametrize("rows,cols", [
        (0, 10),      # rows 为 0
        (10, 0),      # cols 为 0
        (-1, 10),     # rows 为负数
        (10, -5),     # cols 为负数
        (0, 0),       # 均为 0
    ])
    def test_invalid_map_size(self, rows, cols):
        """非法地图尺寸应抛出异常"""
        with pytest.raises((ValueError, IndexError, RecursionError)):
            gen = GridRandom(rows=rows, cols=cols, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)
            gen.generate()

    @pytest.mark.parametrize("wall_ratio", [
        -0.1,   # 负数
        1.5,    # 大于 1
        -1.0,   # 负整数
    ])
    def test_invalid_wall_ratio(self, wall_ratio):
        """非法墙壁比例应抛出异常"""
        with pytest.raises((ValueError, AssertionError)):
            gen = GridRandom(rows=10, cols=10, wall_ratio=wall_ratio, trap_max_ratio=0.1, seed=42)
            gen.generate()

    @pytest.mark.parametrize("trap_max_ratio", [
        -0.1,   # 负数
        1.5,    # 大于 1
        -0.5,   # 负数
    ])
    def test_invalid_trap_ratio(self, trap_max_ratio):
        """非法陷阱比例应抛出异常"""
        with pytest.raises((ValueError, AssertionError)):
            gen = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=trap_max_ratio, seed=42)
            gen.generate()

    def test_non_integer_dimensions(self):
        """非整数尺寸应抛出 TypeError"""
        with pytest.raises(TypeError):
            GridRandom(rows="10", cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)

        with pytest.raises(TypeError):
            GridRandom(rows=10, cols=10.5, wall_ratio=0.3, trap_max_ratio=0.1, seed=42)

    def test_non_float_ratios(self):
        """非浮点比例应抛出 TypeError"""
        with pytest.raises(TypeError):
            GridRandom(rows=10, cols=10, wall_ratio="0.3", trap_max_ratio=0.1, seed=42)

        with pytest.raises(TypeError):
            GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio="0.1", seed=42)

    def test_unknown_algorithm_type(self):
        """未知算法类型应抛出 ValueError"""
        with pytest.raises(ValueError):
            GeneratorFactory.create_generator("UnknownAlgorithm", rows=10, cols=10)


# ============================================================
# 组合测试：多维度参数组合
# ============================================================

class TestParameterCombinations:
    """多维度参数组合测试"""

    @pytest.mark.parametrize("rows,cols,wall_ratio,trap_max_ratio", [
        (5, 5, 0.2, 0.05),
        (10, 15, 0.3, 0.1),
        (20, 10, 0.4, 0.15),
        (15, 20, 0.25, 0.2),
        (8, 12, 0.35, 0.08),
    ])
    def test_various_parameter_combinations(self, rows, cols, wall_ratio, trap_max_ratio):
        """多种参数组合下生成应正确"""
        gen = GridRandom(
            rows=rows, cols=cols,
            wall_ratio=wall_ratio, trap_max_ratio=trap_max_ratio,
            seed=42
        )
        result = gen.generate()

        assert len(result.tile_map) == rows
        assert len(result.tile_map[0]) == cols
        assert result.start == (0, 0)
        assert result.end == (rows - 1, cols - 1)
        assert TestBFSRetry._bfs_check(result.tile_map, result.start, result.end)

    def test_different_seeds_same_parameters(self):
        """相同参数不同种子，地图结构应不同但都合法"""
        results = []
        for seed in range(10):
            gen = GridRandom(rows=10, cols=10, wall_ratio=0.3, trap_max_ratio=0.1, seed=seed)
            result = gen.generate()
            results.append(result)

            # 每个结果都应合法
            assert TestBFSRetry._bfs_check(result.tile_map, result.start, result.end)

        # 至少应有部分地图不同
        maps = [r.tile_map for r in results]
        unique_maps = set(tuple(tuple(row) for row in m) for m in maps)
        assert len(unique_maps) > 1, "所有种子生成的地图完全相同"


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])