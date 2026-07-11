"""
种子管理器模块。

负责种子的标准化处理，确保确定性复现。
规则：
- int 种子范围：1 ~ 999999999
- str 种子：长度 1~32，仅字母数字，非法字符自动清洗
- 非法种子：自动生成 6 位随机数字兜底
- 所有随机行为统一绑定同一个种子，保证全局确定性
- 字符串种子统一 hash 转为整数种子
"""

import random
import hashlib
import re
from typing import Optional, Union


class SeedManager:
    """种子管理器，统一管理随机种子，保证确定性复现。"""

    MIN_INT_SEED = 1
    MAX_INT_SEED = 999999999
    MAX_STR_LEN = 32
    MIN_STR_LEN = 1

    def __init__(self, seed: Optional[Union[int, str]] = None):
        """
        初始化种子管理器。

        Args:
            seed: 可选，种子值（int 或 str）。为 None 时自动生成。
        """
        self._raw_seed: Optional[Union[int, str]] = None
        self._int_seed: int = 0
        self._random_state: Optional[random.Random] = None
        self.reset(seed)

    def reset(self, seed: Optional[Union[int, str]] = None) -> None:
        """
        重置种子，重新绑定随机状态。

        Args:
            seed: 可选，新的种子值。
        """
        self._raw_seed = seed
        self._int_seed = self._normalize_seed(seed)
        self._random_state = random.Random(self._int_seed)

    def _normalize_seed(self, seed: Optional[Union[int, str]]) -> int:
        """
        将种子标准化为整数种子。

        Args:
            seed: 原始种子值。

        Returns:
            标准化后的整数种子。
        """
        if seed is None:
            return self._generate_fallback_seed()

        if isinstance(seed, int):
            return self._normalize_int_seed(seed)

        if isinstance(seed, str):
            return self._normalize_str_seed(seed)

        return self._generate_fallback_seed()

    def _normalize_int_seed(self, seed: int) -> int:
        """
        标准化整数种子。

        Args:
            seed: 整数种子。

        Returns:
            合法范围内的整数种子。
        """
        if self.MIN_INT_SEED <= seed <= self.MAX_INT_SEED:
            return seed
        return self._generate_fallback_seed()

    def _normalize_str_seed(self, seed: str) -> int:
        """
        标准化字符串种子：清洗非法字符后 hash 转为整数。

        Args:
            seed: 字符串种子。

        Returns:
            hash 后的整数种子。
        """
        # 清洗：仅保留字母数字
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', seed)

        # 长度校验
        if len(cleaned) < self.MIN_STR_LEN or len(cleaned) > self.MAX_STR_LEN:
            return self._generate_fallback_seed()

        # 使用 hashlib 将字符串 hash 为整数，并映射到合法范围
        hash_bytes = hashlib.sha256(cleaned.encode('utf-8')).digest()
        hash_int = int.from_bytes(hash_bytes[:8], byteorder='big')
        return (hash_int % (self.MAX_INT_SEED - self.MIN_INT_SEED + 1)) + self.MIN_INT_SEED

    @staticmethod
    def _generate_fallback_seed() -> int:
        """
        生成兜底种子：6 位随机数字。

        Returns:
            6 位随机整数种子。
        """
        # 使用系统随机生成 6 位数字（100000 ~ 999999）
        fallback = random.randint(100000, 999999)
        return fallback

    @property
    def int_seed(self) -> int:
        """获取标准化后的整数种子。"""
        return self._int_seed

    @property
    def raw_seed(self) -> Optional[Union[int, str]]:
        """获取原始种子值。"""
        return self._raw_seed

    @property
    def random(self) -> random.Random:
        """获取绑定种子的随机数生成器。"""
        if self._random_state is None:
            self._random_state = random.Random(self._int_seed)
        return self._random_state

    def get_state(self) -> dict:
        """获取当前种子状态（用于序列化保存）。"""
        return {
            "raw_seed": self._raw_seed,
            "int_seed": self._int_seed,
        }

    @classmethod
    def from_state(cls, state: dict) -> "SeedManager":
        """从状态字典恢复种子管理器。"""
        instance = cls(seed=state.get("raw_seed"))
        return instance
