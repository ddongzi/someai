import re
from langchain.tools import tool

@tool
def apply_search_replace(original: str, diff: str) -> str:
    """
    使用SEARCH/REPLACE 块来修改文本。
    
    参数:
    original: 需要被修改的完整原始字符串。
    diff: 包含一个或多个 <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE 格式的文本块。
    """
    # 匹配 SEARCH/REPLACE 块，允许块前后有任意空白或换行
    pattern = r"<<<<<<< SEARCH\s*\n([\s\S]*?)\n\s*=======\s*\n([\s\S]*?)\n\s*>>>>>>> REPLACE"
    matches = re.findall(pattern, diff)
    
    if not matches:
        raise ValueError("未在 diff 中检测到任何符合格式的 SEARCH/REPLACE 块。")
        
    modified = original
    for search_text, replace_text in matches:
        # 移除部分 LLM 生成时可能多带的头尾空行/空格干扰（保留核心缩进）
        search_cleaned = search_text.rstrip('\r\n')
        replace_cleaned = replace_text.rstrip('\r\n')
        
        # 极端情况：如果 SEARCH 块为空，代表在文件头插入
        if not search_cleaned:
            modified = replace_text + modified
            continue

        # 检查搜索块在源码中的出现次数
        count = modified.count(search_cleaned)
        if count == 0:
            raise ValueError(
                f"【匹配失败】无法在源码中找到对应的搜索块。请检查缩进或断句是否完全一致：\n"
                f"=======[期望搜索的内容]=======\n{search_cleaned}\n=============================="
            )
        elif count > 1:
            raise ValueError(
                f"【歧义错误】搜索块在源码中出现了 {count} 次。请提供更长、更具唯一性的上下文：\n"
                f"=======[存在歧义的内容]=======\n{search_cleaned}\n=============================="
            )
            
        # 确定性精准替换
        modified = modified.replace(search_cleaned, replace_cleaned, 1)
            
    return modified


