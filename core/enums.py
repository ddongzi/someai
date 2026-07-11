"""
枚举类型定义模块。

包含算法类型、地块类型、房间类型、日志级别等枚举。
"""

from enum import StrEnum, IntEnum


class LogLevelEnum(StrEnum):
    """日志级别枚举"""
    debug = "debug"
    info = "info"
    warn = "warn"
    error = "error"


class AlgorithmTypeEnum(StrEnum):
    """算法类型枚举"""
    GridRandom = "GridRandom"
    RoomSplit = "RoomSplit"
    RecursiveBacktrack = "RecursiveBacktrack"
    PerlinNoise = "PerlinNoise"


class RoomTypeEnum(StrEnum):
    """房间类型枚举"""
    battle = "battle"
    treasure = "treasure"
    rest = "rest"
    boss = "boss"


class TileType(IntEnum):
    """地块类型枚举"""
    GROUND = 0       # 空地/可通行
    WALL = 1         # 墙壁/障碍物
    WATER = 2        # 水域
    TRAP_TILE = 3    # 陷阱地块
