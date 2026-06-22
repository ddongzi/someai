## 1. 业务需求  
实现一个支持加减乘除四则运算的简单计算器，输入两个数字（int / float），返回 float 结果。除法若除数为零则抛出 ZeroDivisionError。

## 2. 核心接口规格表  

| 方法      | 入参          | 返回   | 异常               |
|-----------|---------------|--------|--------------------|
| `add`     | a, b: Number  | float  | -                  |
| `subtract`| a, b: Number  | float  | -                  |
| `multiply`| a, b: Number  | float  | -                  |
| `divide`  | a, b: Number  | float  | ZeroDivisionError  |

> Number 指 int 或 float。

## 3. Python 代码骨架  

```python
# calculator.py
from typing import Union

Number = Union[int, float]

class Calculator:
    """简单四则运算计算器"""

    def add(self, a: Number, b: Number) -> float:
        """a + b"""
        pass

    def subtract(self, a: Number, b: Number) -> float:
        """a - b"""
        pass

    def multiply(self, a: Number, b: Number) -> float:
        """a * b"""
        pass

    def divide(self, a: Number, b: Number) -> float:
        """a / b，b=0时抛出 ZeroDivisionError"""
        pass
```

## 4. Pytest 测试骨架  

```python
# test_calculator.py
import pytest
from calculator import Calculator

class TestCalculator:
    """正常：整数 / 浮点数混合"""

    def test_add_normal(self):
        """add: 3+5=8.0, 1.5+2.5=4.0"""
        pass

    def test_subtract_normal(self):
        """subtract: 10-3=7.0, 2.5-0.5=2.0"""
        pass

    def test_multiply_normal(self):
        """multiply: 4*5=20.0, 1.2*3=3.6"""
        pass

    def test_divide_normal(self):
        """divide: 10/2=5.0, 3/4=0.75, -6/3=-2.0"""
        pass

    # ---------- 边界 ----------
    def test_add_boundary(self):
        """大数相加、负数与小数，如 1e9+1e9, -1.0+0.5"""
        pass

    def test_divide_boundary(self):
        """除数为极小数，如 1/1e-9 ≈ 1e9"""
        pass

    # ---------- 异常 ----------
    def test_divide_by_zero(self):
        """ZeroDivisionError with int or float zero"""
        with pytest.raises(ZeroDivisionError):
            calc = Calculator()
            calc.divide(1, 0)
            calc.divide(3.14, 0.0)
```

## 5. 验收对齐规则  

- **通过性**：所有正常 / 边界 / 异常测试用例均通过（使用 `pytest -v`）。  
- **类型安全**：所有方法的入参与返回值标注类型，不引入 `typing` 之外的库。  
- **健壮性**：除法除零必须抛出 Python 内置 `ZeroDivisionError`，不捕获或重新包装。  
- **风格**：PEP8 合规，无冗余 import，单文件结构（`calculator.py` + `test_calculator.py`）。