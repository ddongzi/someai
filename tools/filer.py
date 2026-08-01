import os
from typing import List, Optional,Union
from langchain_core.tools import tool # 如果使用 LangChain，否则可以用标准 python 函数加 type hint
from dotenv import load_dotenv
import logging
import re
import shutil
from pathlib import Path
from langgraph.types import Command
from langchain.tools import ToolRuntime, tool
from globals.state import FileSnapshot
from langchain.messages import ToolMessage
from globals.logger import run_logger
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from utils import calculate_file_hash
from datetime import datetime, timezone
import json

from pathlib import Path
from datetime import datetime, timezone
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, RemoveMessage
from langgraph.types import Command
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState
load_dotenv()
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

@tool
def read_file(file_path: str, state: Annotated[dict, InjectedState], runtime: ToolRuntime) -> str:
    """
    读取指定文本文件的完整内容。
    
    参数:
    file_path: 位于项目内部的相对文件路径。
        注意：请直接写文件名或内部子路径，绝对不要包含项目路径
              正确示例: 'test.py', 'src/utils.py'
              错误示例: 'generated/test.py'
    """
    try:
        # 1. 安全检查：防止路径穿越漏洞
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        if not target_path.is_relative_to(base_path):
            return f"错误：拒绝访问。路径 '{file_path}' 超出了允许的工作目录范围。"
            
        if not target_path.exists():
            return f"错误：文件 '{file_path}' 不存在。请核对路径是否正确。"
        if not target_path.is_file():
            return f"错误：'{file_path}' 是一个目录，不是文件。无法读取内容。"

        current_file_hash = calculate_file_hash(target_path)
        
        # 稳妥获取旧快照，如果不存在则初始化
        files_dict = state.get('files', {})
        file_snapshot: FileSnapshot = files_dict.get(file_path, {
            'file_name': Path(file_path).name,
            'file_path': file_path,
            'last_read_time': '',
            'last_modified_time': '',
            'file_hash': '',
            'allowed_read_nodes': [],  # 根据您之前的设计可选
            'allowed_write_nodes': []
        })

        if file_snapshot['file_hash'] == current_file_hash:
            return f"提示：文件 '{file_path}' 自上次读取后未发生变化，内容未更新。请直接从当前记忆上下文中获取内容。"

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return f"提示：文件 '{file_path}' 内容为空。"

        # 🌟 4. 核心优化：消息“除旧”逻辑
        messages_to_update = []
        history_messages = state.get("messages", [])

        for msg in history_messages:
            if isinstance(msg, ToolMessage) and msg.name == "read_file":
                if isinstance(msg.artifact, dict) and msg.artifact.get("file_path") == file_path:
                    diluted_message = ToolMessage(
                        id=msg.id, #
                        tool_call_id=msg.tool_call_id,
                        content="[系统提示：此处的旧文件内容已被清理，请参考后续最新的读取结果]" # 清空之前旧的消息.
                    )
                    messages_to_update.append(diluted_message)

        # 5. 更新快照数据
        file_snapshot.update({
            'file_hash': current_file_hash,
            'last_read_time': datetime.now(timezone.utc).isoformat(),
        })

        # 🌟 6. 放入新消息，
        new_tool_message = ToolMessage(
            content=content,
            artifact={
                'file_path': file_path,
            },
            tool_call_id=runtime.tool_call_id,
        )
        messages_to_update.append(new_tool_message)

        # 7. 统一提交更新
        return Command(
            update={
                'files': {file_path: file_snapshot},  # 更新快照字典
                'messages': messages_to_update         # [OldToolMessage, ..., NewToolMessage]
            }
        )

    except Exception as e:
        return f"读取文件时发生未知错误: {str(e)}"

