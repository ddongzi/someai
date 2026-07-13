"""
SeedManager 单元测试

覆盖范围：
- 初始化测试（默认种子、自定义种子）
- 种子属性 getter/setter 测试
- 种子边界极值测试（最大/最小/0值）
- 种子一致性回归测试
- 种子确定性/可复现性测试
- reset 重置测试
- get_state / set_state 状态管理测试
- 随机方法测试（randint, uniform, choice, shuffle, sample, random）
- 非法参数容错测试
- 压测：1000 次连续生成稳定性
- 边界情况综合测试
"""

import pytest
import random as std_random

from app import SeedManager


# ================================================================
# 辅助函数
# ================================================================


def _collect_sequence(sm: SeedManager, method: str, n: int = 10, **kwargs):
    """收集 n 次随机调用的结果序列，用于确定性校验。"""
    seq = []
    for _ in range(n):
        fn = getattr(sm, method)
        seq.append(fn(**kwargs))
    return seq


# ================================================================
# 初始化测试
# ================================================================


class TestInit:
    """初始化测试"""

    def test_default_init(self):
        """默认初始化应自动生成种子"""
        sm = SeedManager()
        assert isinstance(sm.seed, int)
        assert sm.seed > 0

    def test_init_with_seed(self):
        """传入种子初始化"""
        sm = SeedManager(seed=42)
        assert sm.seed == 42

    def test_init_with_zero_seed(self):
        """传入 0 作为种子"""
        sm = SeedManager(seed=0)
        assert sm.seed == 0

    def test_init_with_large_seed(self):
        """传入大整数种子"""
        sm = SeedManager(seed=0xFFFF_FFFF)
        assert sm.seed == 0xFFFF_FFFF

    def test_init_with_negative_seed(self):
        """传入负数种子"""
        sm = SeedManager(seed=-100)
        assert sm.seed == -100

    def test_multiple_init_independent(self):
        """多次初始化互不影响"""
        sm1 = SeedManager(seed=10)
        sm2 = SeedManager(seed=20)
        assert sm1.seed == 10
        assert sm2.seed == 20

    def test_init_seed_is_int(self):
        """默认生成的种子应为 int 类型"""
        sm = SeedManager()
        assert isinstance(sm.seed, int)

    def test_init_preserves_initial_seed(self):
        """初始化后 _initial_seed 应与 seed 一致"""
        sm = SeedManager(seed=12345)
        assert sm.seed == 12345
        # 修改 seed 后，_initial_seed 应保持不变
        sm.seed = 999
        assert sm.seed == 999
        sm.reset()
        assert sm.seed == 12345


# ================================================================
# 种子属性测试
# ================================================================


class TestSeedProperty:
    """种子属性 getter/setter 测试"""

    def test_get_seed(self):
        """获取种子值"""
        sm = SeedManager(seed=42)
        assert sm.seed == 42

    def test_set_seed(self):
        """设置种子值"""
        sm = SeedManager()
        sm.seed = 100
        assert sm.seed == 100

    def test_set_seed_updates_random_state(self):
        """设置种子后随机状态应更新"""
        sm = SeedManager(seed=1)
        v1 = sm.randint(0, 1000)
        sm.seed = 1
        v2 = sm.randint(0, 1000)
        assert v1 == v2

    def test_set_seed_zero(self):
        """设置种子为 0"""
        sm = SeedManager(seed=42)
        sm.seed = 0
        assert sm.seed == 0

    def test_set_seed_large(self):
        """设置大整数种子"""
        sm = SeedManager()
        sm.seed = 0x7FFF_FFFF
        assert sm.seed == 0x7FFF_FFFF

    def test_set_seed_negative(self):
        """设置负数种子"""
        sm = SeedManager()
        sm.seed = -1
        assert sm.seed == -1


# ================================================================
# 种子边界极值测试
# ================================================================


