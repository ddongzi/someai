import os
from typing import Optional
from langchain_core.tools import tool


import os
from pathlib import Path
from dotenv import load_dotenv, set_key

load_dotenv()

@tool
def set_environment_variable(variable_name: str, value: str, save_to_dotenv: bool = True) -> str:
    """
    设置或更新环境变量的值。

    Args:
        variable_name (str): 环境变量的名称，例如 'SPEC_FILE', 'WORKSPACE_DIR'。
        value (str): 要设置的字符串值。
        save_to_dotenv (bool): 是否同步持久化写入到项目根目录的 .env 文件中。一般默认为 True 即可 

    Returns:
        str: 执行结果的成功或错误提示信息。
    """
    # 1. 清洗变量名
    clean_name = variable_name.strip().replace("$", "")
    clean_value = str(value).strip()
    
    if not clean_name:
        return "错误：环境变量名称不能为空。"

    try:
        # 2. 在当前运行的内存进程中设置变量（立即可用）
        os.environ[clean_name] = clean_value
        msg = f"成功：当前运行环境中已将 '{clean_name}' 设置为 '{clean_value}'。"

        # 3. 持久化写入 .env 文件
        if save_to_dotenv:
            dotenv_path = Path(".env")
            # 如果 .env 文件不存在，则自动创建
            if not dotenv_path.exists():
                dotenv_path.touch()
            
            # 使用 python-dotenv 提供的 set_key 函数安全写入（自动处理覆盖或新增）
            set_key(dotenv_path=str(dotenv_path), key_to_set=clean_name, value_to_set=clean_value)
            msg += " 并已同步持久化写入到 .env 文件中。"
            
        return msg

    except Exception as e:
        return f"错误：设置环境变量失败，原因：{str(e)}"

@tool
def get_environment_variable(variable_name: str) -> str:
    """
    获取系统环境变量的值。

    Args:
        variable_name (str): 环境变量的名称，, 

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


