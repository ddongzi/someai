# PasswordManager.py

from typing import Dict, Optional

class PasswordManager:
    """
    管理内存中的密码，键是密码名称，值是密码。
    """
    def __init__(self):
        self._passwords: Dict[str, str] = {}

    def add_password(self, name: str, password: str) -> None:
        """
        添加一个密码到管理器中。

        参数：
            name (str): 密码名称，必填。
            password (str): 实际密码，必填。

        返回值：无。

        成功路径：将新密码添加到字典中，如果名称已存在则不进行任何操作。
        失败路径：
            err_none: 参数为 None。抛出 ValueError。
            err_empty_str: 密码名称为空字符串。抛出 ValueError。
        """
        if name is None:
            raise ValueError("name cannot be None")
        if not name:
            raise ValueError("name cannot be an empty string")
        
        self._passwords[name] = password

    def remove_password(self, name: str) -> bool:
        """
        从管理器中移除一个密码。

        参数：
            name (str): 密码名称，必填。

        返回值：bool，表示是否成功移除。

        成功路径：从字典中删除指定名称的密码，如果存在则返回 True，否则返回 False。
        失败路径：
            err_none: 参数为 None。抛出 ValueError。
            err_empty_str: 密码名称为空字符串。抛出 ValueError。
            err_not_found: 密码名称不存在。返回 False。
        """
        if name is None:
            raise ValueError("name cannot be None")
        if not name:
            raise ValueError("name cannot be an empty string")
        
        return self._passwords.pop(name, False)