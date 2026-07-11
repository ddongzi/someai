"""
配置模型模块。

使用 Pydantic 2.x 定义地图生成所需的全部配置参数，包含强校验规则。
"""

from pydantic import BaseModel, Field
from typing import Optional, Union


class MapBasicConfig(BaseModel):
    """地图基础配置模型。"""

    # 地图尺寸
    width: int = Field(default=50, ge=10, le=1000, description="地图宽度")
    height: int = Field(default=50, ge=10, le=1000, description="地图高度")

    # 随机尺寸
    is_random_size: bool = Field(default=False, description="是否随机生成地图尺寸")
    width_range: list[int] = Field(
        default=[20, 100], min_length=2, max_length=2,
        description="宽度随机范围 [min, max]"
    )
    height_range: list[int] = Field(
        default=[20, 100], min_length=2, max_length=2,
        description="高度随机范围 [min, max]"
    )

    # 地块比例
    wall_ratio: int = Field(default=30, ge=0, le=60, description="墙壁占比（百分比）")
    trap_max_ratio: int = Field(default=15, ge=0, le=30, description="陷阱最大占比（百分比）")

    # 房间数量
    room_min_count: int = Field(default=3, ge=1, le=50, description="最小房间数")
    room_max_count: int = Field(default=15, ge=1, le=50, description="最大房间数")

    # 单个房间尺寸
    single_room_min_w: int = Field(default=4, ge=2, le=20, description="房间最小宽度")
    single_room_max_w: int = Field(default=12, ge=4, le=20, description="房间最大宽度")
    single_room_min_h: int = Field(default=4, ge=2, le=20, description="房间最小高度")
    single_room_max_h: int = Field(default=12, ge=4, le=20, description="房间最大高度")

    # 通道宽度
    path_width: int = Field(default=2, ge=1, le=5, description="通道宽度")

    # 难度等级
    difficulty_level: int = Field(default=1, ge=1, le=5, description="难度等级 1-5")

    # 种子
    seed: Optional[Union[int, str]] = Field(default=None, description="随机种子")

    class Config:
        """Pydantic 配置"""
        frozen = False  # 允许修改
        extra = "forbid"  # 禁止额外字段
