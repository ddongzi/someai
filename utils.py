import re
import tiktoken
import logging
import json
logger = logging.getLogger(__name__)

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


def draw_workflow_png(app):
    graph = app.get_graph()
    # 1. 导出原始mermaid字符串
    mermaid_text = graph.draw_mermaid()
    # 替换布局为竖向TD，增加样式
    mermaid_text = mermaid_text.replace(
        "graph LR",
        """graph TD
        classDef node fill:#f0f8ff,stroke:#2c3e50,stroke-width:1.5
        linkStyle all stroke:#555,stroke-width:1
        """
    )
    # 写入mmd文件
    with open("workflow.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_text)
    logger.info("已生成 workflow.mmd")

    png_data = graph.draw_mermaid_png()
    with open("workflow.png", "wb") as f:
        f.write(png_data)
        logger.info("workflow png saved.")


import json
import sys
import tiktoken

def calculate_total_tokens_for_pyobj(dict_values: dict, model="gpt-4o") -> int:
    """
    1. 【模型角度】计算当前 Python 字典对象（State）转化为 JSON 文本后的总 token 数量
    """
    try:
        # 为了防止某些特殊对象（如 LangChain 的 Message 对象）在 json.dumps 时报错，
        # 可以加上 default=str 将其强转为字符串，确保统计不中断
        state_text = json.dumps(dict_values, ensure_ascii=False, indent=2, default=str)
        return calculate_total_tokens_for_text(state_text, model=model)
    except Exception as e:
        print(f"❌ 序列化 Python 对象失败: {e}")
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
