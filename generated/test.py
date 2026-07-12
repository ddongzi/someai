"""
SeedManager 单元测试

覆盖范围：
- 初始化测试
- 种子生成测试（随机种子、数字种子）
- 种子设置参数边界极值测试（数字/字符串/特殊字符/空值）
- 种子一致性回归测试
- 种子确定性/可复现性测试（绑定 random.seed）
- 种子保存与加载测试
- 历史记录测试
- 重置测试
- 非法参数容错测试
- 压测：1000 次连续生成稳定性
- 链式调用测试
- 边界情况综合测试
- 确定性回归测试
- 容错/恢复机制测试
"""

import os
import json
import tempfile
import pytest
import random
import string
from typing import Optional, Union

# ──────────────────────────────────────────────
# 被测试类（直接从 app.py 复制定义）
# ──────────────────────────────────────────────


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


# ================================================================
# 测试代码
# ================================================================


class TestInit:
    """初始化测试"""

    def test_default_init(self):
        """默认初始化后 seed 为 None，历史为空"""
        sm = SeedManager()
        assert sm.get_seed() is None
        assert sm.get_seed_str() == ""
        assert sm.get_history() == []

    def test_re_init(self):
        """多次初始化应互不影响"""
        sm1 = SeedManager()
        sm2 = SeedManager()
        sm1.set_seed(42)
        assert sm1.get_seed() == 42
        assert sm2.get_seed() is None


class TestGenerateSeed:
    """种子生成测试"""

    def test_generate_random_seed_default(self):
        """默认生成 8 位随机字符串种子"""
        sm = SeedManager()
        seed = sm.generate_random_seed()
        assert isinstance(seed, str)
        assert len(seed) == 8
        # 只包含字母和数字
        assert seed.isalnum()

    def test_generate_random_seed_custom_length(self):
        """自定义长度生成随机字符串种子"""
        sm = SeedManager()
        for length in [1, 4, 16, 32]:
            seed = sm.generate_random_seed(length)
            assert isinstance(seed, str)
            assert len(seed) == length
            assert seed.isalnum()

    def test_generate_random_seed_boundary(self):
        """边界长度：0 和 33"""
        sm = SeedManager()
        # 小于 1 时自动设为 1
        seed0 = sm.generate_random_seed(0)
        assert len(seed0) == 1
        # 大于 32 时自动设为 32
        seed33 = sm.generate_random_seed(33)
        assert len(seed33) == 32

    def test_generate_numeric_seed_default(self):
        """默认生成 6 位数字种子"""
        sm = SeedManager()
        seed = sm.generate_numeric_seed()
        assert isinstance(seed, str)
        assert len(seed) == 6
        assert seed.isdigit()

    def test_generate_numeric_seed_custom_length(self):
        """自定义长度生成数字种子"""
        sm = SeedManager()
        for length in [1, 4, 8, 16]:
            seed = sm.generate_numeric_seed(length)
            assert isinstance(seed, str)
            assert len(seed) == length
            assert seed.isdigit()

    def test_generate_numeric_seed_boundary(self):
        """边界长度：0 和 17"""
        sm = SeedManager()
        seed0 = sm.generate_numeric_seed(0)
        assert len(seed0) == 1
        seed17 = sm.generate_numeric_seed(17)
        assert len(seed17) == 16

    def test_generate_randomness(self):
        """多次生成应得到不同结果"""
        sm = SeedManager()
        seeds = {sm.generate_random_seed() for _ in range(100)}
        # 100 次生成几乎不可能全部相同
        assert len(seeds) > 1


