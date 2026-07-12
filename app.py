"""
种子管理器 SeedManager

功能：
- 自动生成随机种子（6-16位数字/字符串）
- 手动设置种子（数字 1-999999999，字符串 1-32 位字母数字）
- 种子保存与读取
- 相同种子 + 相同配置可生成 100% 一致的关卡
"""

import random
import string
import json
import os
from typing import Optional, Union


class SeedManager:
    """种子管理器，负责种子的生成、设置、保存与读取。"""

    # 种子持久化文件路径
    _PERSIST_FILE = "seed_data.json"

    def __init__(self):
        self._seed: Optional[Union[int, str]] = None
        self._history: list = []

    # ──────────────────────────────────────────────
    # 种子生成
    # ──────────────────────────────────────────────

    @staticmethod
    def generate_random_seed(length: int = 8) -> str:
        """生成一个随机种子（字母+数字组合）。

        Args:
            length: 种子长度，范围 6-16，默认 8。

        Returns:
            随机生成的字符串种子。
        """
        length = max(6, min(16, length))
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=length))

    @staticmethod
    def generate_numeric_seed(length: int = 6) -> int:
        """生成一个纯数字随机种子。

        Args:
            length: 数字位数，范围 6-16，默认 6。

        Returns:
            随机生成的数字种子。
        """
        length = max(6, min(16, length))
        lower = 10 ** (length - 1)
        upper = 10**length - 1
        return random.randint(lower, upper)

    # ──────────────────────────────────────────────
    # 种子设置
    # ──────────────────────────────────────────────

    def set_seed(self, seed: Optional[Union[str, int]] = None) -> "SeedManager":
        """设置种子。

        规则：
        - 数字类型：范围 [1, 999999999]
        - 字符串类型：长度 [1, 32]，仅允许大小写字母+数字，特殊字符自动过滤
        - 入参为 None：自动生成 8 位随机字符串种子

        Args:
            seed: 种子值。

        Returns:
            self，支持链式调用。

        Raises:
            ValueError: 种子不符合规则时抛出。
        """
        if seed is None:
            self._seed = self.generate_random_seed()
            return self

        if isinstance(seed, int):
            if seed < 1 or seed > 999999999:
                raise ValueError(
                    f"数字种子必须在 [1, 999999999] 范围内，收到: {seed}"
                )
            self._seed = seed
            return self

        if isinstance(seed, str):
            # 过滤特殊字符，仅保留字母和数字
            filtered = "".join(ch for ch in seed if ch.isalnum())
            if len(filtered) < 1:
                raise ValueError("字符串种子过滤后为空，请提供至少一个字母或数字")
            if len(filtered) > 32:
                filtered = filtered[:32]
            self._seed = filtered
            return self

        raise TypeError(f"不支持的种子类型: {type(seed)}")

    # ──────────────────────────────────────────────
    # 种子获取
    # ──────────────────────────────────────────────

    def get_seed(self) -> Optional[Union[int, str]]:
        """获取当前种子。

        Returns:
            当前种子值，未设置时返回 None。
        """
        return self._seed

    def get_seed_str(self) -> str:
        """获取当前种子的字符串表示。

        Returns:
            种子字符串，未设置时返回空字符串。
        """
        if self._seed is None:
            return ""
        return str(self._seed)

    # ──────────────────────────────────────────────
    # 种子持久化（保存与读取）
    # ──────────────────────────────────────────────

    def save(self, filepath: Optional[str] = None) -> str:
        """保存当前种子到文件。

        Args:
            filepath: 保存路径，默认为 'seed_data.json'。

        Returns:
            实际保存的文件路径。
        """
        if self._seed is None:
            raise RuntimeError("当前种子未设置，无法保存")

        path = filepath or self._PERSIST_FILE
        data = {
            "seed": self._seed,
            "seed_type": "int" if isinstance(self._seed, int) else "str",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def load(self, filepath: Optional[str] = None) -> "SeedManager":
        """从文件加载种子。

        Args:
            filepath: 加载路径，默认为 'seed_data.json'。

        Returns:
            self，支持链式调用。

        Raises:
            FileNotFoundError: 文件不存在时抛出。
            ValueError: 文件格式错误时抛出。
        """
        path = filepath or self._PERSIST_FILE
        if not os.path.exists(path):
            raise FileNotFoundError(f"种子文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        seed_type = data.get("seed_type", "int")
        seed = data["seed"]

        if seed_type == "int":
            self._seed = int(seed)
        else:
            self._seed = str(seed)

        return self

    # ──────────────────────────────────────────────
    # 历史记录
    # ──────────────────────────────────────────────

    def push_history(self) -> "SeedManager":
        """将当前种子压入历史记录。

        Returns:
            self，支持链式调用。
        """
        if self._seed is not None and self._seed not in self._history:
            self._history.append(self._seed)
        return self

    def get_history(self) -> list:
        """获取历史种子列表。

        Returns:
            历史种子列表。
        """
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
