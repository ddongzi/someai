import os
from typing import Optional
from langchain_core.tools import tool

@tool
def get_environment_variable(variable_name: str) -> str:
    """
    获取系统环境变量的值。

    Args:
        variable_name (str): 环境变量的名称，例如 'SPEC_FILE', 

    Returns:
        str: 环境变量对应的字符串值；如果变量未设置，则返回错误提示信息。
    """
    # 移除可能误输入的空格或 $ 符号
    clean_name = variable_name.strip().replace("$", "")
    
    # 从操作系统中读取变量值
    value = os.environ.get(clean_name)
    
    if value is None:
        return f"错误：环境变量 '{clean_name}' 当前未设置或为空。"
    
    return value
