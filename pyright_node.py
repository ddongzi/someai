"""
静态检查node

"""
import os
import json
from globals import GraphState
import subprocess
import logging
logger = logging.getLogger(__name__)

def _do_pyright(code:str) -> dict:
    temp_file = './temp/pyright_code.py'
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(code)
    
    errors = []
    try:
        # 执行 pyright 命令行工具，并要求以 JSON 格式输出结果
        result = subprocess.run(
            ["pyright", "--outputjson", temp_file],
            capture_output=True,
            text=True,
            check=False # 允许返回非 0 退出码
        )
        # logger.info(f'pyright cli result :{result}')
        # 解析 JSON 诊断报告
        if result.stdout:
            data = json.loads(result.stdout)
            diagnostics = data.get("generalDiagnostics", [])
            for diag in diagnostics:
                severity = diag.get("severity", "error")
                # 过滤出错误和警告
                if severity in ["error", "warning"]:
                    msg = f"Line {diag['range']['start']['line'] + 1}: {diag['message']}"
                    errors.append(msg)
                    
    except Exception as e:
        errors.append(f"Failed to execute Pyright CLI: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    return {
        'errors':errors
    }

def pyright_node(state: GraphState) -> dict:
    """Pyright 静态检查节点, 支持各类coder, test_writer"""
    logger.info(f"[pyright] 静态检查....")
    result = {}
    if 'code' in state['pyright_target']:
        errors = _do_pyright(state['code'])
        if not errors:
            result['code'] = errors

    if 'test_code' in state['pyright_target']:
        errors = _do_pyright(state['test_code'])
        if not errors:
            result['test_code'] = errors
    logger.info(f"pyright node ok. {result}")
    
    return {
        'pyright_target': set(), # 消耗完了
        'pyright_result': result
    }