class TestSetSeed:
    """种子设置参数边界极值测试"""

    # ── 数字边界 ──

    @pytest.mark.parametrize("seed", [1, 500, 999999999])
    def test_numeric_valid(self, seed):
        """有效数字种子"""
        sm = SeedManager()
        sm.set_seed(seed)
        assert sm.get_seed() == seed
        assert sm.get_seed_str() == str(seed)

    @pytest.mark.parametrize("seed", [0, -1, -100, 1000000000])
    def test_numeric_out_of_range(self, seed):
        """数字种子越界应抛出 ValueError"""
        sm = SeedManager()
        with pytest.raises(ValueError, match="超出范围"):
            sm.set_seed(seed)

    # ── 字符串边界 ──

    @pytest.mark.parametrize(
        "seed,expected_len",
        [
            ("a", 1),
            ("hello", 5),
            ("a" * 32, 32),
            ("HelloWorld123", 13),
            ("1234567890", 10),
        ],
    )
    def test_string_valid(self, seed, expected_len):
        """有效字符串种子"""
        sm = SeedManager()
        sm.set_seed(seed)
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == expected_len
        assert result.isalnum()

    def test_string_too_long_truncated(self):
        """超过 32 位的字符串应被截断到 32 位"""
        sm = SeedManager()
        long_str = "a" * 50
        sm.set_seed(long_str)
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == 32

    # ── 特殊字符 ──

    @pytest.mark.parametrize(
        "seed",
        [
            "@#$%^&*",
            "!@#$%",
            "   ",  # 纯空格
            "\t\n\r",
            "~~~```",
        ],
    )
    def test_special_chars_only(self, seed):
        """纯特殊字符应自动生成 6 位数字随机种子"""
        sm = SeedManager()
        sm.set_seed(seed)
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == 6
        assert result.isdigit()

    @pytest.mark.parametrize(
        "seed,expected_alnum",
        [
            ("abc@#$", "abc"),
            ("hello!world", "helloworld"),
            ("123#456", "123456"),
            ("a@b#c$d", "abcd"),
        ],
    )
    def test_mixed_special_chars(self, seed, expected_alnum):
        """混合特殊字符应过滤，保留字母数字"""
        sm = SeedManager()
        sm.set_seed(seed)
        result = sm.get_seed()
        assert isinstance(result, str)
        assert result == expected_alnum

    # ── 空值测试 ──

    @pytest.mark.parametrize("seed", [None, ""])
    def test_none_or_empty(self, seed):
        """None 或空字符串应自动生成 6 位数字随机种子"""
        sm = SeedManager()
        sm.set_seed(seed)
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == 6
        assert result.isdigit()

    # ── 非法类型 ──

    @pytest.mark.parametrize(
        "seed",
        [
            3.14,
            True,
            False,
            [1, 2, 3],
            {"key": "value"},
            (1, 2),
            {1, 2, 3},
        ],
    )
    def test_invalid_type(self, seed):
        """非法类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError, match="不支持的种子类型"):
            sm.set_seed(seed)


class TestSeedConsistency:
    """种子一致性回归测试"""

    @pytest.mark.parametrize(
        "seed",
        [
            42,
            1,
            999999999,
            123456789,
            "hello",
            "test123",
            "a",
            "A" * 32,
        ],
    )
    def test_seed_consistency(self, seed):
        """相同种子设置后应得到相同值"""
        sm1 = SeedManager()
        sm2 = SeedManager()
        sm1.set_seed(seed)
        sm2.set_seed(seed)
        assert sm1.get_seed() == sm2.get_seed()
        assert sm1.get_seed_str() == sm2.get_seed_str()

    def test_chain_call_consistency(self):
        """链式调用应保持种子一致"""
        sm = SeedManager()
        sm.set_seed(888).set_seed(888)
        assert sm.get_seed() == 888


class TestSeedDeterminism:
    """种子确定性/可复现性测试

    知识库要求：
    - 确定性原则：同 Seed + 同配置 = 100% 相同结果，不允许随机漂移
    - 所有随机逻辑必须绑定种子，禁止系统随机
    """

    def test_random_seed_deterministic_with_fixed_random_seed(self):
        """绑定 random.seed 后，generate_random_seed 应可复现"""
        fixed_seed = 42
        random.seed(fixed_seed)
        sm1 = SeedManager()
        result1 = sm1.generate_random_seed(8)

        random.seed(fixed_seed)
        sm2 = SeedManager()
        result2 = sm2.generate_random_seed(8)

        assert result1 == result2, (
            f"相同 random.seed({fixed_seed}) 下 generate_random_seed 应产生相同结果, "
            f"但得到 {result1!r} != {result2!r}"
        )

    def test_numeric_seed_deterministic_with_fixed_random_seed(self):
        """绑定 random.seed 后，generate_numeric_seed 应可复现"""
        fixed_seed = 123
        random.seed(fixed_seed)
        sm1 = SeedManager()
        result1 = sm1.generate_numeric_seed(6)

        random.seed(fixed_seed)
        sm2 = SeedManager()
        result2 = sm2.generate_numeric_seed(6)

        assert result1 == result2, (
            f"相同 random.seed({fixed_seed}) 下 generate_numeric_seed 应产生相同结果, "
            f"但得到 {result1!r} != {result2!r}"
        )

    def test_auto_generated_seed_deterministic(self):
        """绑定 random.seed 后，set_seed(None) 自动生成的种子应可复现"""
        fixed_seed = 999
        random.seed(fixed_seed)
        sm1 = SeedManager()
        sm1.set_seed(None)
        result1 = sm1.get_seed()

        random.seed(fixed_seed)
        sm2 = SeedManager()
        sm2.set_seed(None)
        result2 = sm2.get_seed()

        assert result1 == result2, (
            f"相同 random.seed({fixed_seed}) 下 set_seed(None) 应产生相同结果, "
            f"但得到 {result1!r} != {result2!r}"
        )

    def test_special_chars_fallback_deterministic(self):
        """绑定 random.seed 后，纯特殊字符兜底生成的种子应可复现"""
        fixed_seed = 777
        random.seed(fixed_seed)
        sm1 = SeedManager()
        sm1.set_seed("@#$%")
        result1 = sm1.get_seed()

        random.seed(fixed_seed)
        sm2 = SeedManager()
        sm2.set_seed("@#$%")
        result2 = sm2.get_seed()

        assert result1 == result2, (
            f"相同 random.seed({fixed_seed}) 下特殊字符兜底应产生相同结果, "
            f"但得到 {result1!r} != {result2!r}"
        )

    def test_different_random_seeds_produce_different_results(self):
        """不同 random.seed 应产生不同的生成结果"""
        random.seed(1)
        sm1 = SeedManager()
        r1 = sm1.generate_random_seed(8)

        random.seed(2)
        sm2 = SeedManager()
        r2 = sm2.generate_random_seed(8)

        assert r1 != r2, (
            "不同 random.seed 应产生不同的生成结果"
        )

    def test_multiple_calls_same_seed_same_sequence(self):
        """相同 random.seed 下多次调用应产生相同的序列"""
        fixed_seed = 555
        random.seed(fixed_seed)
        sm1 = SeedManager()
        seq1 = [sm1.generate_random_seed(4) for _ in range(5)]

        random.seed(fixed_seed)
        sm2 = SeedManager()
        seq2 = [sm2.generate_random_seed(4) for _ in range(5)]

        assert seq1 == seq2, (
            f"相同 random.seed({fixed_seed}) 下生成序列应一致, "
            f"但得到 {seq1} != {seq2}"
        )


class TestSaveLoad:
    """种子保存与加载测试"""

    @pytest.fixture
    def temp_file(self):
        """创建临时文件路径"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            filepath = f.name
        yield filepath
        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_save_and_load_numeric(self, temp_file):
        """保存并加载数字种子"""
        sm = SeedManager()
        sm.set_seed(12345)
        sm.save(temp_file)

        sm2 = SeedManager()
        sm2.load(temp_file)
        assert sm2.get_seed() == 12345

    def test_save_and_load_string(self, temp_file):
        """保存并加载字符串种子"""
        sm = SeedManager()
        sm.set_seed("my_seed_123")
        sm.save(temp_file)

        sm2 = SeedManager()
        sm2.load(temp_file)
        assert sm2.get_seed() == "my_seed_123"

    def test_save_and_load_auto_generated(self, temp_file):
        """保存并加载自动生成的种子"""
        sm = SeedManager()
        sm.set_seed(None)
        original_seed = sm.get_seed()
        sm.save(temp_file)

        sm2 = SeedManager()
        sm2.load(temp_file)
        assert sm2.get_seed() == original_seed

    def test_save_chain(self, temp_file):
        """save 支持链式调用"""
        sm = SeedManager()
        sm.set_seed(999).save(temp_file).set_seed(111)
        assert sm.get_seed() == 111

        sm2 = SeedManager()
        sm2.load(temp_file)
        assert sm2.get_seed() == 999

    def test_load_nonexistent_file(self):
        """加载不存在的文件应抛出异常"""
        sm = SeedManager()
        with pytest.raises(FileNotFoundError):
            sm.load("/nonexistent/path/seed.json")