@tool
def write_to_file(file_path: str, description: str, content: str, state:Annotated[dict, InjectedState],runtime: ToolRuntime) -> str:
    """
    完全覆盖重写已存在的文件内容。如果文件或其所在的目录不存在，将返回错误。
    
    Args:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
              正确示例: 'core/main.py', 'test.py'
              错误示例: 'generated/test.py'
        content: 写入的全部内容。
        description: 文件摘要描述

        state: 无需传入,会自动注入
        runtime (ToolRuntime): 工具执行时的运行时上下文对象。参数会自动注入
    Return:
        写入成功/失败响应。
    """
    try:
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        # 1. 安全性检查：防止通过 ../ 路径遍历逃逸出目标根目录
        if not str(target_path).startswith(str(base_path)):
            return f"错误：拒绝访问。路径 '{file_path}' 超出了允许的项目根目录。"

        # 2. 检查父级目录是否存在
        if not target_path.parent.exists() or not target_path.parent.is_dir():
            return f"错误：写入失败。目录 '{file_path}' 的上级文件夹不存在。"

        # 3. 检查文件本身是否存在（既然是“覆盖重写”，文件必须先存在）
        if not target_path.exists() or not target_path.is_file():
            return f"错误：写入失败。文件 '{file_path}' 不存在。如需新建文件，请使用创建文件的工具。"

        # 4. 执行覆盖写入
        target_path.write_text(content, encoding="utf-8")

        # 5. 更新文件快照
        current_file_hash = calculate_file_hash(target_path)
        files_dict = state.get('files', {})
        file_snapshot: FileSnapshot = files_dict.get(file_path, {
            'file_name': Path(file_path).name,
            'file_path': file_path,
            'last_read_time': '',
            'last_modified_time': '',
            'file_hash': '',
        })

        file_snapshot.update({
            'file_hash': current_file_hash,
            'description': description,
            'last_modified_time': datetime.now(timezone.utc).isoformat(),
        })

        return Command(
            update={
                'files': {file_path: file_snapshot},  # 更新快照字典
                'messages': [
                    ToolMessage(
                        content=f"成功：文件 '{file_path}' 已成功覆盖重写，并写入了 {len(content)} 个字符。",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )
    except Exception as e:
        return f"错误：写入文件失败。原因：{str(e)}"



@tool
def create_file(file_path: str, content: str, description:str, state:Annotated[dict, InjectedState],runtime:ToolRuntime) -> str:
    """
    在目录中创建一个新文件，并写入初始内容。如果文件已存在，则会报错。
    
    参数:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
        content: 写入文件的初始文本内容。
        description: 文件摘要描述
        runtime (ToolRuntime): 工具执行时的运行时上下文对象。参数会自动注入
        state: 无需传入,会自动注入
    """
    try:
            
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        # 2. 安全检查：防止路径穿越漏洞
        if not target_path.is_relative_to(base_path):
            return f"错误：拒绝访问。路径 '{file_path}' 超出了允许的工作目录范围。"
            
        # 3. 冲突检查：防止意外覆盖已有文件
        if target_path.exists():
            return f"错误：文件 '{file_path}' 已经存在。"
            
        # 4. 自动创建父级文件夹（例如传入 'core/main.py' 时自动创建 'core' 目录）
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 5. 写入内容
        target_path.write_text(content, encoding="utf-8")

        # 6. 更新文件快照
        current_file_hash = calculate_file_hash(target_path)
        files_dict = state.get('files', {})
        file_snapshot: FileSnapshot = files_dict.get(file_path, {
            'file_name': Path(file_path).name,
            'file_path': file_path,
            'last_read_time': '',
            'last_modified_time': '',
            'file_hash': '',
            'description': description,
            'allowed_read_nodes': [],  # 根据您之前的设计可选
            'allowed_write_nodes': []
        })
        
        file_snapshot.update({
            'file_hash': current_file_hash,
            'last_modified_time': datetime.now(timezone.utc).isoformat(),
        })
        return Command(
            update={
                'file_ledger': {file_path: file_snapshot},  # 更新快照字典 
                'messages': [
                    ToolMessage(
                        content=f"成功：文件 '{file_path}' 已成功创建，并写入了 {len(content)} 个字符。",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )
        
    except Exception as e:
        return f"创建文件时发生未知错误: {str(e)}"
    


@tool
def inspect_project(state: Annotated[dict, InjectedState]) -> str:
    """
    查看项目结构,包括文件路径,文件描述

    Args: None (此工具不需要任何输入参数，由系统自动读取状态)

    Returns:
        str: 包含所有文件路径和描述的 Markdown 格式文本。
    """
    run_logger.info(f'inspect project !..{state}')
    # 从自动注入的全局 State 中获取 file_ledger
    file_ledger = state.get("file_ledger", {})
    
    if not file_ledger:
        return "提示：当前项目文件台账为空，尚未创建任何文件。"
        
    # 格式化输出给大模型
    output_lines = ["项目文件列表:"]
    for path, meta in file_ledger.items():
        description = meta.get("description", "暂无描述")
        output_lines.append(f"- `{path}`: {description}")
        
    return "\n".join(output_lines)


import os
import ast
from pathlib import Path
from langchain_core.tools import tool

@tool
def inspect_file_summary(file_path: str, max_preview_lines: int = 15) -> str:
    """
    获取python文件摘要信息：1. 文件完整性、行数、首尾预览行数.  2. 结构大纲信息

    Args:
        file_path: 位于项目内部的相对文件路径。
        max_preview_lines: 头尾切片采样预览的最大行数，默认15行。
    Return:
        文件摘要信息
    """
    base_path = Path(GENERATED_DIR).resolve()
    target_path = Path(base_path, file_path).resolve()
    
    # 🌟 路径防逃逸安全校验
    if not str(target_path).startswith(str(base_path)):
        return f"❌ 错误：拒绝访问。路径 '{file_path}' 超出了允许的项目根目录。"
        
    if not target_path.exists() or not target_path.is_file():
        return f"❌ 错误：未找到文件 '{file_path}'，请确认路径是否正确。"

    try:
        # 1. 读取基础物理数据
        content = target_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        total_lines = len(lines)
        file_size_kb = os.path.getsize(target_path) / 1024

        # 2. 核心改进：结合 AST 构建高密度代码大纲
        structures = []
        
        # 只有 Python 文件支持原生的 ast 解析
        if target_path.suffix.lower() == '.py':
            try:
                tree = ast.parse(content)
                
                # 遍历顶层节点（类和函数）
                for node in tree.body:
                    # 场景 A: 处理类定义
                    if isinstance(node, ast.ClassDef):
                        # 获取类的内置 Docstring 摘要
                        class_doc = ast.get_docstring(node)
                        class_doc_str = f" -> \"{class_doc.splitlines()[0][:40]}\"" if class_doc else " (无文档字符串)"
                        structures.append(f"  🏢 [Class] 行 {node.lineno}: class {node.name}{class_doc_str}")
                        
                        # 深度遍历类内部的方法
                        for sub_node in node.body:
                            if isinstance(sub_node, ast.FunctionDef):
                                func_doc = ast.get_docstring(sub_node)
                                func_doc_str = f" -> \"{func_doc.splitlines()[0][:30]}\"" if func_doc else ""
                                structures.append(f"      └─ ⚙️ [Method] 行 {sub_node.lineno}: def {sub_node.name}(){func_doc_str}")
                                
                    # 场景 B: 处理顶层独立函数定义
                    elif isinstance(node, ast.FunctionDef):
                        func_doc = ast.get_docstring(node)
                        func_doc_str = f" -> \"{func_doc.splitlines()[0][:40]}\"" if func_doc else " (无文档字符串)"
                        structures.append(f"  ⚙️ [Function] 行 {node.lineno}: def {node.name}(){func_doc_str}")
                        
            except SyntaxError:
                structures.append("  ⚠️ [警告] 该 Python 文件当前存在语法错误，无法完成 AST 树解析。")
        else:
            structures.append(f"  ℹ️ [非Python文件] 该工具目前针对 {target_path.suffix} 文件仅支持物理属性和头尾切片预览。")

        # 3. 极致安全的头尾切片采样（压缩预览行数，降低 Token 开销）
        head_preview = ""
        tail_preview = ""
        
        if total_lines <= max_preview_lines * 2:
            head_preview = "\n".join(lines)
        else:
            head_preview = "\n".join(lines[:max_preview_lines])
            tail_preview = "\n".join(lines[-max_preview_lines:])

        # 4. 组装摘要报告
        summary_report = [
            f"=== 📄 文件元信息 ===",
            f"文件路径: {file_path}",
            f"文件大小: {file_size_kb:.2f} KB",
            f"总代码行: {total_lines} 行",
            f"\n=== 🌲 架构大纲 ===",
            "\n".join(structures) if structures and any(s.strip() for s in structures) else "  (未提取到明显的类或函数结构)",
            f"\n=== 🔍 代码头部预览 (前 {max_preview_lines} 行) ===",
            head_preview.strip(),
        ]
        
        if tail_preview:
            summary_report.extend([
                f"\n... (中间隐去 {total_lines - max_preview_lines * 2} 行代码) ...",
                f"\n=== 🔍 代码尾部预览 (后 {max_preview_lines} 行) ===",
                tail_preview.strip(),
            ])
            
        return "\n".join(summary_report)
        
    except Exception as e:
        return f"❌ 错误：分析文件失败。原因：{str(e)}"




PROTECTED_FILES = {
    ".env", 
}

@tool
def delete_files(file_paths: Union[str, List[str]], reason: str,state: Annotated[dict, InjectedState],runtime:ToolRuntime):
    """
    批量或单个删除废弃的模块、代码文件或临时文件。
    
    Args:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
              正确示例: 'core/main.py', 'test.py'
              错误示例: 'generated/test.py'
        reason: 为什么要删除这些文件？。
        state: 无需传入,会自动注入
        runtime:  无需传入,会自动注入
    """
    if not reason or len(reason.strip()) < 5:
        return "拒绝执行：调用删除工具必须提供详细、合理的理由（至少5个字）。"

    # 统一转化为列表处理，兼容单文件和多文件输入
    paths_to_delete = [file_paths] if isinstance(file_paths, str) else file_paths
    
    if not paths_to_delete:
        return "提示：未传入任何有效的删除路径。"

    success_results = []
    failed_results = []
    
    # 1. 锚定工作区根目录的绝对路径
    workspace_real_path = Path(GENERATED_DIR).resolve()
    new_file_ledger = state['file_ledger']

    # 逐个文件执行安全检查与删除
    for path in paths_to_delete:
        try:
            # 2. 计算目标绝对路径并解析符号链接，防止 ../.. 路径遍历攻击
            target_real_path = Path(workspace_real_path, path).resolve()
            
            # 3. 严格的安全边界检查：目标路径必须以工作区根目录为前缀
            if workspace_real_path not in target_real_path.parents and target_real_path != workspace_real_path:
                failed_results.append(f"'{path}' (拒绝：严禁越权访问工作区外部目录)")
                continue

            # 4. 检查是否试图删除根目录本身
            if target_real_path == workspace_real_path:
                failed_results.append(f"'{path}' (拒绝：严禁删除整个工作区根目录)")
                continue

            # 5. 检查目标是否存在（放在路径越界检查之后，防止探测外部敏感文件）
            if not target_real_path.exists():
                success_results.append(f"'{path}' (文件或目录本就不存在，无需处理)")
                continue

            # 6. 检查是否命中核心配置文件黑名单
            base_name = target_real_path.name.lower()
            if base_name in PROTECTED_FILES:
                failed_results.append(f"'{path}' (拒绝：涉及核心配置文件，严禁删除)")
                continue
                
            # 7. 安全通过，执行物理删除
            if target_real_path.is_dir():
                shutil.rmtree(target_real_path)
            else:
                target_real_path.unlink()

            # 更新file_ledger状态，移除已删除的文件条目
            if path in new_file_ledger:
                new_file_ledger[path] = None

                
        except Exception as e:
            failed_results.append(f"'{path}' (删除失败，原因: {str(e)})")

    # --- 组装结构化报告反馈给 LangGraph 状态流 ---
    report = [f"=== 批量删除操作报告 ===", f"操作原因: {reason}"]
    if success_results:
        report.append("\n✅ 成功/已就绪的项目:")
        report.extend([f"  - {item}" for item in success_results])
    if failed_results:
        report.append("\n❌ 遭拦截/失败的项目:")
        report.extend([f"  - {item}" for item in failed_results])

    return Command(
        update={
            'file_ledger': new_file_ledger,
            'messages': [
                    ToolMessage(
                        content='\n'.join(report),
                        tool_call_id=runtime.tool_call_id,
                    )
            ]
        }
    )

# result = inspect_file_summary.invoke({
#     'file_path': 'test.py'
# })
# print(result)