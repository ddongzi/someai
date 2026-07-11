"""
抽象基类模块。

定义所有地图生成算法的统一接口 BaseGenerator。
采用抽象基类 + 工厂模式，四种算法完全解耦。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from core.config import MapBasicConfig
from core.seed_manager import SeedManager


class GenerateResult:
    """生成结果数据结构。"""

    def __init__(
        self,
        tile_map: list[list[int]],
        start: tuple[int, int],
        end: tuple[int, int],
        room_list: Optional[list[dict[str, Any]]] = None,
        seed: int = 0,
        config: Optional[MapBasicConfig] = None,
    ):
        """
        初始化生成结果。

        Args:
            tile_map: 二维地块矩阵，每个元素为 TileType 枚举值
            start: 起点坐标 (row, col)
            end: 终点坐标 (row, col)
            room_list: 房间列表，每个房间为包含位置信息的字典
            seed: 使用的整数种子
            config: 使用的配置
        """
        self.tile_map = tile_map
        self.start = start
        self.end = end
        self.room_list = room_list or []
        self.seed = seed
        self.config = config

    def to_dict(self) -> dict:
        """将结果序列化为字典。"""
        return {
            "tile_map": self.tile_map,
            "start": list(self.start),
            "end": list(self.end),
            "room_list": self.room_list,
            "seed": self.seed,
            "config": self.config.model_dump() if self.config else None,
        }


class BaseGenerator(ABC):
    """地图生成器抽象基类。"""

    def __init__(self, config: Optional[MapBasicConfig] = None):
        """
        初始化生成器。

        Args:
            config: 地图生成配置，为 None 时使用默认配置。
        """
        self.config = config or MapBasicConfig()
        self.seed_manager = SeedManager(self.config.seed)
        self._tile_map: list[list[int]] = []
        self._start: tuple[int, int] = (0, 0)
        self._end: tuple[int, int] = (0, 0)
        self._room_list: list[dict[str, Any]] = []

    @abstractmethod
    def generate(self) -> GenerateResult:
        """
        执行地图生成。

        Returns:
            GenerateResult: 包含 tile_map, start, end, room_list 的生成结果。
        """
        ...

    def reset(self, config: Optional[MapBasicConfig] = None) -> None:
        """
        重置生成器状态。

        Args:
            config: 新的配置，为 None 时保持原配置。
        """
        if config is not None:
            self.config = config
        self.seed_manager.reset(self.config.seed)
        self._tile_map = []
        self._start = (0, 0)
        self._end = (0, 0)
        self._room_list = []

    def get_result(self) -> GenerateResult:
        """获取当前生成结果。"""
        return GenerateResult(
            tile_map=self._tile_map,
            start=self._start,
            end=self._end,
            room_list=self._room_list,
            seed=self.seed_manager.int_seed,
            config=self.config,
        )