class TestHistory:
    """历史记录测试"""

    def test_push_history(self):
        """压入历史记录"""
        sm = SeedManager()
        sm.set_seed(100)
        sm.push_history()
        assert sm.get_history() == [100]

    def test_push_history_multiple(self):
        """多次压入历史记录"""
        sm = SeedManager()
        for seed in [10, 20, 30]:
            sm.set_seed(seed).push_history()
        assert sm.get_history() == [10, 20, 30]

    def test_push_history_no_seed(self):
        """未设置种子时压入历史应无效果"""
        sm = SeedManager()
        sm.push_history()
        assert sm.get_history() == []

    def test_clear_history(self):
        """清空历史记录"""
        sm = SeedManager()
        sm.set_seed(1).push_history()
        sm.set_seed(2).push_history()
        assert len(sm.get_history()) == 2
        sm.clear_history()
        assert sm.get_history() == []

    def test_history_independence(self):
        """get_history 返回副本，修改不影响内部"""
        sm = SeedManager()
        sm.set_seed(42).push_history()
        hist = sm.get_history()
        hist.append(999)
        assert sm.get_history() == [42]

    def test_clear_history_chain(self):
        """clear_history 支持链式调用"""
        sm = SeedManager()
        result = sm.set_seed(1).push_history().clear_history()
        assert result is sm
        assert sm.get_history() == []


