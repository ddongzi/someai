"""
网格随机算法 (GridRandom) 实现
===============================
适用：小型闯关、小游戏地图
核心逻辑：根据 wallRatio / trapMaxRatio 逐地块随机生成，保证基础通路，最后 BFS 校验通路。

依赖：Python 3.9+, Pydantic 2.x
"""

import random
import hashlib
import time
import json
from abc import ABC, abstractmethod
from enum import IntEnum, StrEnum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# 1. 枚举定义
# ============================================================

class TileType(IntEnum):
    """地块类型"""
    GROUND = 0      # 空地/可通行
    WALL = 1        # 墙壁/障碍物
    WATER = 2       # 水域（网格随机算法不使用）
    TRAP_TILE = 3   # 陷阱地块


class AlgorithmTypeEnum(StrEnum):
    """算法类型枚举"""
    GridRandom = "GridRandom"
    RoomSplit = "RoomSplit"
    RecursiveBacktrack = "RecursiveBacktrack"
    PerlinNoise = "PerlinNoise"


class RoomTypeEnum(StrEnum):
    """房间类型枚举（网格随机算法不使用，但保留以统一接口）"""
    battle = "battle"
    treasure = "treasure"
    rest = "rest"
    boss = "boss"


# ============================================================
# 2. 配置模型 (Pydantic)
# ============================================================

class MapBasicConfig(BaseModel):
    """地图基础配置，使用 Pydantic 进行参数校验"""
    width: int = Field(default=50, ge=10, le=1000)
    height: int = Field(default=50, ge=10, le=1000)
    isRandomSize: bool = False
    widthRange: list[int] = Field(default=[20, 100], min_length=2, max_length=2)
    heightRange: list[int] = Field(default=[20, 100], min_length=2, max_length=2)
    wallRatio: int = Field(default=30, ge=0, le=60)
    trapMaxRatio: int = Field(default=15, ge=0, le=30)
    roomMinCount: int = Field(default=3, ge=1, le=50)
    roomMaxCount: int = Field(default=15, ge=1, le=50)
    singleRoomMinW: int = Field(default=4, ge=2, le=20)
    singleRoomMaxW: int = Field(default=12, ge=4, le=20)
    singleRoomMinH: int = Field(default=4, ge=2, le=20)
    singleRoomMaxH: int = Field(default=12, ge=4, le=20)
    pathWidth: int = Field(default=2, ge=1, le=5)
    difficultyLevel: int = Field(default=1, ge=1, le=5)

    @field_validator('widthRange')
    @classmethod
    def validate_width_range(cls, v):
        if v[0] >= v[1]:
            raise ValueError('widthRange[0] must be less than widthRange[1]')
        if v[0] < 10 or v[1] > 1000:
            raise ValueError('widthRange values must be in [10, 1000]')
        return v

    @field_validator('heightRange')
    @classmethod
    def validate_height_range(cls, v):
        if v[0] >= v[1]:
            raise ValueError('heightRange[0] must be less than heightRange[1]')
        if v[0] < 10 or v[1] > 1000:
            raise ValueError('heightRange values must be in [10, 1000]')
        return v

    @field_validator('roomMaxCount')
    @classmethod
    def validate_room_count(cls, v, info):
        if 'roomMinCount' in info.data and v < info.data['roomMinCount']:
            raise ValueError('roomMaxCount must be >= roomMinCount')
        return v

    @field_validator('singleRoomMaxW')
    @classmethod
    def validate_room_max_w(cls, v, info):
        if 'singleRoomMinW' in info.data and v < info.data['singleRoomMinW']:
            raise ValueError('singleRoomMaxW must be >= singleRoomMinW')
        return v

    @field_validator('singleRoomMaxH')
    @classmethod
    def validate_room_max_h(cls, v, info):
        if 'singleRoomMinH' in info.data and v < info.data['singleRoomMinH']:
            raise ValueError('singleRoomMaxH must be >= singleRoomMinH')
        return v


# ============================================================
# 3. 数据模型
# ============================================================

class Position(BaseModel):
    """坐标位置"""
    x: int
    y: int


class RoomData(BaseModel):
    """房间数据（网格随机算法不使用，但保留接口兼容性）"""
    roomId: int
    x: int
    y: int
    width: int
    height: int
    roomType: str = "battle"


class MonsterData(BaseModel):
    """怪物数据"""
    id: int
    x: int
    y: int
    isBoss: bool = False


class ItemData(BaseModel):
    """道具数据"""
    id: int
    x: int
    y: int


class ChestData(BaseModel):
    """宝箱数据"""
    id: int
    x: int
    y: int


