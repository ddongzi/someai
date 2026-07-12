"""
生成器工厂模块。

根据算法类型创建对应的生成器实例，实现算法解耦。
"""

from typing import Optional

from core.base_generator import BaseGenerator
from core.config import MapBasicConfig
from core.enums import AlgorithmTypeEnum
from core.grid_random import GridRandomGenerator


class GeneratorFactory:
    """生成器工厂类。"""

    @staticmethod
    def create_generator(
        algorithm_type: AlgorithmTypeEnum,
        config: Optional[MapBasicConfig] = None,
    ) -> BaseGenerator:
        """
        根据算法类型创建对应的生成器实例。

        Args:
            algorithm_type: 算法类型枚举值
            config: 地图生成配置

        Returns:
            对应算法的生成器实例。

        Raises:
            ValueError: 不支持的算法类型。
        """
        if algorithm_type == AlgorithmTypeEnum.GridRandom:
            return GridRandomGenerator(config)
        # 后续可扩展其他算法
        # elif algorithm_type == AlgorithmTypeEnum.RoomSplit:
        #     return RoomSplitGenerator(config)
        # elif algorithm_type == AlgorithmTypeEnum.RecursiveBacktrack:
        #     return RecursiveBacktrackGenerator(config)
        # elif algorithm_type == AlgorithmTypeEnum.PerlinNoise:
        #     return PerlinNoiseGenerator(config)
        else:
            raise ValueError(f"不支持的算法类型: {algorithm_type}")
