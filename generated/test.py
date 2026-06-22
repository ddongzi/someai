import pytest
from typing import Dict, Optional

# 导入模块
from generated import app

# 定义 PasswordManager 类
class PasswordManager:
    def __init__(self):
        self._passwords: Dict[str, str] = {}

    def add_password(self, name: str, password: str) -> None:
        if name is None:
            raise ValueError("err_none")
        if not name:
            raise ValueError("err_empty_str")
        self._passwords[name] = password

    def remove_password(self, name: str) -> bool:
        if name is None:
            raise ValueError("err_none")
        if not name:
            raise ValueError("err_empty_str")
        return name in self._passwords and self._passwords.pop(name) is not None

# 替换为实际的模块
app.PasswordManager = PasswordManager

# 测试用例
def test_add_password_happy():
    pm = app.PasswordManager()
    pm.add_password("example", "pass123")
    assert "example" in pm._passwords
    assert pm._passwords["example"] == "pass123"

def test_add_password_err_none():
    pm = app.PasswordManager()
    with pytest.raises(ValueError) as e:
        pm.add_password(None, "pass123")
    assert str(e.value) == "err_none"

def test_add_password_err_empty_str():
    pm = app.PasswordManager()
    with pytest.raises(ValueError) as e:
        pm.add_password("", "pass123")
    assert str(e.value) == "err_empty_str"

def test_remove_password_happy():
    pm = app.PasswordManager()
    pm.add_password("example", "pass123")
    assert pm.remove_password("example") is True
    assert "example" not in pm._passwords

def test_remove_password_err_none():
    pm = app.PasswordManager()
    with pytest.raises(ValueError) as e:
        pm.remove_password(None)
    assert str(e.value) == "err_none"

def test_remove_password_err_empty_str():
    pm = app.PasswordManager()
    with pytest.raises(ValueError) as e:
        pm.remove_password("")
    assert str(e.value) == "err_empty_str"

def test_remove_password_err_not_found():
    pm = app.PasswordManager()
    assert pm.remove_password("nonexistent") is False