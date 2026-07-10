import os
from pathlib import Path
import os
from typing import List, Optional
from langchain_core.tools import tool # 如果使用 LangChain，否则可以用标准 python 函数加 type hint
from dotenv import load_dotenv
import os
import logging
from logger import run_logger

load_dotenv()

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

@tool
def read_file(file_path: str) -> str:
    """
    读取指定文本文件的完整内容。
    
    参数:
    file_path: 位于生成目录（GENERATED_DIR）内部的相对文件路径。
        注意：请直接写文件名或内部子路径，绝对不要包含外层的 'generated/' 目录名！
              正确示例: 'test.py', 'src/utils.py'
              错误示例: 'generated/test.py'
    """
    try:
        # 1. 安全检查：防止路径穿越漏洞（Path Traversal）
        # 将工作目录和目标路径转为绝对路径
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        # 确保目标路径在工作目录之内
        if not target_path.is_relative_to(base_path):
            return f"错误：拒绝访问。路径 '{file_path}' 超出了允许的工作目录范围。"
            
        # 2. 存在性与类型检查
        if not target_path.exists():
            return f"错误：文件 '{file_path}' 不存在。请核对路径是否正确。"
        if not target_path.is_file():
            return f"错误：'{file_path}' 是一个目录，不是文件。无法读取内容。"
            
        # 3. 读取内容（带编码容错）
        # 优先使用 utf-8，失败时使用 gbk（兼容 Windows），彻底失败时报错
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(target_path, "r", encoding="gbk") as f:
                content = f.read()
                
        # 4. 返回成功结果（如果文件为空，给予明确提示）
        if not content.strip():
            return f"提示：文件 '{file_path}' 内容为空。"
            
        return content

    except Exception as e:
        # 捕获其他未知异常，并返回友好的错误信息给 Agent
        return f"读取文件时发生未知错误: {str(e)}"
    
@tool
def create_file(file_path: str, content: str = "") -> str:
    """
    在允许的生成目录中创建一个新文件，并写入初始内容。如果文件已存在，则会报错。
    
    参数:
    file_path: 位于生成目录（GENERATED_DIR）内部的相对文件路径。
              注意：请直接写文件名或内部子路径，绝对不要包含外层的 'generated/' 目录名！
              正确示例: 'core/main.py', 'test.py'
              错误示例: 'generated/test.py'
    content: 写入文件的初始文本内容，默认为空字符串。
    """
    try:
        # 1. 自动容错：如果大模型或用户不小心带了 generated/ 前缀，自动裁剪
        if file_path.startswith("generated/"):
            file_path = file_path.replace("generated/", "", 1)
            
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        # 2. 安全检查：防止路径穿越漏洞
        if not target_path.is_relative_to(base_path):
            return f"错误：拒绝访问。路径 '{file_path}' 超出了允许的工作目录范围。"
            
        # 3. 冲突检查：防止意外覆盖已有文件
        if target_path.exists():
            return f"错误：文件 '{file_path}' 已经存在。如果需要修改内容，请使用相应的更新/写入工具。"
            
        # 4. 自动创建父级文件夹（例如传入 'core/main.py' 时自动创建 'core' 目录）
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 5. 写入内容
        target_path.write_text(content, encoding="utf-8")
        return f"成功：文件 '{file_path}' 已成功创建，并写入了 {len(content)} 个字符。"
        
    except Exception as e:
        return f"创建文件时发生未知错误: {str(e)}"
    
@tool
def inspect_project_structure(
    exclude_dirs: Optional[List[str]] = None, 
    max_depth: int = 5
) -> str:
    """
    探索并返回项目直观的目录树状结构。
    在编写任何 import 导入语句、定位代码文件或理解项目架构之前，必须先调用此工具来获取准确的文件路径。
    
    args:
        exclude_dirs: 需要忽略的目录名称列表（例如：['.git', 'node_modules', '__pycache__', 'venv']）。默认会自动过滤常见缓存和依赖目录。
        max_depth: 遍历目录的最大深度，默认值为 5，用于防止目录过深导致大模型 Token 溢出。
    return:
        基于文本的可视化项目目录树状结构。
    """
    root_path = GENERATED_DIR
    if exclude_dirs is None:
        exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']
        
    if not os.path.exists(root_path):
        return f"Error: The path '{root_path}' does not exist."

    tree_lines = [f"📂 {os.path.basename(os.path.abspath(root_path)) or root_path}"]
    
    def _traverse(current_dir: str, prefix: str = "", depth: int = 1):
        if depth > max_depth:
            tree_lines.append(f"{prefix}└── ... (max depth reached)")
            return
            
        try:
            # 获取当前目录下所有项并排序（保证 LLM 读取的稳定性）
            items = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        # 过滤掉不需要的目录或文件
        filtered_items = [
            item for item in items 
            if item not in exclude_dirs and not item.startswith('._')
        ]
        
        count = len(filtered_items)
        for index, item in enumerate(filtered_items):
            path = os.path.join(current_dir, item)
            is_last = (index == count - 1)
            
            # 判断连线符号
            connector = "└── " if is_last else "├── "
            
            if os.path.isdir(path):
                tree_lines.append(f"{prefix}{connector}📁 {item}/")
                # 为子目录准备下一层的缩进前缀
                next_prefix = prefix + ("    " if is_last else "│   ")
                _traverse(path, next_prefix, depth + 1)
            else:
                tree_lines.append(f"{prefix}{connector}📄 {item}")

    _traverse(os.path.abspath(root_path))
    return "\n".join(tree_lines)
