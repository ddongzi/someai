import os
import json
import subprocess
from pathlib import Path
from globals import GENERATED_DIR
from langchain_core.tools import tool
from globals.logger import run_logger

@tool
def static_check(file_path: str) -> str:
    """
    对指定的本地 Python 文件进行 Pyright 静态类型检查与语法诊断。
    适合在修改完某个文件后，快速验证该文件是否存在语法错误、未定义变量或类型冲突。
    
    Args:
        file_path: 位于项目内部的相对文件路径
    Return:
        如果文件无问题返回成功提示；如果存在问题，返回详细的错误和警告行号及原因。
    """
    try:
        # 1. 路径安全解析与校验
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        # 防止大模型利用 ../ 逃逸出项目根目录
        if not str(target_path).startswith(str(base_path)):
            return f"❌ 错误：拒绝访问。路径 '{file_path}' 超出了允许的项目根目录。"
            
        # 2. 检查文件是否存在且是 Python 文件
        if not target_path.exists() or not target_path.is_file():
            return f"❌ 错误：未找到文件 '{file_path}'，请确认路径是否正确或文件是否已创建。"
            
        if target_path.suffix.lower() != '.py':
            return f"❌ 错误：文件 '{file_path}' 不是 Python 文件。Pyright 工具仅支持检查 .py 后缀的代码文件。"

        # 3. 执行 pyright 命令行工具，指向本地真实文件，并要求以 JSON 格式输出结果
        result = subprocess.run(
            ["pyright", "--outputjson", str(target_path)],
            capture_output=True,
            text=True,
            check=False  # 允许返回非 0 状态码（Pyright 查出错误时会返回非 0）
        )
        
        errors = []
        
        # 4. 解析 JSON 诊断报告
        if result.stdout:
            data = json.loads(result.stdout)
            diagnostics = data.get("generalDiagnostics", [])
            for diag in diagnostics:
                severity = diag.get("severity", "error")
                # 过滤出错误和警告
                if severity in ["error", "warning"]:
                    msg = f"  - [{severity}]  {diag['range']} : {diag['message']}"
                    errors.append(msg)
                    
        if not errors:
            return f"✅ 类型检查通过！文件 '{file_path}' 未检测到任何 Pyright 语法错误或类型警告。"
            
        return f"❌ 文件 '{file_path}' 静态检查发现以下问题，\n" + "\n".join(errors)

    except Exception as e:
        error_msg = f"❌ 无法对文件 '{file_path}' 执行 Pyright 静态检查。原因：{str(e)}"
        run_logger.error(error_msg)
        return error_msg
