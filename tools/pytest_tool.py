import sys
import subprocess
from pathlib import Path
from langchain_core.tools import tool
from globals.logger import run_logger
from globals import GENERATED_DIR

@tool
def run_pytest(test_file: str, timeout: int = 120) -> str:
    """
    运行指定的 pytest 测试文件并返回完整的测试输出结果。
    
    Args:
        test_file: 位于项目内部的相对文件路径。
        timeout: 测试执行的超时时间（秒），默认 120 秒。
    Return:
        包含测试结果（通过、失败、报错或超时）的详细控制台文本输出。
    """
    try:
        # 1. 安全与路径解析
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, test_file).resolve()
        
        # 防止大模型利用 ../ 逃逸出项目根目录
        if not str(target_path).startswith(str(base_path)):
            return f"❌ 错误：拒绝访问。路径 '{test_file}' 超出了允许的项目根目录。"
            
        # 2. 检查测试文件是否存在
        if not target_path.exists() or not target_path.is_file():
            return f"❌ 错误：未找到测试文件 '{test_file}'，请确认文件路径是否正确。"

        # 3. 调用子进程执行 pytest
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(target_path),
                "-q"
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # 4. 组装标准输出与错误输出
        output = result.stdout + "\n" + result.stderr
        
        # 同步记录到你的系统日志中
        run_logger.info(f"Pytest 执行日志 ({test_file}):\n{output}")

        # 5. 根据退出状态码（Return Code）格式化返回给大模型的结果
        if result.returncode == 0:
            return f"✅ 测试通过！文件 '{test_file}' 所有测试用例执行成功。\n\n【控制台输出】:\n{output}"
        else:
            return f"❌ 测试未通过。文件 '{test_file}' 存在失败的用例或语法错误（状态码: {result.returncode}）。\n\n【错误详情】:\n{output}"

    except subprocess.TimeoutExpired:
        error_msg = f"⏱️ 错误：测试执行超时（超过 {timeout} 秒），请检查是否存在死循环或阻塞操作。"
        run_logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ 错误：执行测试时发生未知异常。原因：{str(e)}"
        run_logger.error(error_msg)
        return error_msg
