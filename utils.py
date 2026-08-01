import re
import tiktoken
import logging
import json

import os
from typing import Dict, Any, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
import yaml
from jinja2 import Template
from langchain_core.prompts import ChatPromptTemplate

def extract_python_code(llm_output: str) -> str:
    # 匹配 ```python 开头，``` 结尾的代码块
    match = re.search(r"```python\s*(.*?)\s*```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 备用容错：如果 AI 只写了 ``` 而没写 python
    match_fallback = re.search(r"```\s*(.*?)\s*```", llm_output, re.DOTALL)
    if match_fallback:
        return match_fallback.group(1).strip()
    
    # 如果 AI 真的完全没带任何 Markdown，直接返回原文本
    return llm_output.strip()

# 得到运行目录下所有文件和目录结构。只看py结尾的文件
def get_all_files_in_dir(dir_path: str) -> list:
    import os
    return [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.py')]


import os
from pathlib import Path

def draw_workflow_png(graph, name, dir='./art'):
    from globals.logger import run_logger

    # 1. 确保目标目录存在，如果不存在则自动创建（包括多层嵌套目录）
    output_dir = Path(dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 拼接完整的输出路径
    mmd_path = output_dir / f"{name}.mmd"
    png_path = output_dir / f"{name}.png"

    try:

        # 3. 导出原始mermaid字符串
        mermaid_text = graph.draw_mermaid()
        # 4. 写入 mmd 文件到指定目录
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(mermaid_text)
            run_logger.info(f"已生成 {mmd_path}")

        # 5. 写入 png 文件到指定目录
        png_data = graph.draw_mermaid_png()
        with open(png_path, "wb") as f:
            f.write(png_data)
            run_logger.info(f"{png_path} saved.")
    except Exception as e:
        run_logger.exception(f'png mmd failed!. {e}')


import json
import sys
import tiktoken

def calculate_total_tokens_for_pyobj(dict_values: dict, model="gpt-4o") -> int:
    """
    1. 【模型角度】计算当前 Python 字典对象（State）转化为 JSON 文本后的总 token 数量
    """
    from globals.logger import run_logger
    
    try:
        # 为了防止某些特殊对象（如 LangChain 的 Message 对象）在 json.dumps 时报错，
        # 可以加上 default=str 将其强转为字符串，确保统计不中断
        state_text = json.dumps(dict_values, ensure_ascii=False, indent=2, default=str)
        return calculate_total_tokens_for_text(state_text, model=model)
    except Exception as e:
        run_logger.info(f"❌ 序列化 Python 对象失败: {e}")
        return 0

def calculate_total_tokens_for_text(text: str, model="gpt-4o") -> int:
    """
    2. 【纯文本角度】计算一段普通文本（如代码字符串、用户输入）对应的 token 数量
    """
    if not text:
        return 0
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        # 兜底方案：如果模型未找到，默认使用 gpt-4o 的 o200k_base 编码器
        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))

def calculate_memory_size(state_values: dict) -> dict:
    """
    3. 【内存字节大小角度】计算整个字典对象在物理传输/存储时的真实字节大小（Bytes）
    返回一个包含 B、KB、MB 的友好字典
    """
    try:
        # 转为 utf-8 编码的二进制字节流，这是最真实的物理占用大小
        state_bytes = json.dumps(state_values, ensure_ascii=False, default=str).encode('utf-8')
        bytes_size = len(state_bytes)
    except Exception:
        # 如果 dumps 失败，降级使用 sys.getsizeof 估算（不推荐，作为最后防线）
        bytes_size = sys.getsizeof(state_values)
        
    return {
        "bytes": bytes_size,
        "kb": round(bytes_size / 1024, 2),
        "mb": round(bytes_size / (1024 * 1024), 4)
    }

import json
import os


def get_first_pending_task(file_path: str ='todo_tasks.json' ) -> dict | None:
    """从todo_tasks.json 任务列表读取并返回 ID 最小且状态为 pending 的单个任务"""
    if not os.path.exists(file_path):
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            
        # 1. 过滤出所有 pending 状态的任务
        pending_tasks = [t for t in tasks if t.get('status') == 'pending']
        
        if not pending_tasks:
            return None
            
        # 2. 找出 id 最小的任务并返回
        return min(pending_tasks, key=lambda x: x.get('id', float('inf')))
        
    except (json.JSONDecodeError, Exception):
        return None
    

# 假设你的所有 prompt yaml 文件都放在当前目录的 prompts 文件夹下
PROMPT_DIR = "./prompts"

def get_scene_prompt(file_name: str, scene_name: str = 'base', **kwargs) -> str:
    """
    根据配置文件名和业务场景，动态组装并渲染返回 System Prompt 和 User Prompt。

    Args:
        file_name (str): yaml 配置文件名，例如 'coder.yaml'
        scene_name (str): 对应的场景名称，例如 'write_code'
        **kwargs: 需要替换到 Prompt 模板中的动态变量，例如 requirement="xxx"

    Returns:
        Tuple[str, str]: (system_prompt, user_prompt)
    """
    file_path = os.path.join(PROMPT_DIR, f"{file_name}.yaml")
    
    # 1. 安全读取并解析 YAML 文件
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到 Prompt 配置文件: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 文件解析失败: {e}")

    # 2. 提取基础系统提示词 (System Base)
    system_prompt = config.get("system_base", "").strip()

    # 3. 提取对应的业务场景模板 (User Scene)
    scenes_dict = config.get("scenes", {})
    if scene_name not in scenes_dict:
        raise KeyError(f"在文件 {file_name} 中未找到场景配置: '{scene_name}'")
        
    raw_user_template = scenes_dict[scene_name]

    # 4. 使用 Jinja2 渲染用户提示词模板，自动替换 {{variable}}
    try:
        template = Template(raw_user_template)
        user_prompt = template.render(**kwargs).strip()
    except Exception as e:
        raise RuntimeError(f"Prompt 模板渲染失败，可能缺少必要参数。错误信息: {e}")


    return system_prompt, user_prompt

import json
import re

def parse_llm_json(llm_output: str):
    """
    清洗并解析 LLM 输出的 JSON 字符串，支持带有 Markdown 标记或前后废话的情况
    """
    from globals.logger import run_logger
    # 1. 去除两端的空白字符
    text = llm_output.strip()
    
    # 2. 核心正则：匹配最外层的 {} 或 []
    # 这样即使 LLM 输出 "这是结果：```json {\"a\": 1} ``` 谢谢！" 也能精准提取
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    
    if not match:
        raise ValueError("在 LLM 输出中未找到有效的 JSON 结构 ({} 或 [])")
        
    json_str = match.group(1)
    
    # 3. 解析 JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # 如果解析失败，通常是由于 LLM 输出了不规范的控制字符、单引号或截断
        run_logger.info(f"JSON 语法错误: {e}")
        # 兜底清洗：处理常见的反斜杠转义或截断（可选）
        return handle_json_retry(json_str)

def handle_json_retry(corrupted_str: str):
    """兜底逻辑：处理由于 LLM 截断导致的非完整 JSON（可根据需要扩展）"""
    # 如果是因为 LLM token 达到上限被截断，可以使用 json_repair 等第三方库修复
    # 这里先直接抛出异常
    raise ValueError("JSON 结构损坏，无法解析")

def json_serializer(obj):
    """当遇到 json 无法识别的特殊类型时，自动进行优雅降级转换"""
    if isinstance(obj, set):
        return list(obj)  # 🔥 关键修复：把 set 自动转为普通的 list
    if hasattr(obj, "dict"):
        return obj.dict()  # 防御 Pydantic 规范对象
    if hasattr(obj, "to_json"):
        return obj.to_json()
    # 如果实在无法解析，将其转为字符串，防止整个流崩掉
    return str(obj)


import os
import logging
from logging.handlers import RotatingFileHandler
import sys
def get_file_logger(logger_name: str, filename: str, log_dir: str = 'logs', 
                    level=logging.INFO, backup_count: int = 1, so:bool = False) -> logging.Logger:
    """
    创建并返回一个仅输出到文件的日志对象（自动按天切分，不打印到控制台）。
    
    参数:
    logger_name: 日志对象的名称（全局唯一，如 'sse_logger'、'chat_logger'）
    log_dir: 日志文件存放的目录路径
    filename: 日志文件名（如 'sse_stream.log'）
    level: 日志级别，默认为 logging.INFO
    backup_count: 历史日志保留天数，默认为 1 天,
    so: 是否终端输出
    """
    # 1. 获取或创建 run_logger 实例
    run_logger = logging.getLogger(logger_name)
    run_logger.setLevel(level)
    
    # ⭐ 核心：关闭日志向父级传播，彻底阻止其打印到控制台
    run_logger.propagate = False

    # 2. 健壮性检查：如果该 run_logger 已经配置过 handler，直接返回，避免重复添加导致重复打印
    if run_logger.handlers:
        return run_logger

    # 3. 自动创建不存在的日志目录
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, filename)

    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=0, 
        backupCount=backup_count, 
        encoding="utf-8"
    )
        # 2. 【核心】如果日志文件已经存在，说明是上次运行留下的，立即强制切分
    if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 0:
        file_handler.doRollover()
    # 5. 设置统一的日志格式

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s')
    file_handler.setFormatter(formatter)
    
    # 6. 将 handler 绑定到 run_logger
    run_logger.addHandler(file_handler)

    if so:
        # 终端也能输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        run_logger.addHandler(console_handler)
        
    return run_logger


import hashlib
from pathlib import Path
from typing import Union

def calculate_file_hash(file_path: Union[str, Path], chunk_size: int = 8192) -> str:
    """
    分块计算文件的 MD5 哈希值，防止大文件撑爆内存。
    
    Args:
        file_path: 绝对文件路径
        chunk_size: 每次读取的字节数，默认 8KB
        
    Returns:
        str: 32位的十六进制 MD5 哈希字符串
    """
    # 确保路径格式正确
    path = Path(file_path).resolve()
    
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
        
    md5_hash = hashlib.md5()
    
    # 使用二进制模式 ('rb') 读取，确保对所有类型文件（文本、二进制）的通用性
    with open(path, "rb") as f:
        # 循环分块读取
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
            
    return md5_hash.hexdigest()