class TrapData(BaseModel):
    """陷阱数据"""
    id: int
    x: int
    y: int
    damage: int = 10


class MapFullData(BaseModel):
    """完整地图数据"""
    seed: str
    mapWidth: int
    mapHeight: int
    tileLayer: list[list[int]]
    startPos: Position
    endPos: Position
    roomList: list[RoomData] = []
    monsterData: list[MonsterData] = []
    itemData: list[ItemData] = []
    chestData: list[ChestData] = []
    trapData: list[TrapData] = []
    generateCostMs: int = 0
    retryCount: int = 0
    checkPass: bool = True


# ============================================================
# 4. 种子工具
# ============================================================

class SeedUtils:
    """种子工具：支持 int/str 种子，保证确定性复现"""

    @staticmethod
    def normalize_seed(seed: Optional[str | int] = None) -> str:
        """
        标准化种子。
        - int 种子范围：1 ~ 999999999
        - str 种子：长度 1~32，仅字母数字，非法字符自动清洗
        - 非法种子：自动生成 6 位随机数字兜底
        """
        if seed is None:
            # 自动生成 6 位随机数字
            return str(random.randint(100000, 999999))

        if isinstance(seed, int):
            if 1 <= seed <= 999999999:
                return str(seed)
            # 超出范围，取模后保证在范围内
            return str((abs(seed) % 999999999) + 1)

        if isinstance(seed, str):
            if len(seed) == 0 or len(seed) > 32:
                return str(random.randint(100000, 999999))
            # 清洗非法字符，仅保留字母数字
            cleaned = ''.join(c for c in seed if c.isalnum())
            if len(cleaned) == 0:
                return str(random.randint(100000, 999999))
            return cleaned[:32]

        return str(random.randint(100000, 999999))

    @staticmethod
    def seed_to_int(seed_str: str) -> int:
        """字符串种子统一 hash 转为整数种子"""
        try:
            return int(seed_str)
        except ValueError:
            # 使用 hashlib 将字符串 hash 为整数
            hash_bytes = hashlib.sha256(seed_str.encode('utf-8')).digest()
            return int.from_bytes(hash_bytes[:8], 'big') % 999999999 + 1


# ============================================================
# 5. 抽象基类
# ============================================================

class BaseGenerator(ABC):
    """
    所有地图生成算法的抽象基类。
    统一接口：generate() -> MapFullData
    """

    def __init__(self, config: MapBasicConfig, seed: Optional[str | int] = None):
        self.config = config
        self.seed_str = SeedUtils.normalize_seed(seed)
        self.seed_int = SeedUtils.seed_to_int(self.seed_str)
        self._random = random.Random(self.seed_int)

    @abstractmethod
    def generate(self) -> MapFullData:
        """生成地图，返回完整地图数据"""
        pass

    def _resolve_size(self) -> tuple[int, int]:
        """根据配置解析最终地图尺寸"""
        if self.config.isRandomSize:
            w = self._random.randint(self.config.widthRange[0], self.config.widthRange[1])
            h = self._random.randint(self.config.heightRange[0], self.config.heightRange[1])
            return w, h
        return self.config.width, self.config.height


# ============================================================
# 6. 网格随机算法实现
# ============================================================

