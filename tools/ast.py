import ast
import os
from typing import Dict, List, Any, Optional
import logging
logger = logging.getLogger(__name__)

class ASTNodeType:
    """
    AST 节点类型.
    支持 全局变量、函数、类、import、from导入、可执行语句、异步函数.
    """
    GLOBAL_VARIABLE = "global_variable"
    FUNCTION = "function"
    CLASS = "class"
    IMPORT = "import"
    FROM_IMPORT = "from_import"
    EXECUTABLE_STATEMENT = "executable_statement"
    ASYNC_FUNCTION = "async_function"

class ASTParser:
    """
    将py文件 的 ast 读到 结构化JSON.
    支持 全局变量、函数、类、import、from导入、可执行语句、异步函数.

    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.code_lines: List[str] = []
        self.tree: Optional[ast.Module] = None
        self._load_and_parse()

    def _load_and_parse(self):
        """加载文件并转换为 AST 树"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"找不到目标文件: {self.file_path}")
            
        with open(self.file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
            self.code_lines = source_code.splitlines()
            self.tree = ast.parse(source_code, filename=self.file_path)

    def _get_end_line(self, node: ast.AST) -> int:
        """获取节点的结束行号"""
        return getattr(node, "end_lineno", node.lineno)

    def _get_code_preview(self, start_line: int, end_line: int) -> str:
        """安全获取单行或多行代码的简短预览"""
        try:
            if start_line == end_line:
                return self.code_lines[start_line - 1].strip()
            # 多行代码只取第一行加上省略号，避免 JSON 体积过大
            return self.code_lines[start_line - 1].strip() + " ..."
        except IndexError:
            return ""

    def _parse_function_node(self, node: Any, is_method: bool = False) -> Dict[str, Any]:
        """核心解析器：处理普通函数、异步函数和类方法"""
        # 1. 提取参数
        arguments = [arg.arg for arg in node.args.args]
        
        # 2. 提取装饰器名称
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(f"@{dec.id}")
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(f"@{dec.func.id}")
            else:
                decorators.append("@custom_decorator")

        return {
            "name": node.name,
            "type": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            "is_method": is_method,
            "start_line": node.lineno,
            "end_line": self._get_end_line(node),
            "arguments": arguments,
            "decorators": decorators,
            "docstring": ast.get_docstring(node) or ""
        }

    def _parse_class_node(self, node: ast.ClassDef) -> Dict[str, Any]:
        """核心解析器：处理类以及嵌套的类方法"""
        methods = []
        base_classes = []

        # 1. 提取父类名称
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                base_classes.append(f"{base.value.id}.{base.attr}")

        # 2. 遍历类内部节点，只提取方法
        for sub_node in node.body:
            if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._parse_function_node(sub_node, is_method=True))

        return {
            "name": node.name,
            "type": "class",
            "start_line": node.lineno,
            "end_line": self._get_end_line(node),
            "base_classes": base_classes,
            "docstring": ast.get_docstring(node) or "",
            "methods": methods
        }

    def to_structured_json(self) -> Dict[str, Any]:
        """
        外部接口，结构化json
        """
        if not self.tree:
            return {}

        manifest = {
            "file_path": self.file_path,
            "total_lines": len(self.code_lines),
            "imports": [],
            "global_variables": [],
            "classes": [],
            "top_level_functions": [],
            "executable_statements": []
        }

        for node in self.tree.body:
            # 情况 1: 类 (Class)
            if isinstance(node, ast.ClassDef):
                manifest["classes"].append(self._parse_class_node(node))
            
            # 情况 2: 顶级独立函数 (Function / Async Function)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                manifest["top_level_functions"].append(self._parse_function_node(node, is_method=False))
            
            # 情况 3: 全局变量赋值 (Global Variable)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        start = node.lineno
                        end = self._get_end_line(node)
                        manifest["global_variables"].append({
                            "name": target.id,
                            "type": "global_variable",
                            "start_line": start,
                            "end_line": end,
                            "value_preview": self._get_code_preview(start, end).split("=")[-1].strip(),
                            "docstring": ""
                        })
            
            # 情况 4: 模块顶层导入 (Import / ImportFrom)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = []
                import_type = "standard"
                
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                else:  # ImportFrom
                    import_type = "from_import"
                    modules = [alias.name for alias in node.names]
                    
                manifest["imports"].append({
                    "name": node.module if hasattr(node, 'module') and node.module else modules[0],
                    "type": "import",
                    "import_type": import_type,
                    "start_line": node.lineno,
                    "end_line": self._get_end_line(node),
                    "modules": modules
                })

            # 情况 5: 独立的顶层控制流（如 if __name__ == '__main__'）或纯执行语句
            elif isinstance(node, ast.If):
                # 针对性识别 python 的 main 入口块
                if (isinstance(node.test, ast.Compare) and 
                    isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__'):
                    statement_type = "main_block"
                    name = "__main__"
                else:
                    statement_type = "top_level_if"
                    name = "top_if"

                start = node.lineno
                end = self._get_end_line(node)
                manifest["executable_statements"].append({
                    "name": name,
                    "type": "executable_statement",
                    "statement_type": statement_type,
                    "start_line": start,
                    "end_line": end,
                    "code_preview": self._get_code_preview(start, start),
                    "docstring": ""
                })

            # 情况 5 (补充): 顶层的纯表达式/函数调用 (如 print(), setup())
            elif isinstance(node, ast.Expr):
                # 排除纯字符串字面量（比如文件开头的多行注释）
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    continue
                
                start = node.lineno
                end = self._get_end_line(node)
                manifest["executable_statements"].append({
                    "name": "top_expression",
                    "type": "executable_statement",
                    "statement_type": "top_level_call",
                    "start_line": start,
                    "end_line": end,
                    "code_preview": self._get_code_preview(start, end),
                    "docstring": ""
                })

        return manifest
import json

from langchain.tools import tool
# @tool
def ast_search(file_path:str, name, type, **kwargs) -> dict:
    """
    在指定的 Python 文件中，搜索特定类型-名字的 代码片段信息。
    
    Args:
        file_path (str): 目标 Python 文件的绝对或相对路径。
        name (str): 想要查找标识名（例如 'get_user'）。
        type (str): 标识名的类型，可选值包括: 'async_function', 'global_variable', 'function', 'class','import','from_import','executable_statement'
        **kwargs: 可选参数        
    Returns:
        Dict: 返回包含匹配的字典，字典包含 name, type, start_line, end_line, docstring 等字段。
    """
    # cache
    # 1. 传入待解析的文件
    formatter = ASTParser(file_path=file_path)

    # 2. 转换为全结构化 JSON
    result_json = formatter.to_structured_json()
    search_result = {}
    if type == ASTNodeType.GLOBAL_VARIABLE:
        for item in result_json['global_variables']:
            if item['name'] == name:
                search_result = item
                break
    elif type == ASTNodeType.FUNCTION:
        for item in result_json['top_level_functions']:
            if item['name'] == name:
                search_result = item
                break
    elif type == ASTNodeType.CLASS:
        for item in result_json['classes']:
            if item['name'] == name:
                search_result = item
                break
    elif type == ASTNodeType.IMPORT:
        for item in result_json['imports']:
            if item['name'] == name:
                search_result = item
                break
    elif type == ASTNodeType.FROM_IMPORT:
        for item in result_json['imports']:
            if item['name'] == name and item['import_type'] == 'from_import':
                search_result = item
                break
    elif type == ASTNodeType.EXECUTABLE_STATEMENT:
        for item in result_json['executable_statements']:
            if item['name'] == name:
                search_result = item
                break
    elif type == ASTNodeType.ASYNC_FUNCTION:
        for item in result_json['top_level_functions']:
            if item['name'] == name:
                search_result = item
                break

    return search_result


import linecache
import os
from typing import List

def read_file_lines(filepath: str, start_line: int, end_line: int) -> List[str]:
    """
    读取指定文件中 [start_line, end_line] 区间内的所有行（闭区间，基于 1 开始计数）。
    
    Args:
        filepath (str): 文件的路径。
        start_line (int): 起始行号（从 1 开始）。
        end_line (int): 结束行号（包含该行）。
        
    Returns:
        List[str]: 包含读取到的每行内容的字符串列表。
    """
    # 基础边界安全检查
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"找不到文件: {filepath}")
    if start_line < 1 or end_line < start_line:
        return []
    
    lines = []
    # linecache.getline 是从 1 开始计数的
    for line_num in range(start_line, end_line + 1):
        line = linecache.getline(filepath, line_num)
        if not line:
            # 如果读到空字符串，说明已经超过了文件的最大行数，直接提前结束
            break
        lines.append(line)
        
    return lines


file_path = "./tools/ast_test.py"
formatter = ASTParser(file_path=file_path)
result_json = formatter.to_structured_json()

# 按理来说，智能有一
search_result = ast_search(file_path=file_path, name='hello', type='function')

read_result = read_file_lines(filepath=file_path, start_line=search_result['start_line'],end_line= search_result['end_line'])
print(read_result)