"""SeedManager 单元测试"""

import os
import random
import pytest
from app import SeedManager


class TestSeedManager:
    """种子管理器测试套件"""

    def setup_method(self):
        self.mgr = SeedManager()
        # 清理可能残留的测试文件
        for f in ["seed_data.json", "test_seed.json"]:
            if os.path.exists(f):
                os.remove(f)

    # ── 种子生成 ──────────────────────────────────

    def test_generate_random_seed_default(self):
        """默认生成 8 位随机字符串种子"""
        seed = SeedManager.generate_random_seed()
        assert isinstance(seed, str)
        assert len(seed) == 8
        assert seed.isalnum()

    def test_generate_random_seed_custom_length(self):
        """自定义长度生成随机字符串种子"""
        for length in [6, 10, 16]:
            seed = SeedManager.generate_random_seed(length)
            assert len(seed) == length

    def test_generate_random_seed_clamp(self):
        """长度超出 6-16 范围时自动裁剪"""
        assert len(SeedManager.generate_random_seed(4)) == 6
        assert len(SeedManager.generate_random_seed(20)) == 16

    def test_generate_numeric_seed(self):
        """生成纯数字种子"""
        seed = SeedManager.generate_numeric_seed(6)
        assert isinstance(seed, int)
        assert 100000 <= seed <= 999999

    # ── 种子设置 ──────────────────────────────────

    def test_set_seed_none(self):
        """传入 None 时自动生成随机种子"""
        self.mgr.set_seed(None)
        assert self.mgr.get_seed() is not None
        assert isinstance(self.mgr.get_seed(), str)

    def test_set_seed_int(self):
        """设置数字种子"""
        self.mgr.set_seed(42)
        assert self.mgr.get_seed() == 42

    def test_set_seed_int_boundary(self):
        """数字种子边界值"""
        self.mgr.set_seed(1)
        assert self.mgr.get_seed() == 1
        self.mgr.set_seed(999999999)
        assert self.mgr.get_seed() == 999999999

    def test_set_seed_int_invalid(self):
        """数字种子越界时抛出异常"""
        with pytest.raises(ValueError):
            self.mgr.set_seed(0)
        with pytest.raises(ValueError):
            self.mgr.set_seed(1000000000)

    def test_set_seed_str(self):
        """设置字符串种子"""
        self.mgr.set_seed("Hello123")
        assert self.mgr.get_seed() == "Hello123"

    def test_set_seed_str_filter_special_chars(self):
        """字符串种子自动过滤特殊字符"""
        self.mgr.set_seed("Hello!@#World 123")
        assert self.mgr.get_seed() == "HelloWorld123"

    def test_set_seed_str_too_long(self):
        """超长字符串种子自动截断到 32 位"""
        long_seed = "a" * 40
        self.mgr.set_seed(long_seed)
        assert len(self.mgr.get_seed()) == 32

    def test_set_seed_str_empty_after_filter(self):
        """过滤后为空字符串时抛出异常"""
        with pytest.raises(ValueError):
            self.mgr.set_seed("!@#$%")

    def test_set_seed_invalid_type(self):
        """不支持的种子类型抛出 TypeError"""
        with pytest.raises(TypeError):
            self.mgr.set_seed(3.14)  # type: ignore

    # ── 种子获取 ──────────────────────────────────

    def test_get_seed_unset(self):
        """未设置种子时返回 None"""
        assert self.mgr.get_seed() is None

    def test_get_seed_str(self):
        """获取种子字符串表示"""
        self.mgr.set_seed(12345)
        assert self.mgr.get_seed_str() == "12345"
        self.mgr.set_seed("abc")
        assert self.mgr.get_seed_str() == "abc"

    def test_get_seed_str_unset(self):
        """未设置种子时返回空字符串"""
        assert self.mgr.get_seed_str() == ""

    # ── 种子持久化 ────────────────────────────────

    def test_save_and_load(self):
        """保存种子并重新加载"""
        self.mgr.set_seed(2024)
        path = self.mgr.save("test_seed.json")
        assert os.path.exists(path)

        new_mgr = SeedManager()
        new_mgr.load("test_seed.json")
        assert new_mgr.get_seed() == 2024

    def test_save_and_load_str_seed(self):
        """保存并加载字符串种子"""
        self.mgr.set_seed("MySeed123")
        self.mgr.save("test_seed.json")

        new_mgr = SeedManager()
        new_mgr.load("test_seed.json")
        assert new_mgr.get_seed() == "MySeed123"

    def test_save_without_seed(self):
        """未设置种子时保存抛出异常"""
        with pytest.raises(RuntimeError):
            self.mgr.save("test_seed.json")

    def test_load_file_not_found(self):
        """加载不存在的文件抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            self.mgr.load("nonexistent.json")

    # ── 历史记录 ──────────────────────────────────

    def test_push_history(self):
        """压入历史记录"""
        self.mgr.set_seed(1).push_history()
        self.mgr.set_seed(2).push_history()
        self.mgr.set_seed(3).push_history()
        assert self.mgr.get_history() == [1, 2, 3]

    def test_push_history_no_duplicate(self):
        """重复种子不会重复记录"""
        self.mgr.set_seed(42).push_history()
        self.mgr.set_seed(42).push_history()
        assert self.mgr.get_history() == [42]

    def test_clear_history(self):
        """清空历史记录"""
        self.mgr.set_seed(1).push_history()
        self.mgr.set_seed(2).push_history()
        self.mgr.clear_history()
        assert self.mgr.get_history() == []

    # ── 链式调用 ──────────────────────────────────

    def test_chain_calls(self):
        """支持链式调用"""
        self.mgr.set_seed(100).push_history().set_seed(200).push_history()
        assert self.mgr.get_history() == [100, 200]

    # ── 重置 ──────────────────────────────────────

    def test_reset(self):
        """重置管理器"""
        self.mgr.set_seed(42).push_history()
        self.mgr.reset()
        assert self.mgr.get_seed() is None
        assert self.mgr.get_history() == []

    # ── 确定性 ────────────────────────────────────

    def test_deterministic_with_same_seed(self):
        """相同种子应产生相同结果（示例：用种子初始化随机数生成器）"""
        self.mgr.set_seed(12345)
        random.seed(str(self.mgr.get_seed()))
        values_a = [random.randint(0, 100) for _ in range(5)]

        self.mgr.set_seed(12345)
        random.seed(str(self.mgr.get_seed()))
        values_b = [random.randint(0, 100) for _ in range(5)]

        assert values_a == values_b

    # ── 清理 ──────────────────────────────────────

    def teardown_method(self):
        for f in ["seed_data.json", "test_seed.json"]:
            if os.path.exists(f):
                os.remove(f)
