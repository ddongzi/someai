#!/usr/bin/env python3
"""
Tool 扫描器 — 扫描指定目录下所有 @tool 标记的函数，提取 JSON Schema 供下游使用。

用途：
  - 从项目工具集中自动生成 OpenAI Function Calling / MCP 等协议的 JSON Schema
  - 自动过滤 state/runtime 等注入参数，提取 docstring 中的参数描述

用法：
  python3 scan_tools.py <目录>             # 美化 JSON 输出到 stdout
  python3 scan_tools.py <目录> -o compact  # 紧凑 JSON 输出
  python3 scan_tools.py <目录> -f out.json # 写入文件

输出格式示例：
  [
    {
      "name": "tool_name",
      "description": "工具的整体描述",
      "schema": {
        "type": "object",
        "properties": {
          "param1": { "type": "string",  "description": "参数说明" },
          "param2": { "type": "integer", "description": "参数说明" }
        },
        "required": ["param1"]
      },
      "mock_output": "{\"result\": \"ok\"}"
    }
  ]
"""

import sys
import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional

# 防止本地工具目录遮蔽 Python 标准库模块（如 tools/ast.py 遮蔽 stdlib ast）
_script_dir = str(Path(__file__).resolve().parent)
if _script_dir in sys.path:
    sys.path.remove(_script_dir)
sys.path = [p for p in sys.path if Path(p).resolve() != Path(_script_dir)]

import ast

# Python 类型 -> JSON Schema 类型映射
PYTHON_TO_JSON_TYPE = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "None": "null",
    "NoneType": "null",
    "NoneType": "null",
}

# 内置注入类型，不应出现在 schema 中
INJECTED_TYPE_PATTERNS = [
    "InjectedState",
    "ToolRuntime",
]


def is_tool_decorated(node: ast.FunctionDef) -> bool:
    """检查函数是否被 @tool 装饰器标记"""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "tool":
            return True
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "tool":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
            return True
    return False


def _get_annotation_str(node) -> Optional[str]:
    """将 AST 类型注解节点转为字符串"""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _get_default_value(node) -> Optional[str]:
    """将 AST 默认值节点转为可读的值"""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _is_injected_param(annotation_str: Optional[str]) -> bool:
    """判断参数是否为框架注入参数（state/runtime）"""
    if annotation_str is None:
        return False
    for pattern in INJECTED_TYPE_PATTERNS:
        if pattern in annotation_str:
            return True
    return False


def _python_type_to_json_type(type_str: Optional[str]) -> str:
    """将 Python 类型注解字符串转为 JSON Schema 类型"""
    if type_str is None:
        return "string"

    type_str = type_str.strip()

    # 直接映射
    if type_str in PYTHON_TO_JSON_TYPE:
        return PYTHON_TO_JSON_TYPE[type_str]

    # Optional[...] 提取内部类型
    m = re.match(r'Optional\[(.+)\]', type_str, re.IGNORECASE)
    if m:
        return _python_type_to_json_type(m.group(1))

    # Union[a, b] → 取第一个非 None 类型
    m = re.match(r'Union\[(.+)\]', type_str, re.IGNORECASE)
    if m:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",")]
        for part in parts:
            if part.lower() not in ("none", "nonetype"):
                return _python_type_to_json_type(part)

    # Annotated[a, ...] → 提取 a
    m = re.match(r'Annotated\[(.+?),\s*', type_str)
    if m:
        return _python_type_to_json_type(m.group(1))

    # List[...] → array
    if re.match(r'List\[', type_str, re.IGNORECASE):
        return "array"

    # Dict[...] → object
    if re.match(r'Dict\[', type_str, re.IGNORECASE):
        return "object"

    # 其他复杂类型默认 fallback
    if re.match(r'^\w+$', type_str):
        return "string"

    return "string"


def _parse_param_descriptions(docstring: str, param_names: List[str]) -> Dict[str, str]:
    """
    从 docstring 中解析每个参数的描述。
    支持 Google-style (Args:/参数:) 和简单格式。
    """
    if not docstring:
        return {}

    param_descs = {}

    # 尝试匹配 Args/参数/Arguments 区块
    block_patterns = [
        r'(?:^|\n)\s*(?:Args|Arguments|参数|Parameters)\s*:\s*\n',
    ]

    for bp in block_patterns:
        m = re.search(bp, docstring)
        if m:
            block_start = m.end()
            remaining = docstring[block_start:]
            # 下一个区块标记：Returns/Yields/Raises/Note/Example 等
            next_section = re.search(
                r'\n\s*(?:Returns?|Yields?|Raises?|Note|Example|Return|注意|返回|示例)\s*:',
                remaining
            )
            if next_section:
                block_text = remaining[:next_section.start()]
            else:
                block_text = remaining

            # 逐行解析
            current_param = None
            # 用于匹配任何参数行（含不在 param_names 中的，用于检测参数边界）
            any_param_re = re.compile(r'^\s*(\w+)\s*(?:\(.*?\))?\s*:')
            for line in block_text.split("\n"):
                # 先尝试匹配目标参数（支持 0 缩进的中文格式和无缩进格式）
                param_match = re.match(
                    r'\s*(' + '|'.join(re.escape(n) for n in param_names) + r')\s*(?:\(.*?\))?\s*:\s*(.*)',
                    line
                )
                if param_match:
                    current_param = param_match.group(1)
                    param_descs[current_param] = param_match.group(2).strip()
                elif current_param and line.strip():
                    stripped = line.strip()
                    # 如果这行看起来是另一个参数定义（即使不在目标列表中），停止续写
                    if any_param_re.match(line):
                        current_param = None
                    elif not re.match(r'^\S+:', stripped):
                        param_descs[current_param] += " " + stripped

            break  # 只处理第一个匹配的区块

    return param_descs


