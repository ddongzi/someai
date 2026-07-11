import os
from typing import List, Optional,Union
from langchain_core.tools import tool # 如果使用 LangChain，否则可以用标准 python 函数加 type hint
from dotenv import load_dotenv
import logging
import re
import shutil
load_dotenv()
from pathlib import Path
from langgraph.types import Command
from langchain.tools import ToolRuntime, tool
from globals.state import FileMetadata
from langchain.messages import ToolMessage
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

@tool
def read_file(file_path: str) -> str:
    """
    读取指定文本文件的完整内容。
    
    参数:
    file_path: 位于项目内部的相对文件路径。
        注意：请直接写文件名或内部子路径，绝对不要包含项目路径
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
def write_to_file(file_path: str, content: str) -> str:
    """
    完全覆盖重写文件内容
    
    Args:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
              正确示例: 'core/main.py', 'test.py'
              错误示例: 'generated/test.py'
        content: 写入的全部内容。
    Return:
        写入成功/失败响应。
    """
    try:
        # 自动创建不存在的父级目录
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"成功：文件 '{file_path}' 已被重新写入，共 {len(content)} 个字符。"
    except Exception as e:
        return f"错误：写入文件失败。原因：{str(e)}"


@tool
def create_file(file_path: str, content: str, description:str, runtime:ToolRuntime) -> str:
    """
    在目录中创建一个新文件，并写入初始内容。如果文件已存在，则会报错。
    
    参数:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
        content: 写入文件的初始文本内容。
        description: 文件用途描述
        runtime (ToolRuntime): 工具执行时的运行时上下文对象。参数会自动注入

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

        mt = FileMetadata(
            path=file_path,
            description=description,
            permission='none'
        )
        return Command(
            update={
                'file_ledger': {
                    mt["path"] : mt
                },
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
    
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

@tool
def inspect_project(state: Annotated[dict, InjectedState]) -> str:
    """
    查看项目结构,包括文件路径,文件描述

    Args: None (此工具不需要任何输入参数，由系统自动读取状态)

    Returns:
        str: 包含所有文件路径和描述的 Markdown 格式文本。
    """
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


@tool
def inspect_file_summary(file_path: str, max_preview_lines: int = 20) -> str:
    """
    获取文件摘要信息：文件完整性、行数、首尾预览行数，以及内部关键注释内容。
    
    Args:
        file_path: 位于项目内部的相对文件路径。
            注意：请直接写文件名或内部子路径，绝对不要包含项目路径
                正确示例: 'core/main.py', 'test.py'
                错误示例: 'generated/test.py'
        max_preview_lines: 头尾切片采样预览的最大行数，默认20行。
    """
    if not os.path.exists(file_path):
        return f"错误：文件 '{file_path}' 不存在。"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        file_size_kb = os.path.getsize(file_path) / 1024
        
        # --- 核心：多语言关键注释与架构大纲提取 ---
        structures = []
        
        # 1. 匹配大板块横幅或分割线注释 (如: # === 用户管理 === 或 // ----------)
        banner_pattern = re.compile(r'^\s*(#|//|/\*)\s*([-*=_]{3,}|[【★■#===].*[】★■#===])')
        
        # 2. 匹配关键高亮标签 (TODO, FIXME, NOTE, IMPORTANT)
        alert_pattern = re.compile(r'\b(TODO|FIXME|NOTE|IMPORTANT|警告|注意)\b[:：]?\s*(.*)', re.IGNORECASE)
        
        # 3. 匹配常见语言定义行的下一行（捕获紧随其后的单行函数说明或文档字串占位）
        # 比如 Python 的 def 下一行的 '''说明'''，或者 JS/Go 的函数上一行/下一行的简短注释
        definition_pattern = re.compile(r'^\s*(def|class|function|struct|impl|interface)\s+[a-zA-Z_]')

        for idx, line in enumerate(lines):
            clean_line = line.strip()
            if not clean_line:
                continue
                
            line_num = idx + 1
            
            # 策略 A: 捕捉模块横幅/分割线（帮助 AI 划分代码大板块）
            if banner_pattern.match(line):
                structures.append(f"  - Line {line_num} [板块划分]: {clean_line[:60]}")
                continue
                
            # 策略 B: 捕捉关键提醒标签
            alert_match = alert_pattern.search(clean_line)
            if alert_match and (clean_line.startswith('#') or clean_line.startswith('//') or clean_line.startswith('*')):
                structures.append(f"  - Line {line_num} [{alert_match.group(1).upper()}提示]: {alert_match.group(2)[:50]}")
                continue
            
            # 策略 C: 智能捕捉上下文文档——如果当前行是核心定义，看它周围是否有业务注释
            if definition_pattern.match(line):
                doc_found = ""
                # 向前看 1 行 (常用于 JS/TS/Go/Java 的单行函数头注释)
                if idx > 0 and (lines[idx-1].strip().startswith('//') or lines[idx-1].strip().startswith('#')):
                    doc_found = lines[idx-1].strip().lstrip('#/ \t*')
                # 向后看 1 行 (常用于 Python 的 docstring 摘要)
                elif idx < total_lines - 1 and ('"""' in lines[idx+1] or "'''" in lines[idx+1] or lines[idx+1].strip().startswith('#')):
                    doc_found = lines[idx+1].strip().replace('"""', '').replace("'''", "").strip()
                
                # 提取当前的定义名简写（去掉大括号或冒号）
                def_name = clean_line.split('{')[0].split(':')[0].strip()
                
                if doc_found:
                    structures.append(f"  - Line {line_num} [{def_name}]: 👇 注释说明 -> \"{doc_found[:40]}\"")
                else:
                    structures.append(f"  - Line {line_num} [{def_name}]: (无明文注释说明)")

        # --- 极致安全的头尾切片采样 ---
        head_preview = ""
        tail_preview = ""
        
        if total_lines <= max_preview_lines * 2:
            head_preview = "".join(lines)
        else:
            head_preview = "".join(lines[:max_preview_lines])
            tail_preview = "".join(lines[-max_preview_lines:])
            
        # --- 组装高密度、高实用性的摘要报告 ---
        summary_report = [
            f"=== 文件信息 ===",
            f"路径: {file_path}",
            f"大小: {file_size_kb:.2f} KB",
            f"总行数: {total_lines} 行",
            f"\n=== 内容大致摘要===",
            "\n".join(structures) if structures else "无内容摘要",
            f"\n=== 文件头部预览 (前 {max_preview_lines} 行) ===",
            head_preview.strip(),
        ]
        
        if tail_preview:
            summary_report.extend([
                f"\n... (中间数据省略 {total_lines - max_preview_lines * 2} 行) ...",
                f"\n=== 文件尾部预览 (后 {max_preview_lines} 行) ===",
                tail_preview.strip(),
            ])
            
        return "\n".join(summary_report)
        
    except Exception as e:
        return f"错误：分析文件失败。原因：{str(e)}"




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