class TestSeedBoundary:
    """种子边界极值测试"""

    def test_seed_min_int(self):
        """最小整数值种子"""
        sm = SeedManager(seed=-2**31)
        assert sm.seed == -2**31
        # 验证随机方法仍正常工作
        val = sm.randint(0, 100)
        assert 0 <= val <= 100

    def test_seed_max_int(self):
        """最大整数值种子"""
        sm = SeedManager(seed=2**31 - 1)
        assert sm.seed == 2**31 - 1
        val = sm.randint(0, 100)
        assert 0 <= val <= 100

    def test_seed_zero(self):
        """种子为 0"""
        sm = SeedManager(seed=0)
        assert sm.seed == 0
        val = sm.randint(0, 100)
        assert 0 <= val <= 100

    def test_seed_one(self):
        """种子为 1"""
        sm = SeedManager(seed=1)
        assert sm.seed == 1

    def test_seed_negative_one(self):
        """种子为 -1"""
        sm = SeedManager(seed=-1)
        assert sm.seed == -1


# ================================================================
# 种子一致性回归测试
# ================================================================


class TestSeedConsistency:
    """种子一致性回归测试"""

    @pytest.mark.parametrize("seed", [0, 1, 42, 999, 2**31 - 1, -1, -100])
    def test_same_seed_same_value(self, seed):
        """相同种子应得到相同的 seed 值"""
        sm1 = SeedManager(seed=seed)
        sm2 = SeedManager(seed=seed)
        assert sm1.seed == sm2.seed

    @pytest.mark.parametrize("seed", [0, 1, 42, 999, 2**31 - 1, -1, -100])
    def test_same_seed_same_random_sequence(self, seed):
        """相同种子应产生相同的随机序列"""
        sm1 = SeedManager(seed=seed)
        sm2 = SeedManager(seed=seed)
        seq1 = _collect_sequence(sm1, "random", n=20)
        seq2 = _collect_sequence(sm2, "random", n=20)
        assert seq1 == seq2

    def test_different_seeds_different_sequences(self):
        """不同种子应产生不同的随机序列"""
        sm1 = SeedManager(seed=1)
        sm2 = SeedManager(seed=2)
        seq1 = _collect_sequence(sm1, "random", n=10)
        seq2 = _collect_sequence(sm2, "random", n=10)
        assert seq1 != seq2

    def test_set_seed_consistency(self):
        """设置相同种子后随机序列应一致"""
        sm = SeedManager(seed=100)
        seq1 = _collect_sequence(sm, "random", n=5)
        sm.seed = 100
        seq2 = _collect_sequence(sm, "random", n=5)
        assert seq1 == seq2


# ================================================================
# 种子确定性/可复现性测试
# ================================================================


