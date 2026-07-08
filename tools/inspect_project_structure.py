import os
from typing import List, Optional
from langchain_core.tools import tool # 如果使用 LangChain，否则可以用标准 python 函数加 type hint
from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)

load_dotenv()

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

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