def _parse_func_description(docstring: str) -> str:
    """提取函数整体描述（docstring 的第一段，在 Args 等区块之前）"""
    if not docstring:
        return ""

    lines = docstring.split("\n")
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            desc_lines.append("")
            continue
        # 遇到区块标记则停止
        if re.match(r'^(?:Args|Arguments|参数|Parameters|Returns?|Yields?|Raises?|Note|Example|Return|注意|返回|示例)\s*:', stripped):
            break
        desc_lines.append(stripped)

    # 去掉末尾空行
    while desc_lines and desc_lines[-1] == "":
        desc_lines.pop()

    return " ".join(desc_lines).strip()


def extract_function_info(func_node: ast.FunctionDef, file_path: str) -> Optional[dict]:
    """从 AST FunctionDef 节点提取函数信息，构建 JSON Schema 格式输出"""
    name = func_node.name
    raw_doc = ast.get_docstring(func_node)
    docstring = raw_doc.strip() if raw_doc else ""

    args = func_node.args

    # ---- 收集所有有名字的用户参数 ----
    raw_params = []

    for arg in args.posonlyargs:
        raw_params.append({
            "name": arg.arg,
            "type": _get_annotation_str(arg.annotation),
            "default": None,
            "has_default": False,
            "kind": "positional_only",
        })

    num_args = len(args.args)
    num_defaults = len(args.defaults)
    no_default_count = num_args - num_defaults

    for i, arg in enumerate(args.args):
        if arg.arg == "self":
            continue
        default = None
        has_default = False
        if i >= no_default_count:
            default_idx = i - no_default_count
            default = _get_default_value(args.defaults[default_idx])
            has_default = True
        raw_params.append({
            "name": arg.arg,
            "type": _get_annotation_str(arg.annotation),
            "default": default,
            "has_default": has_default,
            "kind": "positional_or_keyword",
        })

    kw_defaults = args.kw_defaults or []
    for i, arg in enumerate(args.kwonlyargs):
        default = None
        has_default = False
        if i < len(kw_defaults) and kw_defaults[i] is not None:
            default = _get_default_value(kw_defaults[i])
            has_default = True
        raw_params.append({
            "name": arg.arg,
            "type": _get_annotation_str(arg.annotation),
            "default": default,
            "has_default": has_default,
            "kind": "keyword_only",
        })

    # 过滤掉注入参数 (state, runtime)
    user_params = [p for p in raw_params if not _is_injected_param(p["type"])]

    # 从 docstring 解析各参数的描述
    param_names = [p["name"] for p in user_params]
    param_descs = _parse_param_descriptions(docstring, param_names)

    # 整体描述（docstring 第一段）
    description = _parse_func_description(docstring)

    # ---- 构建 JSON Schema ----
    properties = {}
    required = []

    for p in user_params:
        json_type = _python_type_to_json_type(p["type"])
        prop = {"type": json_type}

        # 参数描述：优先 docstring 提取，否则用类型注解作为 fallback
        p_desc = param_descs.get(p["name"], "")
        if not p_desc and p["type"]:
            p_desc = f"类型: {p['type']}"
        prop["description"] = p_desc

        if p["default"] is not None:
            prop["default"] = p["default"]

        properties[p["name"]] = prop

        if not p["has_default"]:
            required.append(p["name"])

    schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return {
        "name": name,
        "description": description,
        "schema": schema,
        "mock_output": '{"result": "ok"}',
    }


def scan_file(file_path: Path) -> List[dict]:
    """扫描单个 .py 文件中的 @tool 函数"""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"警告：无法解析文件 {file_path}：{e}", file=sys.stderr)
        return []

    tools = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_tool_decorated(node):
                info = extract_function_info(node, str(file_path))
                if info:
                    tools.append(info)

    return tools


def scan_directory(directory: str) -> List[dict]:
    """递归扫描目录下所有 .py 文件"""
    dir_path = Path(directory).resolve()
    if not dir_path.exists():
        print(f"错误：目录 '{directory}' 不存在", file=sys.stderr)
        sys.exit(1)
    if not dir_path.is_dir():
        print(f"错误：'{directory}' 不是一个目录", file=sys.stderr)
        sys.exit(1)

    all_tools = []
    for py_file in sorted(dir_path.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        tools = scan_file(py_file)
        all_tools.extend(tools)

    return all_tools


def main():
    parser = argparse.ArgumentParser(
        description="扫描目录下所有 @tool 标记的函数，输出 JSON Schema 格式"
    )
    parser.add_argument(
        "directory",
        help="要扫描的目录路径",
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "compact"],
        default="json",
        help="输出格式: json (美化,默认), compact (紧凑一行)",
    )
    parser.add_argument(
        "--outfile", "-f",
        default=None,
        help="将结果写入指定文件 (默认打印到 stdout)",
    )

    args = parser.parse_args()
    tools = scan_directory(args.directory)

    if not tools:
        msg = f"未在目录 '{args.directory}' 中找到任何 @tool 标记的函数。"
        print(msg, file=sys.stderr)
        return

    indent = None if args.output == "compact" else 2
    result = json.dumps(tools, ensure_ascii=False, indent=indent)

    if args.outfile:
        Path(args.outfile).write_text(result + "\n", encoding="utf-8")
        print(f"结果已写入 {args.outfile} ({len(tools)} 个工具)", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