class TestSeedDeterminism:
    """种子确定性/可复现性测试

    知识库要求：
    - 确定性原则：同 Seed + 同配置 = 100% 相同结果，不允许随机漂移
    - 所有随机逻辑必须绑定种子，禁止系统随机
    """

    def test_randint_deterministic(self):
        """相同种子下 randint 结果可复现"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        for _ in range(50):
            assert sm1.randint(0, 1000) == sm2.randint(0, 1000)

    def test_uniform_deterministic(self):
        """相同种子下 uniform 结果可复现"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        for _ in range(50):
            assert sm1.uniform(0.0, 1.0) == sm2.uniform(0.0, 1.0)

    def test_choice_deterministic(self):
        """相同种子下 choice 结果可复现"""
        seq = list(range(100))
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        for _ in range(50):
            assert sm1.choice(seq) == sm2.choice(seq)

    def test_shuffle_deterministic(self):
        """相同种子下 shuffle 结果可复现"""
        seq1 = list(range(50))
        seq2 = list(range(50))
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        sm1.shuffle(seq1)
        sm2.shuffle(seq2)
        assert seq1 == seq2

    def test_sample_deterministic(self):
        """相同种子下 sample 结果可复现"""
        population = list(range(100))
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        for _ in range(20):
            assert sm1.sample(population, 5) == sm2.sample(population, 5)

    def test_random_deterministic(self):
        """相同种子下 random 结果可复现"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        for _ in range(50):
            assert sm1.random() == sm2.random()

    def test_full_sequence_deterministic(self):
        """完整随机调用序列确定性"""
        sm1 = SeedManager(seed=123)
        sm2 = SeedManager(seed=123)
        seq1 = []
        seq2 = []
        for _ in range(30):
            seq1.append(sm1.randint(1, 6))
            seq1.append(sm1.uniform(0.0, 10.0))
            seq1.append(sm1.choice(["a", "b", "c"]))
            seq2.append(sm2.randint(1, 6))
            seq2.append(sm2.uniform(0.0, 10.0))
            seq2.append(sm2.choice(["a", "b", "c"]))
        assert seq1 == seq2

    def test_different_seeds_different_full_sequence(self):
        """不同种子完整序列应不同"""
        sm1 = SeedManager(seed=1)
        sm2 = SeedManager(seed=2)
        seq1 = _collect_sequence(sm1, "random", n=100)
        seq2 = _collect_sequence(sm2, "random", n=100)
        assert seq1 != seq2


# ================================================================
# Reset 重置测试
# ================================================================


class TestReset:
    """重置测试"""

    def test_reset_restores_initial_seed(self):
        """reset 应恢复为初始种子"""
        sm = SeedManager(seed=42)
        sm.seed = 100
        assert sm.seed == 100
        sm.reset()
        assert sm.seed == 42

    def test_reset_restores_random_state(self):
        """reset 后随机状态应恢复到初始状态"""
        sm = SeedManager(seed=42)
        seq1 = _collect_sequence(sm, "random", n=10)
        sm.seed = 999
        _collect_sequence(sm, "random", n=5)  # 消耗一些随机数
        sm.reset()
        seq2 = _collect_sequence(sm, "random", n=10)
        assert seq1 == seq2

    def test_reset_multiple_times(self):
        """多次 reset 应始终恢复到初始种子"""
        sm = SeedManager(seed=42)
        for new_seed in [100, 200, 300, 400]:
            sm.seed = new_seed
            sm.reset()
            assert sm.seed == 42

    def test_reset_after_init_without_seed(self):
        """默认初始化后 reset 应恢复到初始种子"""
        sm = SeedManager()
        initial = sm.seed
        sm.seed = 999
        sm.reset()
        assert sm.seed == initial

    def test_reset_then_set_seed(self):
        """reset 后可重新设置种子"""
        sm = SeedManager(seed=42)
        sm.reset()
        sm.seed = 200
        assert sm.seed == 200


# ================================================================
# 状态管理测试
# ================================================================


class TestStateManagement:
    """get_state / set_state 状态管理测试"""

    def test_get_state_returns_random(self):
        """get_state 应返回 random.Random 对象"""
        sm = SeedManager(seed=42)
        state = sm.get_state()
        assert isinstance(state, std_random.Random)

    def test_set_state_restores_state(self):
        """set_state 应恢复随机状态"""
        sm = SeedManager(seed=42)
        seq1 = _collect_sequence(sm, "random", n=10)
        # 保存状态
        state = sm.get_state()
        # 消耗一些随机数
        _collect_sequence(sm, "random", n=5)
        # 恢复状态
        sm.set_state(state)
        seq2 = _collect_sequence(sm, "random", n=10)
        assert seq1 == seq2

    def test_set_state_from_another_manager(self):
        """可以从另一个 SeedManager 复制状态"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=999)
        _collect_sequence(sm1, "random", n=5)
        state = sm1.get_state()
        sm2.set_state(state)
        seq1 = _collect_sequence(sm1, "random", n=10)
        seq2 = _collect_sequence(sm2, "random", n=10)
        assert seq1 == seq2

    def test_state_independence(self):
        """不同 SeedManager 的状态应独立"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        sm1.randint(0, 100)  # 消耗 sm1 的随机数
        state1 = sm1.get_state()
        state2 = sm2.get_state()
        # 两个状态应不同（因为 sm1 消耗了一个随机数）
        v1 = state1.random()
        v2 = state2.random()
        assert v1 != v2


# ================================================================
# 随机方法测试
# ================================================================


class TestRandomMethods:
    """随机方法功能测试"""

    def test_randint_range(self):
        """randint 返回值应在 [a, b] 范围内"""
        sm = SeedManager(seed=42)
        for _ in range(100):
            val = sm.randint(5, 10)
            assert 5 <= val <= 10

    def test_randint_single_value(self):
        """randint 当 a==b 时应返回该值"""
        sm = SeedManager(seed=42)
        for _ in range(10):
            assert sm.randint(7, 7) == 7

    def test_randint_negative_range(self):
        """randint 负数范围"""
        sm = SeedManager(seed=42)
        for _ in range(100):
            val = sm.randint(-10, -1)
            assert -10 <= val <= -1

    def test_uniform_range(self):
        """uniform 返回值应在 [a, b) 范围内"""
        sm = SeedManager(seed=42)
        for _ in range(100):
            val = sm.uniform(0.0, 10.0)
            assert 0.0 <= val < 10.0

    def test_uniform_negative_range(self):
        """uniform 负数范围"""
        sm = SeedManager(seed=42)
        for _ in range(100):
            val = sm.uniform(-5.0, 0.0)
            assert -5.0 <= val < 0.0

    def test_uniform_single_value(self):
        """uniform 当 a==b 时应返回该值"""
        sm = SeedManager(seed=42)
        for _ in range(10):
            assert sm.uniform(3.5, 3.5) == 3.5

    def test_choice_from_list(self):
        """choice 从列表中选取元素"""
        sm = SeedManager(seed=42)
        seq = [10, 20, 30, 40, 50]
        for _ in range(50):
            val = sm.choice(seq)
            assert val in seq

    def test_choice_from_single_element(self):
        """choice 从单元素列表中选取"""
        sm = SeedManager(seed=42)
        assert sm.choice([42]) == 42

    def test_choice_from_string(self):
        """choice 从字符串中选取字符"""
        sm = SeedManager(seed=42)
        s = "abcdefg"
        for _ in range(50):
            val = sm.choice(s)
            assert val in s

    def test_shuffle_modifies_in_place(self):
        """shuffle 应就地打乱序列"""
        sm = SeedManager(seed=42)
        original = list(range(20))
        seq = original.copy()
        sm.shuffle(seq)
        # 元素应相同但顺序可能不同
        assert sorted(seq) == original
        # 大概率顺序已改变
        assert seq != original

    def test_shuffle_empty_list(self):
        """shuffle 空列表不应报错"""
        sm = SeedManager(seed=42)
        seq = []
        sm.shuffle(seq)
        assert seq == []

    def test_shuffle_single_element(self):
        """shuffle 单元素列表不应改变"""
        sm = SeedManager(seed=42)
        seq = [1]
        sm.shuffle(seq)
        assert seq == [1]

    def test_sample_size(self):
        """sample 应返回 k 个元素"""
        sm = SeedManager(seed=42)
        population = list(range(100))
        result = sm.sample(population, 5)
        assert len(result) == 5

    def test_sample_no_repetition(self):
        """sample 应返回不重复元素"""
        sm = SeedManager(seed=42)
        population = list(range(100))
        result = sm.sample(population, 20)
        assert len(set(result)) == 20

    def test_sample_all_elements(self):
        """sample 当 k==len(population) 时应返回所有元素（顺序可能不同）"""
        sm = SeedManager(seed=42)
        population = list(range(10))
        result = sm.sample(population, 10)
        assert sorted(result) == population

    def test_random_range(self):
        """random 返回值应在 [0.0, 1.0) 范围内"""
        sm = SeedManager(seed=42)
        for _ in range(100):
            val = sm.random()
            assert 0.0 <= val < 1.0

    def test_random_distribution(self):
        """random 应产生不同的值"""
        sm = SeedManager(seed=42)
        values = [sm.random() for _ in range(100)]
        # 100 个值中至少应有 90 个不同的
        assert len(set(values)) >= 90


# ================================================================
# 非法参数容错测试
# ================================================================


class TestInvalidParams:
    """非法参数容错测试"""

    def test_randint_reversed_bounds(self):
        """randint 当 a > b 时应抛出 ValueError"""
        sm = SeedManager(seed=42)
        with pytest.raises(ValueError):
            sm.randint(10, 5)

    def test_choice_empty_list(self):
        """choice 空列表应抛出 IndexError"""
        sm = SeedManager(seed=42)
        with pytest.raises(IndexError):
            sm.choice([])

    def test_sample_k_too_large(self):
        """sample 当 k > len(population) 时应抛出 ValueError"""
        sm = SeedManager(seed=42)
        with pytest.raises(ValueError):
            sm.sample([1, 2, 3], 5)

    def test_sample_k_zero(self):
        """sample 当 k == 0 时应返回空列表"""
        sm = SeedManager(seed=42)
        result = sm.sample([1, 2, 3], 0)
        assert result == []

    def test_sample_k_negative(self):
        """sample 当 k < 0 时应抛出 ValueError"""
        sm = SeedManager(seed=42)
        with pytest.raises(ValueError):
            sm.sample([1, 2, 3], -1)

    def test_shuffle_non_list(self):
        """shuffle 传入非列表应抛出 TypeError"""
        sm = SeedManager(seed=42)
        with pytest.raises(TypeError):
            sm.shuffle("string")

    def test_randint_non_integer(self):
        """randint 传入非整数应抛出 TypeError"""
        sm = SeedManager(seed=42)
        with pytest.raises(TypeError):
            sm.randint(1.5, 10)
        with pytest.raises(TypeError):
            sm.randint(1, 10.5)

    def test_uniform_non_numeric(self):
        """uniform 传入非数值应抛出 TypeError"""
        sm = SeedManager(seed=42)
        with pytest.raises(TypeError):
            sm.uniform("a", 10.0)
        with pytest.raises(TypeError):
            sm.uniform(1.0, "b")


# ================================================================
# __repr__ 测试
# ================================================================


class TestRepr:
    """__repr__ 测试"""

    def test_repr_with_seed(self):
        """repr 应包含种子值"""
        sm = SeedManager(seed=42)
        assert "SeedManager(seed=42)" in repr(sm)

    def test_repr_after_set_seed(self):
        """修改种子后 repr 应更新"""
        sm = SeedManager(seed=42)
        sm.seed = 100
        assert "SeedManager(seed=100)" in repr(sm)

    def test_repr_after_reset(self):
        """reset 后 repr 应恢复"""
        sm = SeedManager(seed=42)
        sm.seed = 100
        sm.reset()
        assert "SeedManager(seed=42)" in repr(sm)


# ================================================================
# 压测：1000 次连续生成稳定性
# ================================================================


class TestStress:
    """压测：1000 次连续生成稳定性"""

    def test_1000_randint(self):
        """1000 次连续 randint 无崩溃"""
        sm = SeedManager(seed=42)
        for _ in range(1000):
            val = sm.randint(0, 1000)
            assert 0 <= val <= 1000

    def test_1000_uniform(self):
        """1000 次连续 uniform 无崩溃"""
        sm = SeedManager(seed=42)
        for _ in range(1000):
            val = sm.uniform(0.0, 1.0)
            assert 0.0 <= val < 1.0

    def test_1000_random(self):
        """1000 次连续 random 无崩溃"""
        sm = SeedManager(seed=42)
        for _ in range(1000):
            val = sm.random()
            assert 0.0 <= val < 1.0

    def test_1000_choice(self):
        """1000 次连续 choice 无崩溃"""
        sm = SeedManager(seed=42)
        seq = list(range(100))
        for _ in range(1000):
            val = sm.choice(seq)
            assert val in seq

    def test_1000_shuffle(self):
        """1000 次连续 shuffle 无崩溃"""
        sm = SeedManager(seed=42)
        for _ in range(1000):
            seq = list(range(20))
            sm.shuffle(seq)
            assert len(seq) == 20

    def test_1000_sample(self):
        """1000 次连续 sample 无崩溃"""
        sm = SeedManager(seed=42)
        population = list(range(100))
        for _ in range(1000):
            result = sm.sample(population, 5)
            assert len(result) == 5
            assert len(set(result)) == 5

    def test_1000_seed_set_and_reset(self):
        """1000 次连续设置种子和重置无崩溃"""
        sm = SeedManager(seed=42)
        for i in range(1000):
            sm.seed = i
            sm.randint(0, 100)
            sm.reset()
            assert sm.seed == 42

    def test_1000_mixed_operations(self):
        """1000 次混合随机操作无崩溃"""
        sm = SeedManager(seed=42)
        seq = list(range(50))
        for i in range(1000):
            op = i % 6
            if op == 0:
                sm.randint(0, 100)
            elif op == 1:
                sm.uniform(0.0, 1.0)
            elif op == 2:
                sm.choice(seq)
            elif op == 3:
                sm.shuffle(seq.copy())
            elif op == 4:
                sm.sample(seq, 5)
            else:
                sm.random()

    def test_1000_state_save_restore(self):
        """1000 次状态保存恢复无崩溃"""
        sm = SeedManager(seed=42)
        for _ in range(1000):
            state = sm.get_state()
            sm.randint(0, 100)
            sm.set_state(state)
            v1 = sm.random()
            sm.set_state(state)
            v2 = sm.random()
            assert v1 == v2


# ================================================================
# 边界情况综合测试
# ================================================================


class TestEdgeCases:
    """边界情况综合测试"""

    def test_seed_set_then_reset_then_set_again(self):
        """设置种子 → 重置 → 再次设置"""
        sm = SeedManager(seed=42)
        sm.seed = 100
        assert sm.seed == 100
        sm.reset()
        assert sm.seed == 42
        sm.seed = 200
        assert sm.seed == 200

    def test_randint_large_range(self):
        """randint 大范围"""
        sm = SeedManager(seed=42)
        val = sm.randint(-10**9, 10**9)
        assert -10**9 <= val <= 10**9

    def test_randint_zero_range(self):
        """randint 零范围（a==b）"""
        sm = SeedManager(seed=42)
        assert sm.randint(5, 5) == 5

    def test_uniform_large_range(self):
        """uniform 大范围"""
        sm = SeedManager(seed=42)
        val = sm.uniform(-1e6, 1e6)
        assert -1e6 <= val < 1e6

    def test_choice_large_list(self):
        """choice 从大列表中选取"""
        sm = SeedManager(seed=42)
        large_list = list(range(10000))
        val = sm.choice(large_list)
        assert 0 <= val < 10000

    def test_shuffle_large_list(self):
        """shuffle 大列表"""
        sm = SeedManager(seed=42)
        seq = list(range(1000))
        sm.shuffle(seq)
        assert sorted(seq) == list(range(1000))
        assert seq != list(range(1000))

    def test_sample_large_population(self):
        """sample 从大总体中抽样"""
        sm = SeedManager(seed=42)
        population = list(range(10000))
        result = sm.sample(population, 100)
        assert len(result) == 100
        assert len(set(result)) == 100

    def test_sample_small_population(self):
        """sample 从小总体中抽样"""
        sm = SeedManager(seed=42)
        population = [1, 2, 3]
        result = sm.sample(population, 2)
        assert len(result) == 2
        for v in result:
            assert v in population

    def test_state_after_reset(self):
        """reset 后状态应与初始状态一致"""
        sm = SeedManager(seed=42)
        seq1 = _collect_sequence(sm, "random", n=10)
        sm.seed = 999
        _collect_sequence(sm, "random", n=20)
        sm.reset()
        seq2 = _collect_sequence(sm, "random", n=10)
        assert seq1 == seq2

    def test_multiple_resets_same_sequence(self):
        """多次 reset 应产生相同的随机序列"""
        sm = SeedManager(seed=42)
        for _ in range(5):
            seq = _collect_sequence(sm, "random", n=5)
            sm.reset()
            seq2 = _collect_sequence(sm, "random", n=5)
            assert seq == seq2

    def test_seed_property_type(self):
        """seed 属性应为 int 类型"""
        sm = SeedManager(seed=42)
        assert isinstance(sm.seed, int)
        sm.seed = 100
        assert isinstance(sm.seed, int)

    def test_initial_seed_preserved(self):
        """_initial_seed 应始终保存初始值"""
        sm = SeedManager(seed=42)
        assert sm._initial_seed == 42
        sm.seed = 999
        assert sm._initial_seed == 42
        sm.reset()
        assert sm._initial_seed == 42


# ================================================================
# 确定性回归测试
# ================================================================


class TestDeterministic:
    """确定性回归测试"""

    def test_same_seed_same_result_multiple_times(self):
        """同一种子多次初始化应得到相同结果"""
        for _ in range(10):
            sm1 = SeedManager(seed=12345)
            sm2 = SeedManager(seed=12345)
            assert sm1.seed == sm2.seed
            assert sm1.random() == sm2.random()

    def test_same_seed_same_randint_sequence(self):
        """同一种子 randint 序列应一致"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        seq1 = [sm1.randint(1, 100) for _ in range(50)]
        seq2 = [sm2.randint(1, 100) for _ in range(50)]
        assert seq1 == seq2

    def test_same_seed_same_mixed_sequence(self):
        """同一种子混合调用序列应一致"""
        sm1 = SeedManager(seed=42)
        sm2 = SeedManager(seed=42)
        seq1 = []
        seq2 = []
        for i in range(30):
            if i % 3 == 0:
                seq1.append(sm1.randint(0, 100))
                seq2.append(sm2.randint(0, 100))
            elif i % 3 == 1:
                seq1.append(sm1.uniform(0.0, 1.0))
                seq2.append(sm2.uniform(0.0, 1.0))
            else:
                seq1.append(sm1.choice(["x", "y", "z"]))
                seq2.append(sm2.choice(["x", "y", "z"]))
        assert seq1 == seq2

    def test_different_seeds_different_randint(self):
        """不同种子 randint 序列应不同"""
        sm1 = SeedManager(seed=1)
        sm2 = SeedManager(seed=2)
        seq1 = [sm1.randint(0, 1000) for _ in range(20)]
        seq2 = [sm2.randint(0, 1000) for _ in range(20)]
        assert seq1 != seq2

    def test_seed_set_deterministic(self):
        """设置相同种子后随机序列应一致"""
        sm = SeedManager(seed=42)
        seq1 = [sm.randint(0, 100) for _ in range(10)]
        sm.seed = 42
        seq2 = [sm.randint(0, 100) for _ in range(10)]
        assert seq1 == seq2


