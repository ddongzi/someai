"""
种子管理器 (SeedManager)
实现种子管理、基础四套生成算法、简单参数配置、基础地形生成、基础校验、数据导出功能。
"""

import random
import string
import json
import copy
from typing import Optional, Union, Any


class SeedManager:
    """种子管理器，支持种子设置、地图生成、模板保存加载等完整功能。"""

    # 种子数字边界
    SEED_MIN = 1
    SEED_MAX = 999999999
    # 字符串种子长度边界
    SEED_STR_MIN_LEN = 1
    SEED_STR_MAX_LEN = 32
    # 自动生成种子长度范围
    AUTO_SEED_MIN_LEN = 6
    AUTO_SEED_MAX_LEN = 16

    # 支持的生成算法
    ALGORITHMS = ["GridRandom", "RoomSplit", "RecursiveBacktrack", "PerlinNoise"]

    def __init__(self):
        self._initialized = False
        self._seed: Optional[Union[str, int]] = None
        self._seed_raw: Optional[Union[str, int]] = None  # 原始种子值
        self._config: dict = {}
        self._map_data: Optional[dict] = None
        self._templates: dict = {}

    # ==================== 初始化接口 ====================

    def Init(self) -> dict:
        """初始化组件，完成参数加载和默认种子生成。

        Returns:
            dict: 包含操作结果的字典，格式为 {"success": bool, "message": str}
        """
        if self._initialized:
            return {"success": False, "message": "重复初始化，组件已初始化"}
        self._initialized = True
        self._config = self._default_config()
        self._auto_generate_seed()
        return {"success": True, "message": "初始化成功"}

    @staticmethod
    def _default_config() -> dict:
        """返回默认配置。"""
        return {
            "algorithm": "GridRandom",
            "width": 50,
            "height": 50,
            "room_min_size": 3,
            "room_max_size": 10,
            "wall_thickness": 1,
            "seed_length": 8,
        }

    # ==================== 种子管理 ====================

    def _auto_generate_seed(self) -> None:
        """自动生成随机种子（6-16位随机数字字符串）。"""
        length = random.randint(self.AUTO_SEED_MIN_LEN, self.AUTO_SEED_MAX_LEN)
        seed_str = "".join(random.choices(string.digits, k=length))
        self._seed = seed_str
        self._seed_raw = seed_str

    def SetSeed(self, seed: Optional[Union[str, int]]) -> dict:
        """设置关卡种子。

        参数边界：
        - 数字类型：[1, 999999999]
        - 字符串类型：长度[1,32]，仅允许大小写字母+数字，特殊字符自动过滤并重新生成随机种子
        - 入参为空：自动生成6位数字随机种子

        Args:
            seed: 种子值，可以是数字、字符串或 None。

        Returns:
            dict: {"success": bool, "message": str, "seed": str}
        """
        if not self._initialized:
            return {"success": False, "message": "组件未初始化", "seed": ""}

        # 空值处理
        if seed is None or (isinstance(seed, str) and seed.strip() == ""):
            self._auto_generate_seed()
            return {
                "success": True,
                "message": f"已自动生成随机种子: {self._seed}",
                "seed": str(self._seed),
            }

        # 数字类型处理
        if isinstance(seed, (int, float)):
            if isinstance(seed, float):
                return {"success": False, "message": "种子不能为浮点数", "seed": ""}
            if seed < self.SEED_MIN or seed > self.SEED_MAX:
                return {
                    "success": False,
                    "message": f"数字种子超出范围 [{self.SEED_MIN}, {self.SEED_MAX}]",
                    "seed": "",
                }
            self._seed = seed
            self._seed_raw = seed
            return {"success": True, "message": f"种子设置成功: {seed}", "seed": str(seed)}

        # 字符串类型处理
        if isinstance(seed, str):
            if len(seed) < self.SEED_STR_MIN_LEN or len(seed) > self.SEED_STR_MAX_LEN:
                return {
                    "success": False,
                    "message": f"字符串种子长度超出范围 [{self.SEED_STR_MIN_LEN}, {self.SEED_STR_MAX_LEN}]",
                    "seed": "",
                }
            # 过滤特殊字符：仅允许大小写字母+数字
            filtered = "".join(ch for ch in seed if ch.isalnum())
            if filtered != seed:
                # 包含特殊字符，自动重新生成随机种子
                self._auto_generate_seed()
                return {
                    "success": True,
                    "message": f"种子包含特殊字符，已自动重新生成: {self._seed}",
                    "seed": str(self._seed),
                }
            self._seed = seed
            self._seed_raw = seed
            return {"success": True, "message": f"种子设置成功: {seed}", "seed": seed}

        return {"success": False, "message": f"不支持的种子类型: {type(seed).__name__}", "seed": ""}

    # ==================== 配置管理 ====================

    def SetConfig(self, config: dict) -> dict:
        """设置生成参数。

        Args:
            config: 配置字典，支持部分配置。

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self._initialized:
            return {"success": False, "message": "组件未初始化"}

        if not isinstance(config, dict):
            return {"success": False, "message": "配置必须为字典类型"}

        if not config:
            return {"success": False, "message": "配置为空"}

        valid_keys = set(self._default_config().keys())
        for key in config:
            if key not in valid_keys:
                return {"success": False, "message": f"无效配置键: {key}"}

        self._config.update(config)
        return {"success": True, "message": "配置更新成功"}

    def GetConfig(self) -> dict:
        """获取当前配置的深拷贝。"""
        return copy.deepcopy(self._config)

    # ==================== 地图生成 ====================

    def GenerateMap(self) -> dict:
        """执行地图生成。

        根据当前配置的算法和种子，生成地图数据。

        Returns:
            dict: {"success": bool, "message": str, "data": dict|None}
        """
        if not self._initialized:
            return {"success": False, "message": "组件未初始化", "data": None}

        algorithm = self._config.get("algorithm", "GridRandom")
        if algorithm not in self.ALGORITHMS:
            return {"success": False, "message": f"不支持的算法: {algorithm}", "data": None}

        # 用种子初始化随机数生成器，保证相同种子生成相同地图
        seed_value = self._seed
        if seed_value is None:
            self._auto_generate_seed()
            seed_value = self._seed

        rng = random.Random(str(seed_value))

        width = self._config.get("width", 50)
        height = self._config.get("height", 50)

        try:
            if algorithm == "GridRandom":
                map_data = self._generate_grid_random(rng, width, height)
            elif algorithm == "RoomSplit":
                map_data = self._generate_room_split(rng, width, height)
            elif algorithm == "RecursiveBacktrack":
                map_data = self._generate_recursive_backtrack(rng, width, height)
            elif algorithm == "PerlinNoise":
                map_data = self._generate_perlin_noise(rng, width, height)
            else:
                return {"success": False, "message": f"未知算法: {algorithm}", "data": None}

            self._map_data = {
                "grid": map_data,
                "width": width,
                "height": height,
                "algorithm": algorithm,
                "seed": str(seed_value),
            }
            return {"success": True, "message": f"地图生成成功，算法: {algorithm}", "data": self._map_data}
        except Exception as e:
            return {"success": False, "message": f"地图生成失败: {str(e)}", "data": None}

    def _generate_grid_random(self, rng: random.Random, width: int, height: int) -> list:
        """GridRandom 算法：随机填充网格，0=空地，1=墙壁。"""
        grid = [[0 for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                grid[y][x] = 1 if rng.random() < 0.4 else 0
        return grid

    def _generate_room_split(self, rng: random.Random, width: int, height: int) -> list:
        """RoomSplit 算法：递归分割生成房间。"""
        grid = [[1 for _ in range(width)] for _ in range(height)]

        def carve_room(x1, y1, x2, y2):
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if 0 <= y < height and 0 <= x < width:
                        grid[y][x] = 0

        def split(x1, y1, x2, y2, depth=0):
            if depth > 5:
                carve_room(x1, y1, x2, y2)
                return
            w, h = x2 - x1, y2 - y1
            if w < 6 or h < 6:
                carve_room(x1, y1, x2, y2)
                return

            if w > h:
                split_x = rng.randint(x1 + 3, x2 - 3)
                split(x1, y1, split_x, y2, depth + 1)
                split(split_x + 1, y1, x2, y2, depth + 1)
                # 开门洞
                door_y = rng.randint(y1, y2)
                if 0 <= door_y < height and 0 <= split_x < width:
                    grid[door_y][split_x] = 0
            else:
                split_y = rng.randint(y1 + 3, y2 - 3)
                split(x1, y1, x2, split_y, depth + 1)
                split(x1, split_y + 1, x2, y2, depth + 1)
                # 开门洞
                door_x = rng.randint(x1, x2)
                if 0 <= split_y < height and 0 <= door_x < width:
                    grid[split_y][door_x] = 0

        split(0, 0, width - 1, height - 1)
        return grid

    def _generate_recursive_backtrack(self, rng: random.Random, width: int, height: int) -> list:
        """RecursiveBacktrack 算法：递归回溯生成迷宫。"""
        # 确保宽高为奇数
        if width % 2 == 0:
            width -= 1
        if height % 2 == 0:
            height -= 1
        if width < 3:
            width = 3
        if height < 3:
            height = 3

        grid = [[1 for _ in range(width)] for _ in range(height)]

        def carve(x, y):
            grid[y][x] = 0
            dirs = [(0, 2), (0, -2), (2, 0), (-2, 0)]
            rng.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] == 1:
                    grid[y + dy // 2][x + dx // 2] = 0
                    carve(nx, ny)

        carve(0, 0)
        return grid

    def _generate_perlin_noise(self, rng: random.Random, width: int, height: int) -> list:
        """PerlinNoise 算法：简化噪声生成地形。"""
        grid = [[0 for _ in range(width)] for _ in range(height)]

        # 生成随机梯度
        grad = {}
        step = 8
        for y in range(0, height + step, step):
            for x in range(0, width + step, step):
                angle = rng.random() * 2 * 3.14159265
                grad[(x, y)] = (rng.random(), rng.random())

        def dot_grid(ix, iy, x, y):
            dx = x - ix
            dy = y - iy
            gx, gy = grad.get((ix, iy), (0, 0))
            return dx * gx + dy * gy

        def lerp(a, b, t):
            return a + t * (b - a)

        def smoothstep(t):
            return t * t * (3 - 2 * t)

        for y in range(height):
            for x in range(width):
                x0 = (x // step) * step
                y0 = (y // step) * step
                x1 = x0 + step
                y1 = y0 + step

                sx = smoothstep((x - x0) / step) if step > 0 else 0
                sy = smoothstep((y - y0) / step) if step > 0 else 0

                n0 = dot_grid(x0, y0, x, y)
                n1 = dot_grid(x1, y0, x, y)
                ix0 = lerp(n0, n1, sx)

                n0 = dot_grid(x0, y1, x, y)
                n1 = dot_grid(x1, y1, x, y)
                ix1 = lerp(n0, n1, sx)

                val = lerp(ix0, ix1, sy)
                grid[y][x] = 1 if val > 0 else 0

        return grid

    # ==================== 数据获取 ====================

    def GetMapData(self) -> Optional[dict]:
        """获取生成后的地图全量数据。

        Returns:
            dict|None: 地图数据字典，如果未生成则返回 None。
        """
        if not self._initialized:
            return None
        return copy.deepcopy(self._map_data)

    # ==================== 模板管理 ====================

    def SaveTemplate(self, name: str) -> dict:
        """保存当前配置为模板。

        Args:
            name: 模板名称。

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self._initialized:
            return {"success": False, "message": "组件未初始化"}
        if not name or not isinstance(name, str):
            return {"success": False, "message": "模板名称无效"}
        self._templates[name] = copy.deepcopy(self._config)
        return {"success": True, "message": f"模板 '{name}' 保存成功"}

    def LoadTemplate(self, name: str) -> dict:
        """加载已保存的模板配置。

        Args:
            name: 模板名称。

        Returns:
            dict: {"success": bool, "message": str, "config": dict|None}
        """
        if not self._initialized:
            return {"success": False, "message": "组件未初始化", "config": None}
        if name not in self._templates:
            return {"success": False, "message": f"模板 '{name}' 不存在", "config": None}
        self._config = copy.deepcopy(self._templates[name])
        return {"success": True, "message": f"模板 '{name}' 加载成功", "config": self.GetConfig()}

    def ListTemplates(self) -> list:
        """列出所有已保存的模板名称。"""
        return list(self._templates.keys())

    # ==================== 状态查询 ====================

    def GetSeed(self) -> Optional[str]:
        """获取当前种子值。"""
        return str(self._seed) if self._seed is not None else None

    def IsInitialized(self) -> bool:
        """检查组件是否已初始化。"""
        return self._initialized