class TestReset:
    """重置测试"""

    def test_reset_clears_seed(self):
        """reset 应清空种子"""
        sm = SeedManager()
        sm.set_seed(12345)
        assert sm.get_seed() is not None
        sm.reset()
        assert sm.get_seed() is None

    def test_reset_clears_history(self):
        """reset 应清空历史记录"""
        sm = SeedManager()
        sm.set_seed(1).push_history()
        sm.set_seed(2).push_history()
        sm.reset()
        assert sm.get_history() == []

    def test_reset_chain(self):
        """reset 支持链式调用"""
        sm = SeedManager()
        result = sm.set_seed(42).push_history().reset()
        assert result is sm
        assert sm.get_seed() is None

    def test_reset_then_set_seed(self):
        """reset 后可重新设置种子"""
        sm = SeedManager()
        sm.set_seed(100)
        sm.reset()
        sm.set_seed(200)
        assert sm.get_seed() == 200


class TestGetSeedStr:
    """get_seed_str 测试"""

    def test_get_seed_str_none(self):
        """种子为 None 时返回空字符串"""
        sm = SeedManager()
        assert sm.get_seed_str() == ""

    def test_get_seed_str_numeric(self):
        """数字种子返回字符串形式"""
        sm = SeedManager()
        sm.set_seed(12345)
        assert sm.get_seed_str() == "12345"

    def test_get_seed_str_string(self):
        """字符串种子返回原字符串"""
        sm = SeedManager()
        sm.set_seed("hello")
        assert sm.get_seed_str() == "hello"


class TestRepr:
    """__repr__ 测试"""

    def test_repr_default(self):
        """默认状态的 repr"""
        sm = SeedManager()
        assert "None" in repr(sm)
        assert "history_count=0" in repr(sm)

    def test_repr_with_seed(self):
        """设置种子后的 repr"""
        sm = SeedManager()
        sm.set_seed(42)
        assert "42" in repr(sm)

    def test_repr_with_history(self):
        """有历史记录时的 repr"""
        sm = SeedManager()
        sm.set_seed(1).push_history()
        sm.set_seed(2).push_history()
        assert "history_count=2" in repr(sm)


