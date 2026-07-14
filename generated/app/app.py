"""
种子管理器 (SeedManager)
提供种子的生成、存储、检索和重置等核心功能。
"""

import json
import random
import string
from typing import Any, Optional, Union


class SeedManager:
    """种子管理器，管理随机种子的生成、存储与重置。

    支持数字种子（任何整数）和字符串种子（1~32 位字母数字）。
    非法种子会自动生成 6 位随机数字兜底。
    所有随机行为统一绑定同一个种子，保证全局确定性。
    """

    # 常量定义
    MIN_INT_SEED = 1
    MAX_INT_SEED = 999999999
    MAX_STR_SEED_LENGTH = 32
    DEFAULT_RANDOM_LENGTH = 8
    DEFAULT_NUMERIC_LENGTH = 6
    MAX_RANDOM_LENGTH = 32
    MAX_NUMERIC_LENGTH = 16
    FALLBACK_LENGTH = 6

    def __init__(self, seed: Any = None) -> None:
        """初始化种子管理器。

        Args:
            seed: 初始种子值。为 None 时自动生成 6 位数字种子。
        """
        self._seed: Optional[Union[int, str]] = None
        self._history: list[Union[int, str]] = []
        self._initial_seed: Optional[Union[int, str]] = None
        self._random: random.Random = random.Random()

        if seed is not None:
            self.set_seed(seed)
            self._initial_seed = self._seed
        else:
            # 默认自动生成种子
            self._seed = self.generate_numeric_seed(self.FALLBACK_LENGTH)
            self._initial_seed = self._seed
            self._random.seed(str(self._seed))

    # ──────────────────────────────────────────────
    # 公开属性
    # ──────────────────────────────────────────────

    @property
    def seed(self) -> Optional[Union[int, str]]:
        """获取当前种子值。"""
        return self._seed

    @seed.setter
    def seed(self, value: Any) -> None:
        """设置种子值，委托给 set_seed。"""
        self.set_seed(value)

    def get_seed(self) -> Optional[Union[int, str]]:
        """获取当前种子值。"""
        return self._seed

    def get_seed_str(self) -> str:
        """获取当前种子的字符串表示。

        Returns:
            种子为 None 时返回空字符串，否则返回 str(seed)。
        """
        if self._seed is None:
            return ""
        return str(self._seed)

    def get_history(self) -> list[Union[int, str]]:
        """获取历史记录副本。"""
        return list(self._history)

    # ──────────────────────────────────────────────
    # 种子生成
    # ──────────────────────────────────────────────

    def generate_random_seed(self, length: int = DEFAULT_RANDOM_LENGTH) -> str:
        """生成随机字母数字种子。

        Args:
            length: 种子长度，范围 1~32，超出自动修正。

        Returns:
            由字母和数字组成的随机字符串。
        """
        length = self._clamp(length, 1, self.MAX_RANDOM_LENGTH)
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    def generate_numeric_seed(self, length: int = DEFAULT_NUMERIC_LENGTH) -> str:
        """生成随机数字种子。

        Args:
            length: 种子长度，范围 1~16，超出自动修正。

        Returns:
            由数字组成的随机字符串。
        """
        length = self._clamp(length, 1, self.MAX_NUMERIC_LENGTH)
        return "".join(random.choice(string.digits) for _ in range(length))

    # ──────────────────────────────────────────────
    # 种子设置
    # ──────────────────────────────────────────────

    def set_seed(self, seed: Any) -> "SeedManager":
        """设置种子值。

        支持的类型和规则：
        - int: 范围 1 ~ 999999999，超出抛出 ValueError
        - str: 长度 1~32，仅保留字母数字，非法字符自动清洗。
                清洗后为空或超长时自动兜底生成 6 位数字种子。
        - None / "": 自动生成 6 位数字种子兜底
        - 其他类型: 抛出 TypeError

        Args:
            seed: 种子值。

        Returns:
            self，支持链式调用。

        Raises:
            TypeError: 不支持的种子类型。
            ValueError: 数字种子超出范围。
        """
        if seed is None or seed == "":
            self._seed = self.generate_numeric_seed(self.FALLBACK_LENGTH)
            self._random.seed(str(self._seed))
            return self

        if isinstance(seed, bool):
            raise TypeError(f"不支持的种子类型: bool")

        if isinstance(seed, int):
            self._seed = seed
            self._random.seed(seed)
            return self

        if isinstance(seed, str):
            # 清洗：只保留字母和数字
            cleaned = "".join(ch for ch in seed if ch.isalnum())

            # 如果清洗后为空，自动生成兜底
            if not cleaned:
                self._seed = self.generate_numeric_seed(self.FALLBACK_LENGTH)
                self._random.seed(str(self._seed))
                return self

            # 截断到最大长度
            if len(cleaned) > self.MAX_STR_SEED_LENGTH:
                cleaned = cleaned[: self.MAX_STR_SEED_LENGTH]

            self._seed = cleaned
            self._random.seed(str(self._seed))
            return self

        raise TypeError(f"不支持的种子类型: {type(seed).__name__}")

    # ──────────────────────────────────────────────
    # 历史记录
    # ──────────────────────────────────────────────

    def push_history(self) -> "SeedManager":
        """将当前种子压入历史记录。

        如果当前种子为 None，则不执行任何操作。
        """
        if self._seed is not None:
            self._history.append(self._seed)
        return self

    def clear_history(self) -> "SeedManager":
        """清空历史记录。"""
        self._history.clear()
        return self

    # ──────────────────────────────────────────────
    # 重置
    # ──────────────────────────────────────────────

    def reset(self) -> "SeedManager":
        """重置管理器：恢复到初始种子，清空历史记录。"""
        self._history.clear()
        if self._initial_seed is not None:
            self._seed = self._initial_seed
            self._random.seed(str(self._seed))
        else:
            self._seed = None
        return self

    # ──────────────────────────────────────────────
    # 状态管理
    # ──────────────────────────────────────────────

    def get_state(self) -> random.Random:
        """获取当前随机状态对象。

        Returns:
            当前 random.Random 对象。
        """
        return self._random

    def set_state(self, state: random.Random) -> "SeedManager":
        """设置随机状态对象。

        Args:
            state: random.Random 对象。

        Returns:
            self，支持链式调用。
        """
        self._random = state
        return self

    # ──────────────────────────────────────────────
    # 随机方法
    # ──────────────────────────────────────────────

    def randint(self, a: int, b: int) -> int:
        """返回 [a, b] 范围内的随机整数。

        Args:
            a: 下限。
            b: 上限。

        Returns:
            [a, b] 范围内的随机整数。

        Raises:
            TypeError: 参数不是整数。
            ValueError: a > b。
        """
        return self._random.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """返回 [a, b) 范围内的随机浮点数。

        Args:
            a: 下限。
            b: 上限。

        Returns:
            [a, b) 范围内的随机浮点数。
        """
        return self._random.uniform(a, b)

    def choice(self, seq: Any) -> Any:
        """从非空序列中随机选取一个元素。

        Args:
            seq: 非空序列。

        Returns:
            序列中的随机元素。

        Raises:
            IndexError: 序列为空。
        """
        return self._random.choice(seq)

    def shuffle(self, x: list) -> None:
        """就地打乱序列。

        Args:
            x: 列表。

        Raises:
            TypeError: 参数不是列表。
        """
        self._random.shuffle(x)

    def sample(self, population: list, k: int) -> list:
        """从总体中随机抽取 k 个不重复元素。

        Args:
            population: 总体列表。
            k: 抽取数量。

        Returns:
            包含 k 个不重复元素的列表。

        Raises:
            ValueError: k > len(population) 或 k < 0。
        """
        return self._random.sample(population, k)

    def random(self) -> float:
        """返回 [0.0, 1.0) 范围内的随机浮点数。

        Returns:
            [0.0, 1.0) 范围内的随机浮点数。
        """
        return self._random.random()

    # ──────────────────────────────────────────────
    # 保存与加载
    # ──────────────────────────────────────────────

    def save(self, filepath: str) -> "SeedManager":
        """将当前种子保存到 JSON 文件。

        Args:
            filepath: 文件路径。

        Returns:
            self，支持链式调用。
        """
        data = {"seed": self._seed}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return self

    def load(self, filepath: str) -> "SeedManager":
        """从 JSON 文件加载种子。

        Args:
            filepath: 文件路径。

        Returns:
            self，支持链式调用。

        Raises:
            FileNotFoundError: 文件不存在。
            json.JSONDecodeError: 文件内容损坏。
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._seed = data.get("seed")
        if self._seed is not None:
            self._random.seed(str(self._seed))
        return self

    # ──────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────

    @staticmethod
    def _clamp(value: int, low: int, high: int) -> int:
        """将值限制在 [low, high] 范围内。"""
        if value < low:
            return low
        if value > high:
            return high
        return value

    # ──────────────────────────────────────────────
    # 特殊方法
    # ──────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SeedManager(seed={self._seed}, "
            f"history_count={len(self._history)})"
        )