# ================================================================
# 容错/恢复机制测试
# ================================================================


class TestFaultTolerance:
    """容错/恢复机制测试"""

    def test_invalid_randint_does_not_crash(self):
        """非法 randint 参数不应导致后续调用崩溃"""
        sm = SeedManager(seed=42)
        try:
            sm.randint(10, 5)
        except ValueError:
            pass
        # 后续调用应正常
        assert sm.randint(0, 100) == sm.randint(0, 100)

    def test_invalid_choice_does_not_crash(self):
        """非法 choice 参数不应导致后续调用崩溃"""
        sm = SeedManager(seed=42)
        try:
            sm.choice([])
        except IndexError:
            pass
        # 后续调用应正常
        assert sm.choice([1, 2, 3]) in [1, 2, 3]

    def test_invalid_sample_does_not_crash(self):
        """非法 sample 参数不应导致后续调用崩溃"""
        sm = SeedManager(seed=42)
        try:
            sm.sample([1, 2, 3], 5)
        except ValueError:
            pass
        # 后续调用应正常
        result = sm.sample([1, 2, 3], 2)
        assert len(result) == 2

    def test_recovery_after_error(self):
        """错误后管理器仍可正常使用"""
        sm = SeedManager(seed=42)
        # 触发错误
        try:
            sm.randint(10, 5)
        except ValueError:
            pass
        # 恢复后正常使用
        v1 = sm.randint(0, 100)
        v2 = sm.randint(0, 100)
        assert 0 <= v1 <= 100
        assert 0 <= v2 <= 100

    def test_multiple_errors_recovery(self):
        """多次错误后管理器仍可正常使用"""
        sm = SeedManager(seed=42)
        errors = 0
        for _ in range(10):
            try:
                sm.randint(10, 5)
            except ValueError:
                errors += 1
        assert errors == 10
        # 恢复后正常使用
        val = sm.randint(0, 100)
        assert 0 <= val <= 100
