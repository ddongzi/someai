"""
种子管理器 SeedManager

提供种子的生成、设置、获取、持久化及历史记录管理功能。
所有修改方法均支持链式调用。
"""

import json
import random
import string
from typing import Optional, Union


class SeedManager:
    """种子管理器，负责种子的生成、设置、保存与读取。"""

    def __init__(self):
        self._seed: Optional[Union[int, str]] = None
        self._history: list = []

    # ──────────────────────────────────────────────
    # 种子生成
    # ──────────────────────────────────────────────

    def generate_random_seed(self, length: int = 8) -> str:
        """生成一个随机种子（字母+数字组合）。

        Args:
            length: 种子长度，默认 8 位。

        Returns:
            随机生成的字符串种子。
        """
        if length < 1:
            length = 1
        if length > 32:
            length = 32
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=length))

    def generate_numeric_seed(self, length: int = 6) -> str:
        """生成一个纯数字随机种子。

        Args:
            length: 种子长度，默认 6 位。

        Returns:
            纯数字字符串种子。
        """
        if length < 1:
            length = 1
        if length > 16:
            length = 16
        return "".join(random.choices(string.digits, k=length))

    # ──────────────────────────────────────────────
    # 种子设置
    # ──────────────────────────────────────────────

    def set_seed(self, seed: Optional[Union[int, str]] = None) -> "SeedManager":
        """设置种子。

        Args:
            seed: 种子值。
                - 数字类型：范围 [1, 999999999]
                - 字符串类型：长度 [1, 32]，仅允许大小写字母+数字
                - None / 空字符串：自动生成 6 位数字随机种子
                - 含特殊字符的字符串：自动过滤并重新生成随机种子

        Returns:
            self，支持链式调用。

        Raises:
            TypeError: 种子类型不支持（如 float、bool、list、dict 等）。
        """
        # 类型检查
        if seed is not None and not isinstance(seed, (int, str)):
            raise TypeError(
                f"不支持的种子类型: {type(seed).__name__}，仅支持 int 或 str"
            )

        # None / 空字符串 → 自动生成
        if seed is None or (isinstance(seed, str) and seed.strip() == ""):
            self._seed = self.generate_numeric_seed(6)
            return self

        # 字符串处理
        if isinstance(seed, str):
            # 过滤特殊字符
            filtered = "".join(ch for ch in seed if ch.isalnum())
            if len(filtered) == 0:
                # 全是特殊字符 → 重新生成
                self._seed = self.generate_numeric_seed(6)
                return self
            # 截断到 32 位
            self._seed = filtered[:32]
            return self

        # 数字处理
        if isinstance(seed, int):
            if seed < 1 or seed > 999999999:
                raise ValueError(
                    f"数字种子超出范围 [1, 999999999]: {seed}"
                )
            self._seed = seed
            return self

        return self

    # ──────────────────────────────────────────────
    # 种子获取
    # ──────────────────────────────────────────────

    def get_seed(self) -> Optional[Union[int, str]]:
        """获取当前种子。"""
        return self._seed

    def get_seed_str(self) -> str:
        """获取当前种子的字符串表示。"""
        if self._seed is None:
            return ""
        return str(self._seed)

    # ──────────────────────────────────────────────
    # 保存与加载
    # ──────────────────────────────────────────────

    def save(self, filepath: str) -> "SeedManager":
        """保存当前种子到文件。

        Args:
            filepath: 文件路径。

        Returns:
            self，支持链式调用。
        """
        data = {"seed": self._seed}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return self

    def load(self, filepath: str) -> "SeedManager":
        """从文件加载种子。

        Args:
            filepath: 文件路径。

        Returns:
            self，支持链式调用。
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._seed = data["seed"]
        return self

    # ──────────────────────────────────────────────
    # 历史记录
    # ──────────────────────────────────────────────

    def push_history(self) -> "SeedManager":
        """将当前种子压入历史记录。

        Returns:
            self，支持链式调用。
        """
        if self._seed is not None:
            self._history.append(self._seed)
        return self

    def get_history(self) -> list:
        """获取历史种子列表。"""
        return list(self._history)

    def clear_history(self) -> "SeedManager":
        """清空历史记录。

        Returns:
            self，支持链式调用。
        """
        self._history.clear()
        return self

    # ──────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────

    def reset(self) -> "SeedManager":
        """重置种子管理器（清空种子和历史）。

        Returns:
            self，支持链式调用。
        """
        self._seed = None
        self._history.clear()
        return self

    def __repr__(self) -> str:
        return f"SeedManager(seed={self._seed!r}, history_count={len(self._history)})"
