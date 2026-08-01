import re
from pathlib import Path
from langchain_core.tools import tool
from globals import GENERATED_DIR

@tool
def apply_search_replace(file_path: str, diff: str) -> str:
    """
    使用一个或多个短小精悍的 SEARCH/REPLACE 块精确修改指定的本地文件。
    
    Args:
        file_path: 位于项目内部的相对文件路径。
        diff: 包含一个或多个差异比对块的文本，格式严格如下：
            <<<<<<< SEARCH
            [需要被替换的精确原始文本]
            =======
            [替换后的新文本]
            >>>>>>> REPLACE
    Return:
        修改成功提示，或具体的错误原因。
    Note:
        1. search块尽量局部短小.
        2. 如果需要大面积修改,也应该将其拆分多个块,
    """
    try:
        # 1. 路径安全解析与校验
        base_path = Path(GENERATED_DIR).resolve()
        target_path = Path(base_path, file_path).resolve()
        
        if not str(target_path).startswith(str(base_path)):
            return f"❌ 错误：拒绝访问。路径 '{file_path}' 超出了项目根目录。"
            
        if not target_path.exists() or not target_path.is_file():
            return f"❌ 错误：未找到文件 '{file_path}'，请确认路径是否正确或文件是否已创建。"

        # 2. 读取本地最新文件内容
        content = target_path.read_text(encoding="utf-8")

        # 3. 解析所有的 SEARCH/REPLACE 块
        # 使用正向预查和非贪婪匹配捕获所有的块
        pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
        blocks = re.findall(pattern, diff, re.DOTALL)
        
        if not blocks:
            return "❌ 错误：未在 diff 参数中检测到符合格式的 <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE 块。"

        # 4. 逐个块进行匹配和替换
        modified_content = content
        for idx, (search_text, replace_text) in enumerate(blocks, 1):
            # 严格检查是否存在且唯一
            count = modified_content.count(search_text)
            if count == 0:
                return f"❌ 错误：第 {idx} 个 SEARCH 块匹配失败。找不到指定的原始文本，请检查空格、换行或拼写是否完全一致。"
            if count > 1:
                return f"❌ 错误：第 {idx} 个 SEARCH 块存在歧义。在文件中找到了 {count} 处相同的文本，请扩大 SEARCH 块的范围以确保唯一性。"
            
            # 执行精确替换
            modified_content = modified_content.replace(search_text, replace_text)

        # 5. 将修改后的内容写回磁盘
        target_path.write_text(modified_content, encoding="utf-8")
        
        return f"✅ 成功：文件 '{file_path}' 已成功应用 {len(blocks)} 个块的修改。"

    except Exception as e:
        return f"❌ 错误：修改文件时发生异常。原因：{str(e)}"