class GridRandomGenerator(BaseGenerator):
    """
    网格随机算法 (GridRandom)
    
    逻辑：
    1. 根据 wallRatio 随机生成墙壁地块
    2. 根据 trapMaxRatio 随机生成陷阱地块
    3. 保证起点和终点为可通行空地
    4. 使用 BFS 校验起点到终点是否存在通路
    5. 若不通则重试，直到生成有效地图或达到最大重试次数
    """

    MAX_RETRY = 50

    def generate(self) -> MapFullData:
        """生成网格随机地图"""
        start_time = time.time()
        retry_count = 0

        width, height = self._resolve_size()

        for attempt in range(self.MAX_RETRY):
            retry_count = attempt
            tile_layer = self._generate_tile_layer(width, height)

            # 选取起点（左上区域）和终点（右下区域）
            start_pos, end_pos = self._pick_start_end(width, height, tile_layer)

            # BFS 校验通路
            if self._bfs_check(tile_layer, start_pos, end_pos, width, height):
                # 生成成功
                elapsed_ms = int((time.time() - start_time) * 1000)

                # 收集陷阱数据
                trap_data = self._collect_trap_data(tile_layer, width, height)

                return MapFullData(
                    seed=self.seed_str,
                    mapWidth=width,
                    mapHeight=height,
                    tileLayer=tile_layer,
                    startPos=Position(x=start_pos[0], y=start_pos[1]),
                    endPos=Position(x=end_pos[0], y=end_pos[1]),
                    roomList=[],
                    monsterData=[],
                    itemData=[],
                    chestData=[],
                    trapData=trap_data,
                    generateCostMs=elapsed_ms,
                    retryCount=retry_count,
                    checkPass=True
                )

        # 所有重试均失败，返回一个全空地的最小有效地图
        elapsed_ms = int((time.time() - start_time) * 1000)
        fallback_tile = [[TileType.GROUND for _ in range(width)] for _ in range(height)]
        # 在边界加墙
        for x in range(width):
            fallback_tile[0][x] = TileType.WALL
            fallback_tile[height - 1][x] = TileType.WALL
        for y in range(height):
            fallback_tile[y][0] = TileType.WALL
            fallback_tile[y][width - 1] = TileType.WALL
        # 留出起点终点
        fallback_tile[1][1] = TileType.GROUND
        fallback_tile[height - 2][width - 2] = TileType.GROUND

        return MapFullData(
            seed=self.seed_str,
            mapWidth=width,
            mapHeight=height,
            tileLayer=fallback_tile,
            startPos=Position(x=1, y=1),
            endPos=Position(x=width - 2, y=height - 2),
            roomList=[],
            monsterData=[],
            itemData=[],
            chestData=[],
            trapData=[],
            generateCostMs=elapsed_ms,
            retryCount=retry_count,
            checkPass=False
        )

    def _generate_tile_layer(self, width: int, height: int) -> list[list[int]]:
        """
        根据 wallRatio 和 trapMaxRatio 逐地块随机生成。
        
        策略：
        - 边界固定为墙壁
        - 内部区域按 wallRatio 概率生成墙壁
        - 非墙壁地块按 trapMaxRatio 概率生成陷阱
        """
        tile_layer = [[TileType.GROUND for _ in range(width)] for _ in range(height)]

        wall_ratio = min(self.config.wallRatio, 60) / 100.0
        trap_ratio = min(self.config.trapMaxRatio, 30) / 100.0

        for y in range(height):
            for x in range(width):
                # 边界固定为墙壁
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    tile_layer[y][x] = TileType.WALL
                else:
                    # 内部区域按概率生成
                    if self._random.random() < wall_ratio:
                        tile_layer[y][x] = TileType.WALL
                    elif self._random.random() < trap_ratio:
                        tile_layer[y][x] = TileType.TRAP_TILE
                    else:
                        tile_layer[y][x] = TileType.GROUND

        return tile_layer

    def _pick_start_end(
        self, width: int, height: int, tile_layer: list[list[int]]
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        选取起点和终点。
        起点在左上 1/4 区域，终点在右下 1/4 区域。
        确保起点和终点都是可通行的空地。
        """
        # 起点：左上区域 (1 ~ width//4, 1 ~ height//4)
        start_x = self._random.randint(1, max(1, width // 4))
        start_y = self._random.randint(1, max(1, height // 4))
        tile_layer[start_y][start_x] = TileType.GROUND

        # 终点：右下区域 (3*width//4 ~ width-2, 3*height//4 ~ height-2)
        end_x = self._random.randint(max(width // 2, 3 * width // 4), width - 2)
        end_y = self._random.randint(max(height // 2, 3 * height // 4), height - 2)
        tile_layer[end_y][end_x] = TileType.GROUND

        return (start_x, start_y), (end_x, end_y)

    def _bfs_check(
        self,
        tile_layer: list[list[int]],
        start: tuple[int, int],
        end: tuple[int, int],
        width: int,
        height: int,
    ) -> bool:
        """
        使用 BFS 校验起点到终点是否存在通路。
        只允许在 GROUND 上行走。
        """
        if tile_layer[start[1]][start[0]] != TileType.GROUND:
            return False
        if tile_layer[end[1]][end[0]] != TileType.GROUND:
            return False

        visited = [[False for _ in range(width)] for _ in range(height)]
        queue = [start]
        visited[start[1]][start[0]] = True

        # 四方向移动
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) == end:
                return True

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if not visited[ny][nx] and tile_layer[ny][nx] == TileType.GROUND:
                        visited[ny][nx] = True
                        queue.append((nx, ny))

        return False

    def _collect_trap_data(
        self, tile_layer: list[list[int]], width: int, height: int
    ) -> list[TrapData]:
        """收集所有陷阱地块数据"""
        trap_data = []
        trap_id = 4001
        for y in range(height):
            for x in range(width):
                if tile_layer[y][x] == TileType.TRAP_TILE:
                    # 根据难度等级计算伤害
                    damage = 5 * self.config.difficultyLevel
                    trap_data.append(TrapData(id=trap_id, x=x, y=y, damage=damage))
                    trap_id += 1
        return trap_data


# ============================================================
# 7. 工厂模式
# ============================================================

class GeneratorFactory:
    """
    生成器工厂，负责注册和创建各类地图生成算法实例。
    采用工厂模式，四种算法完全解耦。
    """

    _generators: dict[str, type[BaseGenerator]] = {}

    @classmethod
    def register(cls, algorithm_type: str, generator_cls: type[BaseGenerator]) -> None:
        """注册生成器类"""
        cls._generators[algorithm_type] = generator_cls

    @classmethod
    def create(
        cls,
        algorithm_type: str,
        config: MapBasicConfig,
        seed: Optional[str | int] = None,
    ) -> BaseGenerator:
        """创建生成器实例"""
        if algorithm_type not in cls._generators:
            raise ValueError(f"Unknown algorithm type: {algorithm_type}. "
                             f"Available: {list(cls._generators.keys())}")
        return cls._generators[algorithm_type](config, seed)

    @classmethod
    def available_algorithms(cls) -> list[str]:
        """返回所有已注册的算法类型列表"""
        return list(cls._generators.keys())


# 注册网格随机算法
GeneratorFactory.register(AlgorithmTypeEnum.GridRandom, GridRandomGenerator)


# ============================================================
# 8. 对外接口
# ============================================================

def GenerateMap(
    algorithm_type: Optional[str] = None,
    config: Optional[MapBasicConfig] = None,
    seed: Optional[str | int] = None,
) -> MapFullData:
    """
    生成地图的对外接口。
    
    Args:
        algorithm_type: 算法类型，可选，不传使用默认算法 (GridRandom)
        config: 地图配置，可选，不传使用默认配置
        seed: 随机种子，可选，不传自动生成
        
    Returns:
        MapFullData: 完整地图数据
    """
    if algorithm_type is None:
        algorithm_type = AlgorithmTypeEnum.GridRandom

    if config is None:
        config = MapBasicConfig()

    generator = GeneratorFactory.create(algorithm_type, config, seed)
    return generator.generate()


def SetMapBasicConfig(config: dict) -> MapBasicConfig:
    """
    设置地图基本配置。
    
    Args:
        config: 配置字典
        
    Returns:
        MapBasicConfig: 校验后的配置对象
    """
    return MapBasicConfig(**config)


# ============================================================
# 9. 主程序入口 / 示例
# ============================================================

if __name__ == "__main__":
    # 示例：使用默认配置生成地图
    print("=== 使用默认配置生成网格随机地图 ===")
    result = GenerateMap(seed="hello_map")
    print(f"种子: {result.seed}")
    print(f"地图尺寸: {result.mapWidth}x{result.mapHeight}")
    print(f"起点: ({result.startPos.x}, {result.startPos.y})")
    print(f"终点: ({result.endPos.x}, {result.endPos.y})")
    print(f"生成耗时: {result.generateCostMs}ms")
    print(f"重试次数: {result.retryCount}")
    print(f"通路校验: {'通过' if result.checkPass else '失败'}")
    print(f"陷阱数量: {len(result.trapData)}")
    print(f"地图数据 (前5行):")
    for row in result.tileLayer[:5]:
        print(f"  {row}")

    # 示例：自定义配置
    print("\n=== 自定义配置生成地图 ===")
    custom_config = MapBasicConfig(
        width=30,
        height=30,
        wallRatio=20,
        trapMaxRatio=10,
        difficultyLevel=3,
    )
    result2 = GenerateMap(
        algorithm_type="GridRandom",
        config=custom_config,
        seed=12345,
    )
    print(f"种子: {result2.seed}")
    print(f"地图尺寸: {result2.mapWidth}x{result2.mapHeight}")
    print(f"通路校验: {'通过' if result2.checkPass else '失败'}")

    # 示例：确定性复现（相同种子生成相同地图）
    print("\n=== 确定性复现验证 ===")
    r1 = GenerateMap(seed="test_seed")
    r2 = GenerateMap(seed="test_seed")
    print(f"两次生成 tileLayer 相同: {r1.tileLayer == r2.tileLayer}")

    # 示例：输出 JSON
    print("\n=== 地图 JSON 输出 (部分) ===")
    json_str = result.model_dump_json(indent=2)
    # 只打印前 500 字符
    print(json_str[:500] + "...")