class TestInvalidParams:
    """非法参数容错测试"""

    def test_float_seed_raises_typeerror(self):
        """float 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed(3.14)

    def test_bool_seed_raises_typeerror(self):
        """bool 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed(True)

    def test_list_seed_raises_typeerror(self):
        """list 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed([1, 2, 3])

    def test_dict_seed_raises_typeerror(self):
        """dict 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed({"a": 1})

    def test_tuple_seed_raises_typeerror(self):
        """tuple 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed((1, 2))

    def test_set_seed_raises_typeerror(self):
        """set 类型应抛出 TypeError"""
        sm = SeedManager()
        with pytest.raises(TypeError):
            sm.set_seed({1, 2, 3})


class TestStress:
    """压测：1000 次连续生成稳定性"""

    def test_1000_times_generate_random_seed(self):
        """1000 次连续生成随机种子无崩溃"""
        sm = SeedManager()
        for _ in range(1000):
            seed = sm.generate_random_seed()
            assert isinstance(seed, str)
            assert 1 <= len(seed) <= 32
            assert seed.isalnum()

    def test_1000_times_generate_numeric_seed(self):
        """1000 次连续生成数字种子无崩溃"""
        sm = SeedManager()
        for _ in range(1000):
            seed = sm.generate_numeric_seed()
            assert isinstance(seed, str)
            assert 1 <= len(seed) <= 16
            assert seed.isdigit()

    def test_1000_times_set_seed(self):
        """1000 次连续设置种子无崩溃"""
        sm = SeedManager()
        for i in range(1000):
            if i % 2 == 0:
                sm.set_seed(i + 1)
            else:
                sm.set_seed(f"seed_{i}")
            assert sm.get_seed() is not None

    def test_1000_times_save_load(self, tmp_path):
        """1000 次连续保存加载无崩溃"""
        sm = SeedManager()
        for i in range(1000):
            filepath = tmp_path / f"seed_{i}.json"
            sm.set_seed(i + 1)
            sm.save(str(filepath))

            sm2 = SeedManager()
            sm2.load(str(filepath))
            assert sm2.get_seed() == i + 1
            os.unlink(str(filepath))

    def test_1000_times_history_push(self):
        """1000 次连续压入历史无崩溃"""
        sm = SeedManager()
        for i in range(1000):
            sm.set_seed(i + 1).push_history()
        assert len(sm.get_history()) == 1000

    def test_chain_call_stability(self):
        """链式调用稳定性测试"""
        sm = SeedManager()
        for _ in range(500):
            sm.set_seed(42).push_history().clear_history().set_seed(100)
        assert sm.get_seed() == 100


class TestEdgeCases:
    """边界情况综合测试"""

    def test_set_seed_then_reset_then_set_again(self):
        """设置种子 → 重置 → 再次设置"""
        sm = SeedManager()
        sm.set_seed(100)
        assert sm.get_seed() == 100
        sm.reset()
        assert sm.get_seed() is None
        sm.set_seed(200)
        assert sm.get_seed() == 200

    def test_history_after_reset(self):
        """重置后历史应清空"""
        sm = SeedManager()
        sm.set_seed(1).push_history()
        sm.set_seed(2).push_history()
        sm.reset()
        sm.set_seed(3).push_history()
        assert sm.get_history() == [3]

    def test_save_without_seed(self):
        """未设置种子时保存"""
        sm = SeedManager()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            filepath = f.name
        try:
            sm.save(filepath)
            # 保存 None 种子
            with open(filepath, "r") as f:
                data = json.load(f)
            assert data["seed"] is None
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_corrupted_file(self):
        """加载损坏的文件应抛出异常"""
        sm = SeedManager()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json")
            filepath = f.name
        try:
            with pytest.raises(json.JSONDecodeError):
                sm.load(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_string_with_leading_trailing_spaces(self):
        """字符串前后带空格"""
        sm = SeedManager()
        sm.set_seed("  hello123  ")
        # 空格不是字母数字，会被过滤
        result = sm.get_seed()
        assert isinstance(result, str)
        assert result == "hello123"

    def test_numeric_seed_as_string(self):
        """数字字符串种子"""
        sm = SeedManager()
        sm.set_seed("12345")
        result = sm.get_seed()
        assert isinstance(result, str)
        assert result == "12345"

    def test_unicode_letters(self):
        """Unicode 字母应被过滤"""
        sm = SeedManager()
        sm.set_seed("héllo")
        result = sm.get_seed()
        assert isinstance(result, str)
        # é 不是字母数字，被过滤
        assert result == "hllo"

    def test_empty_string_after_filter(self):
        """过滤后为空字符串应自动生成"""
        sm = SeedManager()
        sm.set_seed("!!!")
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == 6
        assert result.isdigit()

    def test_max_int_seed_boundary(self):
        """最大合法整数种子"""
        sm = SeedManager()
        sm.set_seed(999999999)
        assert sm.get_seed() == 999999999

    def test_min_int_seed_boundary(self):
        """最小合法整数种子"""
        sm = SeedManager()
        sm.set_seed(1)
        assert sm.get_seed() == 1

    def test_max_string_seed_length(self):
        """最大合法字符串种子长度"""
        sm = SeedManager()
        seed = "A" * 32
        sm.set_seed(seed)
        assert sm.get_seed() == seed

    def test_min_string_seed_length(self):
        """最小合法字符串种子长度"""
        sm = SeedManager()
        sm.set_seed("a")
        assert sm.get_seed() == "a"

    def test_save_load_chain(self):
        """save 和 load 链式调用"""
        sm = SeedManager()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            filepath = f.name
        try:
            result = sm.set_seed(42).save(filepath).reset().load(filepath)
            assert result is sm
            assert sm.get_seed() == 42
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


class TestDeterministic:
    """确定性回归测试"""

    def test_same_seed_same_result_multiple_times(self):
        """同一种子多次设置应得到相同结果"""
        sm = SeedManager()
        sm.set_seed(12345)
        result1 = sm.get_seed()
        sm.set_seed(12345)
        result2 = sm.get_seed()
        assert result1 == result2

    def test_same_string_seed_same_result(self):
        """同一字符串种子多次设置应得到相同结果"""
        sm = SeedManager()
        sm.set_seed("test_seed")
        result1 = sm.get_seed()
        sm.set_seed("test_seed")
        result2 = sm.get_seed()
        assert result1 == result2

    def test_save_load_consistency(self):
        """保存后再加载应得到完全相同的种子"""
        sm = SeedManager()
        sm.set_seed(888888)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            filepath = f.name
        try:
            sm.save(filepath)
            sm2 = SeedManager()
            sm2.load(filepath)
            assert sm2.get_seed() == sm.get_seed()
            assert sm2.get_seed_str() == sm.get_seed_str()
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_auto_generated_seed_consistency(self):
        """自动生成的种子在保存加载后应一致"""
        sm = SeedManager()
        sm.set_seed(None)
        auto_seed = sm.get_seed()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            filepath = f.name
        try:
            sm.save(filepath)
            sm2 = SeedManager()
            sm2.load(filepath)
            assert sm2.get_seed() == auto_seed
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


class TestFaultTolerance:
    """容错/恢复机制测试"""

    def test_invalid_type_does_not_crash(self):
        """非法类型不应导致崩溃"""
        sm = SeedManager()
        invalid_inputs = [3.14, True, False, [1], {"a": 1}, (1,), {1}]
        for inp in invalid_inputs:
            with pytest.raises(TypeError):
                sm.set_seed(inp)
        # 管理器仍可正常使用
        sm.set_seed(42)
        assert sm.get_seed() == 42

    def test_out_of_range_does_not_crash(self):
        """越界数字不应导致崩溃"""
        sm = SeedManager()
        invalid_inputs = [0, -1, -100, 1000000000]
        for inp in invalid_inputs:
            with pytest.raises(ValueError):
                sm.set_seed(inp)
        # 管理器仍可正常使用
        sm.set_seed(42)
        assert sm.get_seed() == 42

    def test_special_chars_fallback(self):
        """特殊字符自动兜底生成"""
        sm = SeedManager()
        sm.set_seed("@#$%")
        result = sm.get_seed()
        assert isinstance(result, str)
        assert len(result) == 6
        assert result.isdigit()

    def test_none_fallback(self):
        """None 自动