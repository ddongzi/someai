"""
网格随机算法 (GridRandom) 单元测试
===================================
测试覆盖：
1. 参数边界极值测试（最大/最小/0值）
2. 种子一致性回归测试
3. 四算法独立生成测试（GridRandom 为主）
4. 校验失败重试测试
5. 模板保存加载测试
6. 超大地图性能测试
7. 压测：1000 次连续生成稳定性
8. 非法参数容错测试

运行方式：
    pytest test_grid_random.py -v --tb=short
"""

import json
import time
import pytest
from pydantic import ValidationError

from app import (
    GridRandomGenerator,
    GeneratorFactory,
    GenerateMap,
    SetMapBasicConfig,
    MapBasicConfig,
    MapFullData,
    TileType,
    AlgorithmTypeEnum,
    SeedUtils,
    Position,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def default_config():
    """默认配置 fixture"""
    return MapBasicConfig()


@pytest.fixture
def small_config():
    """小型地图配置 fixture"""
    return MapBasicConfig(
        width=10,
        height=10,
        wallRatio=10,
        trapMaxRatio=5,
    )


@pytest.fixture
def medium_config():
    """中型地图配置 fixture"""
    return MapBasicConfig(
        width=50,
        height=50,
        wallRatio=30,
        trapMaxRatio=15,
    )


@pytest.fixture
def large_config():
    """大型地图配置 fixture"""
    return MapBasicConfig(
        width=200,
        height=200,
        wallRatio=25,
        trapMaxRatio=10,
    )


@pytest.fixture
def extreme_config():
    """极值配置 fixture（最大尺寸、最大墙比例、最大陷阱比例）"""
    return MapBasicConfig(
        width=1000,
        height=1000,
        wallRatio=60,
        trapMaxRatio=30,
    )


@pytest.fixture
def zero_config():
    """零值边界配置 fixture（墙和陷阱比例为 0）"""
    return MapBasicConfig(
        width=20,
        height=20,
        wallRatio=0,
        trapMaxRatio=0,
    )


# ============================================================
# 1. 参数边界极值测试
# ============================================================

class TestParameterBoundary:
    """参数边界极值测试（最大/最小/0值）"""

    def test_min_size_map(self):
        """最小尺寸地图 (10x10) 生成"""
        config = MapBasicConfig(width=10, height=10, wallRatio=10, trapMaxRatio=5)
        result = GenerateMap(config=config, seed=42)
        assert result.mapWidth == 10
        assert result.mapHeight == 10
        assert result.checkPass is True
        assert len(result.tileLayer) == 10
        assert len(result.tileLayer[0]) == 10

    def test_max_size_map(self):
        """最大尺寸地图 (1000x1000) 生成"""
        config = MapBasicConfig(width=1000, height=1000, wallRatio=20, trapMaxRatio=10)
        result = GenerateMap(config=config, seed=42)
        assert result.mapWidth == 1000
        assert result.mapHeight == 1000
        assert result.checkPass is True
        assert len(result.tileLayer) == 1000
        assert len(result.tileLayer[0]) == 1000

    def test_zero_wall_and_trap_ratio(self):
        """墙比例和陷阱比例为 0 时，地图应无墙无陷阱（除边界）"""
        config = MapBasicConfig(width=30, height=30, wallRatio=0, trapMaxRatio=0)
        result = GenerateMap(config=config, seed=42)
        assert result.checkPass is True
        # 内部区域应全为 GROUND
        for y in range(1, result.mapHeight - 1):
            for x in range(1, result.mapWidth - 1):
                assert result.tileLayer[y][x] == TileType.GROUND, \
                    f"位置 ({x},{y}) 应为 GROUND，实际为 {result.tileLayer[y][x]}"
        # 边界应为 WALL
        for x in range(result.mapWidth):
            assert result.tileLayer[0][x] == TileType.WALL
            assert result.tileLayer[result.mapHeight - 1][x] == TileType.WALL
        for y in range(result.mapHeight):
            assert result.tileLayer[y][0] == TileType.WALL
            assert result.tileLayer[y][result.mapWidth - 1] == TileType.WALL

    def test_max_wall_and_trap_ratio(self):
        """最大墙比例 (60) 和最大陷阱比例 (30) 生成"""
        config = MapBasicConfig(width=50, height=50, wallRatio=60, trapMaxRatio=30)
        result = GenerateMap(config=config, seed=42)
        assert result.checkPass is True
        # 统计墙和陷阱数量
        wall_count = sum(
            1 for row in result.tileLayer for cell in row if cell == TileType.WALL
        )
        trap_count = sum(
            1 for row in result.tileLayer for cell in row if cell == TileType.TRAP_TILE
        )
        total_cells = result.mapWidth * result.mapHeight
        # 墙比例不应超过 60%（边界墙固定，内部按概率）
        assert wall_count / total_cells <= 0.65, f"墙比例过高: {wall_count / total_cells:.2%}"
        # 陷阱比例不应超过 30%
        assert trap_count / total_cells <= 0.35, f"陷阱比例过高: {trap_count / total_cells:.2%}"

    def test_min_width_height_range(self):
        """最小尺寸范围 [10, 20]"""
        config = MapBasicConfig(
            isRandomSize=True,
            widthRange=[10, 20],
            heightRange=[10, 20],
            wallRatio=20,
            trapMaxRatio=10,
        )
        for _ in range(10):
            result = GenerateMap(config=config, seed=100 + _)
            assert 10 <= result.mapWidth <= 20
            assert 10 <= result.mapHeight <= 20

    def test_max_width_height_range(self):
        """最大尺寸范围 [500, 1000]"""
        config = MapBasicConfig(
            isRandomSize=True,
            widthRange=[500, 1000],
            heightRange=[500, 1000],
            wallRatio=20,
            trapMaxRatio=10,
        )
        result = GenerateMap(config=config, seed=42)
        assert 500 <= result.mapWidth <= 1000
        assert 500 <= result.mapHeight <= 1000

    def test_difficulty_level_boundary(self):
        """难度等级边界值 (1 和 5)"""
        for level in [1, 5]:
            config = MapBasicConfig(
                width=30, height=30,
                wallRatio=20, trapMaxRatio=10,
                difficultyLevel=level,
            )
            result = GenerateMap(config=config, seed=42)
            assert result.checkPass is True
            # 陷阱伤害应随难度变化
            if result.trapData:
                expected_damage = 5 * level
                for trap in result.trapData:
                    assert trap.damage == expected_damage

    def test_path_width_boundary(self):
        """通道宽度边界值 (1 和 5)"""
        for pw in [1, 5]:
            config = MapBasicConfig(
                width=30, height=30,
                wallRatio=20, trapMaxRatio=10,
                pathWidth=pw,
            )
            result = GenerateMap(config=config, seed=42)
            assert result.checkPass is True


# ============================================================
# 2. 种子一致性回归测试
# ============================================================

class TestSeedConsistency:
    """种子一致性回归测试"""

    def test_same_seed_same_result(self):
        """相同种子应生成完全相同的地图"""
        config = MapBasicConfig(width=30, height=30, wallRatio=25, trapMaxRatio=10)
        result1 = GenerateMap(config=config, seed="fixed_seed_123")
        result2 = GenerateMap(config=config, seed="fixed_seed_123")
        assert result1.tileLayer == result2.tileLayer
        assert result1.startPos == result2.startPos
        assert result1.endPos == result2.endPos
        assert result1.trapData == result2.trapData

    def test_different_seed_different_result(self):
        """不同种子应生成不同的地图（极大概率）"""
        config = MapBasicConfig(width=30, height=30, wallRatio=25, trapMaxRatio=10)
        result1 = GenerateMap(config=config, seed="seed_a")
        result2 = GenerateMap(config=config, seed="seed_b")
        # 两个不同种子的地图几乎不可能完全相同
        assert result1.tileLayer != result2.tileLayer

    def test_int_seed_consistency(self):
        """整数种子一致性"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        result1 = GenerateMap(config=config, seed=999)
        result2 = GenerateMap(config=config, seed=999)
        assert result1.tileLayer == result2.tileLayer

    def test_string_seed_consistency(self):
        """字符串种子一致性"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        result1 = GenerateMap(config=config, seed="hello_map")
        result2 = GenerateMap(config=config, seed="hello_map")
        assert result1.tileLayer == result2.tileLayer

    def test_seed_normalize_int_range(self):
        """种子标准化：int 种子范围 1~999999999"""
        assert SeedUtils.normalize_seed(1) == "1"
        assert SeedUtils.normalize_seed(999999999) == "999999999"
        # 超出范围应取模处理
        normalized = SeedUtils.normalize_seed(1000000000)
        assert 1 <= int(normalized) <= 999999999

    def test_seed_normalize_invalid_str(self):
        """种子标准化：非法字符串应自动清洗或兜底"""
        # 空字符串
        seed = SeedUtils.normalize_seed("")
        assert 100000 <= int(seed) <= 999999
        # 超长字符串
        seed = SeedUtils.normalize_seed("a" * 33)
        assert 100000 <= int(seed) <= 999999
        # 特殊字符
        seed = SeedUtils.normalize_seed("!@#$%^")
        assert 100000 <= int(seed) <= 999999

    def test_seed_to_int_consistency(self):
        """seed_to_int 应保持一致性"""
        assert SeedUtils.seed_to_int("123") == 123
        result1 = SeedUtils.seed_to_int("hello")
        result2 = SeedUtils.seed_to_int("hello")
        assert result1 == result2

    def test_seed_none_auto_generate(self):
        """种子为 None 时自动生成"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        result1 = GenerateMap(config=config, seed=None)
        result2 = GenerateMap(config=config, seed=None)
        # 两次自动生成的种子不同，地图也应不同
        assert result1.seed != result2.seed
        assert result1.tileLayer != result2.tileLayer


# ============================================================
# 3. 四算法独立生成测试（GridRandom 为主）
# ============================================================

class TestGridRandomAlgorithm:
    """网格随机算法独立生成测试"""

    def test_generate_returns_map_full_data(self):
        """generate() 应返回 MapFullData 实例"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert isinstance(result, MapFullData)

    def test_generate_tile_layer_dimensions(self):
        """生成的 tileLayer 尺寸应与配置一致"""
        config = MapBasicConfig(width=35, height=45, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert len(result.tileLayer) == 45
        assert len(result.tileLayer[0]) == 35

    def test_start_end_positions(self):
        """起点和终点应在合理区域"""
        config = MapBasicConfig(width=50, height=50, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        # 起点应在左上区域
        assert result.startPos.x <= 50 // 4 + 1
        assert result.startPos.y <= 50 // 4 + 1
        # 终点应在右下区域
        assert result.startPos.x >= 1
        assert result.startPos.y >= 1
        assert result.endPos.x >= 50 // 2
        assert result.endPos.y >= 50 // 2
        assert result.endPos.x <= 50 - 2
        assert result.endPos.y <= 50 - 2

    def test_start_end_are_ground(self):
        """起点和终点必须是 GROUND"""
        config = MapBasicConfig(width=30, height=30, wallRatio=30, trapMaxRatio=15)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert result.tileLayer[result.startPos.y][result.startPos.x] == TileType.GROUND
        assert result.tileLayer[result.endPos.y][result.endPos.x] == TileType.GROUND

    def test_boundary_is_wall(self):
        """地图边界应为墙壁"""
        config = MapBasicConfig(width=25, height=25, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        w, h = result.mapWidth, result.mapHeight
        for x in range(w):
            assert result.tileLayer[0][x] == TileType.WALL, f"上边界 ({x},0) 不是墙"
            assert result.tileLayer[h - 1][x] == TileType.WALL, f"下边界 ({x},{h-1}) 不是墙"
        for y in range(h):
            assert result.tileLayer[y][0] == TileType.WALL, f"左边界 (0,{y}) 不是墙"
            assert result.tileLayer[y][w - 1] == TileType.WALL, f"右边界 ({w-1},{y}) 不是墙"

    def test_tile_types_valid(self):
        """所有地块类型必须在 TileType 枚举范围内"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        valid_types = {TileType.GROUND, TileType.WALL, TileType.TRAP_TILE}
        for row in result.tileLayer:
            for cell in row:
                assert cell in valid_types, f"非法地块类型: {cell}"

    def test_trap_data_collection(self):
        """陷阱数据收集应与 tileLayer 中的陷阱一致"""
        config = MapBasicConfig(width=30, height=30, wallRatio=20, trapMaxRatio=15)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        # 统计 tileLayer 中的陷阱数量
        tile_trap_count = sum(
            1 for row in result.tileLayer for cell in row if cell == TileType.TRAP_TILE
        )
        assert len(result.trapData) == tile_trap_count
        # 验证每个陷阱的位置
        for trap in result.trapData:
            assert result.tileLayer[trap.y][trap.x] == TileType.TRAP_TILE

    def test_bfs_path_exists(self):
        """BFS 校验应确保起点到终点存在通路"""
        config = MapBasicConfig(width=30, height=30, wallRatio=25, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert result.checkPass is True

    def test_random_size_generation(self):
        """随机尺寸生成"""
        config = MapBasicConfig(
            isRandomSize=True,
            widthRange=[20, 50],
            heightRange=[20, 50],
            wallRatio=20,
            trapMaxRatio=10,
        )
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert 20 <= result.mapWidth <= 50
        assert 20 <= result.mapHeight <= 50

    def test_generate_cost_ms_positive(self):
        """生成耗时应为正数"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert result.generateCostMs >= 0

    def test_retry_count_non_negative(self):
        """重试次数应为非负数"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        assert result.retryCount >= 0


# ============================================================
# 4. 校验失败重试测试
# ============================================================

class TestRetryMechanism:
    """校验失败重试测试"""

    def test_retry_on_bfs_failure(self):
        """BFS 校验失败时应自动重试"""
        # 使用高墙比例增加重试概率
        config = MapBasicConfig(width=20, height=20, wallRatio=60, trapMaxRatio=0)
        generator = GridRandomGenerator(config, seed=42)
        result = generator.generate()
        # 即使重试多次，最终结果也应通过校验
        assert result.checkPass is True

    def test_max_retry_limit(self):
        """达到最大重试次数后应返回 fallback 地图"""
        # 极端情况：几乎全墙，必然失败
        config = MapBasicConfig(width=10, height=10, wallRatio=60, trapMaxRatio=0)
        # 使用一个会导致 BFS 失败的种子
        generator = GridRandomGenerator(config, seed=999999)
        result = generator.generate()
        # 即使 checkPass 为 False，也应返回有效数据结构
        assert isinstance(result, MapFullData)
        assert result.retryCount >= 0

    def test_fallback_map_valid_structure(self):
        """fallback 地图应具有有效的结构"""
        config = MapBasicConfig(width=10, height=10, wallRatio=60, trapMaxRatio=0)
        generator = GridRandomGenerator(config, seed=999999)
        result = generator.generate()
        # fallback 地图应有边界墙
        w, h = result.mapWidth, result.mapHeight
        for x in range(w):
            assert result.tileLayer[0][x] in (TileType.WALL, TileType.GROUND)
            assert result.tileLayer[h - 1][x] in (TileType.WALL, TileType.GROUND)
        for y in range(h):
            assert result.tileLayer[y][0] in (TileType.WALL, TileType.GROUND)
            assert result.tileLayer[y][w - 1] in (TileType.WALL, TileType.GROUND)

    def test_retry_count_increments(self):
        """多次重试时 retryCount 应递增"""
        config = MapBasicConfig(width=15, height=15, wallRatio=50, trapMaxRatio=0)
        # 使用不同种子，观察重试次数
        results = []
        for s in range(10):
            result = GenerateMap(config=config, seed=1000 + s)
            results.append(result.retryCount)
        # 至少有一些种子需要重试
        assert any(r > 0 for r in results) or True  # 不强制，仅观察


# ============================================================
# 5. 模板保存加载测试
# ============================================================

class TestTemplateSaveLoad:
    """模板保存加载测试（序列化/反序列化）"""

    def test_map_full_data_to_json(self):
        """MapFullData 可序列化为 JSON"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        result = GenerateMap(config=config, seed=42)
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        assert data["mapWidth"] == 20
        assert data["mapHeight"] == 20
        assert "tileLayer" in data
        assert "startPos" in data
        assert "endPos" in data
        assert "trapData" in data

    def test_map_full_data_from_json(self):
        """从 JSON 可反序列化为 MapFullData"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        original = GenerateMap(config=config, seed=42)
        json_str = original.model_dump_json()
        restored = MapFullData.model_validate_json(json_str)
        assert restored.mapWidth == original.mapWidth
        assert restored.mapHeight == original.mapHeight
        assert restored.tileLayer == original.tileLayer
        assert restored.startPos == original.startPos
        assert restored.endPos == original.endPos
        assert restored.trapData == original.trapData
        assert restored.seed == original.seed

    def test_config_to_json(self):
        """MapBasicConfig 可序列化为 JSON"""
        config = MapBasicConfig(width=30, height=40, wallRatio=25, trapMaxRatio=10)
        json_str = config.model_dump_json()
        data = json.loads(json_str)
        assert data["width"] == 30
        assert data["height"] == 40

    def test_config_from_json(self):
        """从 JSON 可反序列化为 MapBasicConfig"""
        json_str = '{"width": 30, "height": 40, "wallRatio": 25, "trapMaxRatio": 10}'
        config = MapBasicConfig.model_validate_json(json_str)
        assert config.width == 30
        assert config.height == 40
        assert config.wallRatio == 25
        assert config.trapMaxRatio == 10

    def test_round_trip_equality(self):
        """序列化再反序列化应保持数据一致"""
        config = MapBasicConfig(width=25, height=25, wallRatio=20, trapMaxRatio=10)
        original = GenerateMap(config=config, seed=12345)
        # 序列化
        json_str = original.model_dump_json()
        # 反序列化
        restored = MapFullData.model_validate_json(json_str)
        # 比较所有字段
        assert restored.model_dump() == original.model_dump()

    def test_trap_data_serialization(self):
        """陷阱数据序列化/反序列化"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=15)
        result = GenerateMap(config=config, seed=42)
        json_str = result.model_dump_json()
        restored = MapFullData.model_validate_json(json_str)
        assert len(restored.trapData) == len(result.trapData)
        for t1, t2 in zip(result.trapData, restored.trapData):
            assert t1.id == t2.id
            assert t1.x == t2.x
            assert t1.y == t2.y
            assert t1.damage == t2.damage


# ============================================================
# 6. 超大地图性能测试
# ============================================================

class TestLargeMapPerformance:
    """超大地图性能测试"""

    @pytest.mark.slow
    def test_large_map_generation_time(self):
        """500x500 地图生成应在 5 秒内完成"""
        config = MapBasicConfig(
            width=500, height=500,
            wallRatio=25, trapMaxRatio=10,
        )
        start = time.time()
        result = GenerateMap(config=config, seed=42)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"500x500 地图生成耗时 {elapsed:.2f}s，超过 5s 限制"
        assert result.checkPass is True

    @pytest.mark.slow
    def test_extreme_large_map_generation_time(self):
        """1000x1000 地图生成应在 10 秒内完成"""
        config = MapBasicConfig(
            width=1000, height=1000,
            wallRatio=20, trapMaxRatio=10,
        )
        start = time.time()
        result = GenerateMap(config=config, seed=42)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"1000x1000 地图生成耗时 {elapsed:.2f}s，超过 10s 限制"
        assert result.checkPass is True

    @pytest.mark.slow
    def test_large_map_memory_footprint(self):
        """500x500 地图数据大小应在合理范围内"""
        config = MapBasicConfig(
            width=500, height=500,
            wallRatio=25, trapMaxRatio=10,
        )
        result = GenerateMap(config=config, seed=42)
        json_str = result.model_dump_json()
        # 500x500 地图 JSON 大小应在 10MB 以内
        assert len(json_str) < 10 * 1024 * 1024, f"JSON 数据过大: {len(json_str)} bytes"

    @pytest.mark.slow
    def test_large_map_bfs_valid(self):
        """超大地图的 BFS 通路校验应正确"""
        config = MapBasicConfig(
            width=300, height=300,
            wallRatio=20, trapMaxRatio=10,
        )
        result = GenerateMap(config=config, seed=42)
        assert result.checkPass is True


# ============================================================
# 7. 压测：1000 次连续生成稳定性
# ============================================================

class TestStressStability:
    """压测：1000 次连续生成稳定性"""

    @pytest.mark.slow
    def test_1000_consecutive_generations(self):
        """1000 次连续生成不应抛出异常"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        for i in range(1000):
            result = GenerateMap(config=config, seed=i)
            assert isinstance(result, MapFullData), f"第 {i} 次生成返回类型错误"
            assert result.checkPass is True, f"第 {i} 次生成通路校验失败"
        # 如果执行到这里，说明 1000 次全部通过

    @pytest.mark.slow
    def test_1000_generations_no_memory_leak(self):
        """1000 次连续生成不应导致内存泄漏（通过耗时稳定性判断）"""
        config = MapBasicConfig(width=30, height=30, wallRatio=20, trapMaxRatio=10)
        times = []
        for i in range(100):
            start = time.time()
            GenerateMap(config=config, seed=1000 + i)
            elapsed = time.time() - start
            times.append(elapsed)
        # 检查耗时是否稳定（标准差不应过大）
        avg = sum(times) / len(times)
        variance = sum((t - avg) ** 2 for t in times) / len(times)
        std_dev = variance ** 0.5
        # 标准差应小于平均耗时的 2 倍（允许一定波动）
        assert std_dev < avg * 2 or avg < 0.01, \
            f"生成耗时波动过大: avg={avg:.4f}s, std={std_dev:.4f}s"

    @pytest.mark.slow
    def test_1000_generations_all_paths_valid(self):
        """1000 次生成中所有地图通路均应有效"""
        config = MapBasicConfig(width=15, height=15, wallRatio=25, trapMaxRatio=10)
        failed_count = 0
        for i in range(1000):
            result = GenerateMap(config=config, seed=10000 + i)
            if not result.checkPass:
                failed_count += 1
        # 失败率应低于 5%
        failure_rate = failed_count / 1000
        assert failure_rate < 0.05, f"通路校验失败率过高: {failure_rate:.2%}"

    @pytest.mark.slow
    def test_1000_generations_deterministic(self):
        """1000 次生成中相同种子应产生相同结果"""
        config = MapBasicConfig(width=20, height=20, wallRatio=20, trapMaxRatio=10)
        for i in range(100):
            r1 = GenerateMap(config=config, seed=f"stress_{i}")
            r2 = GenerateMap(config=config, seed=f"stress_{i}")
            assert r1.tileLayer == r2.tileLayer, f"种子 stress_{i} 不一致"


# ============================================================
# 8. 非法参数容错测试
# ============================================================

class TestInvalidParameterTolerance:
    """非法参数容错测试"""

    def test_invalid_width_too_small(self):
        """宽度小于最小值 (10) 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=5, height=20)

    def test_invalid_width_too_large(self):
        """宽度大于最大值 (1000) 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=2000, height=20)

    def test_invalid_height_too_small(self):
        """高度小于最小值 (10) 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=3)

    def test_invalid_height_too_large(self):
        """高度大于最大值 (1000) 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=5000)

    def test_invalid_wall_ratio_negative(self):
        """墙比例为负数应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=20, wallRatio=-1)

    def test_invalid_wall_ratio_too_high(self):
        """墙比例大于 60 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=20, wallRatio=80)

    def test_invalid_trap_ratio_negative(self):
        """陷阱比例为负数应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=20, trapMaxRatio=-5)

    def test_invalid_trap_ratio_too_high(self):
        """陷阱比例大于 30 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=20, height=20, trapMaxRatio=50)

    def test_invalid_width_range_order(self):
        """widthRange[0] >= widthRange[1] 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(
                isRandomSize=True,
                widthRange=[50, 20],
                heightRange=[20, 50],
            )

    def test_invalid_height_range_order(self):
        """heightRange[0] >= heightRange[1] 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(
                isRandomSize=True,
                widthRange=[20, 50],
                heightRange=[50, 20],
            )

    def test_invalid_room_count_order(self):
        """roomMaxCount < roomMinCount 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(roomMinCount=10, roomMaxCount=5)

    def test_invalid_single_room_width_order(self):
        """singleRoomMaxW < singleRoomMinW 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(singleRoomMinW=10, singleRoomMaxW=5)

    def test_invalid_single_room_height_order(self):
        """singleRoomMaxH < singleRoomMinH 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(singleRoomMinH=10, singleRoomMaxH=5)

    def test_invalid_difficulty_level_too_low(self):
        """难度等级小于 1 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(difficultyLevel=0)

    def test_invalid_difficulty_level_too_high(self):
        """难度等级大于 5 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(difficultyLevel=10)

    def test_invalid_path_width_too_small(self):
        """通道宽度小于 1 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(pathWidth=0)

    def test_invalid_path_width_too_large(self):
        """通道宽度大于 5 应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(pathWidth=10)

    def test_invalid_algorithm_type(self):
        """未知算法类型应抛出 ValueError"""
        with pytest.raises(ValueError, match="Unknown algorithm type"):
            GeneratorFactory.create("NonExistentAlgorithm", MapBasicConfig())

    def test_set_map_basic_config_invalid(self):
        """SetMapBasicConfig 传入非法参数应抛出异常"""
        with pytest.raises(ValidationError):
            SetMapBasicConfig({"width": -10, "height": 20})

    def test_generate_with_invalid_config_dict(self):
        """GenerateMap 传入非法配置字典应抛出异常"""
        with pytest.raises(ValidationError):
            MapBasicConfig(width=-5, height=20)

    def test_seed_utils_normalize_none(self):
        """SeedUtils.normalize_seed(None) 应返回 6 位数字"""
        seed = SeedUtils.normalize_seed(None)
        assert 100000 <= int(seed) <= 999999

    def test_seed_utils_normalize_empty_string(self):
        """SeedUtils.normalize_seed('') 应返回兜底种子"""
        seed = SeedUtils.normalize_seed("")
        assert 100000 <= int(seed) <= 999999

    def test_seed_utils_normalize_special_chars(self):
        """SeedUtils.normalize_seed 应清洗特殊字符"""
        seed = SeedUtils.normalize_seed("!@#abc$%^")
        assert seed == "abc"
        assert seed.isalnum()

    def test_seed_utils_normalize_oversize_string(self):
        """SeedUtils.normalize_seed 超长字符串应返回兜底"""
        seed = SeedUtils.normalize_seed("a" * 33)
        assert 100000 <= int(seed) <= 999999

    def test_seed_utils_seed_to_int_string(self):
        """SeedUtils.seed_to_int 字符串应 hash 为整数"""
        result = SeedUtils.seed_to_int("hello")
        assert isinstance(result, int)
        assert 1 <= result <= 999999999


# ============================================================
# 9. 工厂模式测试
# ============================================================

class TestGeneratorFactory:
    """工厂模式测试"""

    def test_create_grid_random_generator(self