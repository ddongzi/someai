"""
网格随机算法模块 (GridRandom)。

适用场景：小型简单关卡、平地闯关、H5小游戏关卡。
核心特性：生成速度快、结构简单，随机生成空地、障碍物、基础资源。

算法逻辑：
1. 根据 wall_ratio / trap_max_ratio 逐地块随机生成
2. 保证基础通路（边界为墙，内部随机）
3. 最后 BFS 校验通路，确保起点到终点可达
4. 若不通则重新生成（有重试上限）
"""

import random
from collections import deque
from typing import Optional

from core.base_generator import BaseGenerator, GenerateResult
from core.config import MapBasicConfig
from core.enums import TileType


class GridRandomGenerator(BaseGenerator):
    """
    网格随机算法生成器。

    逐地块随机生成空地、墙壁、陷阱，保证基础通路，
    最后 BFS 校验起点到终点的连通性。
    """

    # 最大重试次数，杜绝死循环
    MAX_RETRY_COUNT = 100

    def __init__(self, config: Optional[MapBasicConfig] = None):
        """初始化网格随机生成器。"""
        super().__init__(config)
        self._retry_count = 0

    def generate(self) -> GenerateResult:
        """
        执行网格随机地图生成。

        Returns:
            GenerateResult: 包含 tile_map, start, end, room_list 的生成结果。
        """
        self._retry_count = 0

        while self._retry_count < self.MAX_RETRY_COUNT:
            self._retry_count += 1

            # 1. 确定地图尺寸
            width, height = self._determine_size()

            # 2. 初始化地图（全部为墙）
            self._tile_map = self._init_map(width, height)

            # 3. 逐地块随机生成
            self._random_fill(width, height)

            # 4. 确定起点和终点
            self._start, self._end = self._pick_start_end(width, height)

            # 5. BFS 校验通路
            if self._validate_path(self._start, self._end, width, height):
                # 6. 构建房间列表（网格随机算法将整个地图视为一个房间）
                self._room_list = self._build_room_list(width, height)
                return self.get_result()

        # 超过重试次数，生成一个简单可通行的地图作为兜底
        return self._fallback_generate(width, height)

    def _determine_size(self) -> tuple[int, int]:
        """
        确定地图尺寸。

        Returns:
            (width, height) 元组。
        """
        rng = self.seed_manager.random

        if self.config.is_random_size:
            w_min, w_max = self.config.width_range
            h_min, h_max = self.config.height_range
            width = rng.randint(w_min, w_max)
            height = rng.randint(h_min, h_max)
        else:
            width = self.config.width
            height = self.config.height

        return width, height

    def _init_map(self, width: int, height: int) -> list[list[int]]:
        """
        初始化地图，全部填充为墙壁。

        Args:
            width: 地图宽度
            height: 地图高度

        Returns:
            初始化的二维地图矩阵。
        """
        return [[TileType.WALL for _ in range(width)] for _ in range(height)]

    def _random_fill(self, width: int, height: int) -> None:
        """
        逐地块随机生成空地、墙壁、陷阱。

        逻辑：
        - 边界保持为墙
        - 内部区域根据 wall_ratio 生成墙壁，根据 trap_max_ratio 生成陷阱
        - 其余为空地

        Args:
            width: 地图宽度
            height: 地图高度
        """
        rng = self.seed_manager.random
        wall_ratio = self.config.wall_ratio
        trap_max_ratio = self.config.trap_max_ratio

        for row in range(height):
            for col in range(width):
                # 边界保持为墙
                if row == 0 or row == height - 1 or col == 0 or col == width - 1:
                    self._tile_map[row][col] = TileType.WALL
                    continue

                # 内部区域随机生成
                rand_val = rng.randint(1, 100)

                if rand_val <= wall_ratio:
                    # 生成墙壁
                    self._tile_map[row][col] = TileType.WALL
                elif rand_val <= wall_ratio + trap_max_ratio:
                    # 生成陷阱
                    self._tile_map[row][col] = TileType.TRAP_TILE
                else:
                    # 生成空地
                    self._tile_map[row][col] = TileType.GROUND

    def _pick_start_end(
        self, width: int, height: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        选取起点和终点。

        起点：左上角内部区域第一个空地
        终点：右下角内部区域最后一个空地
        如果找不到合适的空地，则使用边界附近的位置。

        Args:
            width: 地图宽度
            height: 地图高度

        Returns:
            ((start_row, start_col), (end_row, end_col))
        """
        rng = self.seed_manager.random

        # 起点：在左上区域找一个空地
        start_candidates = []
        for row in range(1, max(2, height // 3)):
            for col in range(1, max(2, width // 3)):
                if self._tile_map[row][col] == TileType.GROUND:
                    start_candidates.append((row, col))

        if start_candidates:
            start = rng.choice(start_candidates)
        else:
            # 如果没有空地，强制在左上角生成一个空地作为起点
            start = (1, 1)
            self._tile_map[1][1] = TileType.GROUND

        # 终点：在右下区域找一个空地
        end_candidates = []
        for row in range(min(height - 2, height * 2 // 3), height - 1):
            for col in range(min(width - 2, width * 2 // 3), width - 1):
                if self._tile_map[row][col] == TileType.GROUND:
                    end_candidates.append((row, col))

        if end_candidates:
            end = rng.choice(end_candidates)
        else:
            # 如果没有空地，强制在右下角生成一个空地作为终点
            end = (height - 2, width - 2)
            self._tile_map[height - 2][width - 2] = TileType.GROUND

        return start, end

    def _validate_path(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        width: int,
        height: int,
    ) -> bool:
        """
        使用 BFS 校验起点到终点是否连通（只走空地 GROUND）。

        Args:
            start: 起点坐标 (row, col)
            end: 终点坐标 (row, col)
            width: 地图宽度
            height: 地图高度

        Returns:
            True 如果存在通路，否则 False。
        """
        if self._tile_map[start[0]][start[1]] != TileType.GROUND:
            return False
        if self._tile_map[end[0]][end[1]] != TileType.GROUND:
            return False

        # 四个方向：上、下、左、右
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        visited = [[False] * width for _ in range(height)]
        queue = deque()
        queue.append(start)
        visited[start[0]][start[1]] = True

        while queue:
            row, col = queue.popleft()

            # 到达终点
            if (row, col) == end:
                return True

            for dr, dc in directions:
                nr, nc = row + dr, col + dc

                # 边界检查
                if 0 <= nr < height and 0 <= nc < width:
                    if not visited[nr][nc] and self._tile_map[nr][nc] == TileType.GROUND:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

        return False

    def _build_room_list(
        self, width: int, height: int
    ) -> list[dict]:
        """
        构建房间列表。
        网格随机算法将整个地图视为一个房间。

        Args:
            width: 地图宽度
            height: 地图高度

        Returns:
            房间列表。
        """
        from core.enums import RoomTypeEnum

        return [
            {
                "id": 0,
                "type": RoomTypeEnum.battle.value,
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "start": list(self._start),
                "end": list(self._end),
            }
        ]

    def _fallback_generate(
        self, width: int, height: int
    ) -> GenerateResult:
        """
        兜底生成：当重试次数用尽时，生成一个简单可通行的地图。

        Args:
            width: 地图宽度
            height: 地图高度

        Returns:
            保证可通行的生成结果。
        """
        # 全部初始化为空地
        self._tile_map = [
            [TileType.GROUND for _ in range(width)] for _ in range(height)
        ]

        # 边界设为墙
        for col in range(width):
            self._tile_map[0][col] = TileType.WALL
            self._tile_map[height - 1][col] = TileType.WALL
        for row in range(height):
            self._tile_map[row][0] = TileType.WALL
            self._tile_map[row][width - 1] = TileType.WALL

        # 起点和终点
        self._start = (1, 1)
        self._end = (height - 2, width - 2)

        self._room_list = self._build_room_list(width, height)

        return self.get_result()
