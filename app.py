"""
网格随机算法 (GridRandom)
适用：小型闯关、小游戏地图
逻辑：根据 wallRatio / trapMaxRatio 逐地块随机生成，保证基础通路，最后 BFS 校验通路。
"""

import random
from typing import List, Tuple, Optional
from collections import deque


class GridRandomGenerator:
    """网格随机地图生成器"""

    TILE_EMPTY = 0  # 空地
    TILE_WALL = 1   # 障碍物
    TILE_TRAP = 2   # 陷阱
    TILE_RESOURCE = 3  # 资源

    def __init__(self, seed: Optional[int] = None):
        """
        初始化生成器
        Args:
            seed: 随机种子，用于确定性复现。None 则使用系统随机。
        """
        if seed is not None:
            self.seed = self._normalize_seed(seed)
            random.seed(self.seed)
        else:
            self.seed = None

    @staticmethod
    def _normalize_seed(seed: int) -> int:
        """标准化种子，确保在合法范围内"""
        if not isinstance(seed, int):
            raise TypeError(f"种子必须是整数，收到 {type(seed).__name__}")
        if seed < 1 or seed > 999999999:
            raise ValueError(f"种子范围: 1 ~ 999999999，收到 {seed}")
        return seed

    def generate(
        self,
        width: int,
        height: int,
        wall_ratio: float = 0.3,
        trap_max_ratio: float = 0.1,
        resource_ratio: float = 0.05,
        ensure_path: bool = True,
    ) -> Tuple[List[List[int]], Tuple[int, int], Tuple[int, int], List[Tuple[int, int]]]:
        """
        生成网格随机地图

        Args:
            width: 地图宽度（列数）
            height: 地图高度（行数）
            wall_ratio: 障碍物比例 (0.0 ~ 1.0)
            trap_max_ratio: 陷阱最大比例 (0.0 ~ 1.0)
            resource_ratio: 资源比例 (0.0 ~ 1.0)
            ensure_path: 是否确保起点到终点有通路

        Returns:
            tile_map: 二维网格地图 (height x width)
            start: 起点坐标 (row, col)
            end: 终点坐标 (row, col)
            room_list: 空地格子列表
        """
        # 参数校验
        if width < 3 or height < 3:
            raise ValueError(f"地图尺寸至少为 3x3，收到 {width}x{height}")
        if not (0.0 <= wall_ratio <= 1.0):
            raise ValueError(f"wall_ratio 必须在 [0, 1] 范围内，收到 {wall_ratio}")
        if not (0.0 <= trap_max_ratio <= 1.0):
            raise ValueError(f"trap_max_ratio 必须在 [0, 1] 范围内，收到 {trap_max_ratio}")
        if not (0.0 <= resource_ratio <= 1.0):
            raise ValueError(f"resource_ratio 必须在 [0, 1] 范围内，收到 {resource_ratio}")

        total_cells = width * height

        # 计算各类格子数量
        wall_count = int(total_cells * wall_ratio)
        trap_count = int(total_cells * trap_max_ratio)
        resource_count = int(total_cells * resource_ratio)

        # 初始化全空地地图
        tile_map = [[self.TILE_EMPTY for _ in range(width)] for _ in range(height)]

        # 收集所有格子坐标
        all_positions = [(r, c) for r in range(height) for c in range(width)]

        # 随机打乱
        random.shuffle(all_positions)

        # 放置障碍物
        idx = 0
        for _ in range(wall_count):
            r, c = all_positions[idx]
            tile_map[r][c] = self.TILE_WALL
            idx += 1

        # 放置陷阱
        for _ in range(trap_count):
            r, c = all_positions[idx]
            tile_map[r][c] = self.TILE_TRAP
            idx += 1

        # 放置资源
        for _ in range(resource_count):
            r, c = all_positions[idx]
            tile_map[r][c] = self.TILE_RESOURCE
            idx += 1

        # 确定起点（左上角空地）和终点（右下角空地）
        start = self._find_start(tile_map)
        end = self._find_end(tile_map)

        # 如果起点或终点是障碍物，强制设为空地
        if tile_map[start[0]][start[1]] == self.TILE_WALL:
            tile_map[start[0]][start[1]] = self.TILE_EMPTY
        if tile_map[end[0]][end[1]] == self.TILE_WALL:
            tile_map[end[0]][end[1]] = self.TILE_EMPTY

        # BFS 校验通路
        if ensure_path:
            path_exists = self._bfs_check(tile_map, start, end)
            if not path_exists:
                # 如果无通路，尝试打通一条路径
                self._carve_path(tile_map, start, end)

        # 收集空地格子列表
        room_list = [
            (r, c)
            for r in range(height)
            for c in range(width)
            if tile_map[r][c] != self.TILE_WALL
        ]

        return tile_map, start, end, room_list

    def _find_start(self, tile_map: List[List[int]]) -> Tuple[int, int]:
        """找到起点（左上角区域）"""
        height = len(tile_map)
        width = len(tile_map[0])
        # 从左上角开始找空地
        for r in range(height):
            for c in range(width):
                if tile_map[r][c] != self.TILE_WALL:
                    return (r, c)
        return (0, 0)

    def _find_end(self, tile_map: List[List[int]]) -> Tuple[int, int]:
        """找到终点（右下角区域）"""
        height = len(tile_map)
        width = len(tile_map[0])
        # 从右下角开始找空地
        for r in range(height - 1, -1, -1):
            for c in range(width - 1, -1, -1):
                if tile_map[r][c] != self.TILE_WALL:
                    return (r, c)
        return (height - 1, width - 1)

    def _bfs_check(
        self,
        tile_map: List[List[int]],
        start: Tuple[int, int],
        end: Tuple[int, int],
    ) -> bool:
        """BFS 检查起点到终点是否有通路"""
        height = len(tile_map)
        width = len(tile_map[0])
        visited = [[False] * width for _ in range(height)]
        queue = deque([start])
        visited[start[0]][start[1]] = True

        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        while queue:
            r, c = queue.popleft()
            if (r, c) == end:
                return True
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < height and 0 <= nc < width:
                    if not visited[nr][nc] and tile_map[nr][nc] != self.TILE_WALL:
                        visited[nr][nc] = True
                        queue.append((nr, nc))
        return False

    def _carve_path(
        self,
        tile_map: List[List[int]],
        start: Tuple[int, int],
        end: Tuple[int, int],
    ) -> None:
        """打通一条从起点到终点的路径（简单直线+随机偏移）"""
        height = len(tile_map)
        width = len(tile_map[0])
        r1, c1 = start
        r2, c2 = end

        # 先水平方向打通
        step_c = 1 if c2 >= c1 else -1
        for c in range(c1, c2 + step_c, step_c):
            if tile_map[r1][c] == self.TILE_WALL:
                tile_map[r1][c] = self.TILE_EMPTY

        # 再垂直方向打通
        step_r = 1 if r2 >= r1 else -1
        for r in range(r1, r2 + step_r, step_r):
            if tile_map[r][c2] == self.TILE_WALL:
                tile_map[r][c2] = self.TILE_EMPTY
