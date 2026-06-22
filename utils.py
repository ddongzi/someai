import re

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