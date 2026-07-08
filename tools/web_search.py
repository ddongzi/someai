import os
import json
from langchain_core.tools import tool
from langchain_tavily import TavilySearch  # 最新推荐的官方标准导入路径


@tool
def query_python_docs(query: str = "python最新版本中注解有什么变化？") -> str:
    """
    专门用于在 Python 官方文档中搜索与查询技术细节（如注解变化、语法特性、标准库）。
    当 Agent 需要核实最新的 Python 特性或查阅官方文档指导时，应调用此工具。
    
    参数:
        query: 具体的中文或英文自然语言搜索词。
    返回:
        JSON 格式的字符串，包含官方文档匹配到的标题、URL 及文本片段。
    """
    # 健壮性检查：确保配置了环境变量
    if not os.environ.get("TAVILY_API_KEY"):
        return "错误：未检测到环境变量 TAVILY_API_KEY，请在 .env 中进行配置。"

    try:
        # 正确做法 1：在实例化工具时就约束好搜索行为
        # max_results 必须带 's'，include_domains 只能传入纯主域名
        search_tool = TavilySearch(
            max_results=3,                         # 限制返回前3个结果，防止单个结果信息不全
            include_domains=["docs.python.org"],   # 🔥 精准限定在 Python 官方文档网站中检索
            search_depth="advanced"                # 面对最新语法注解等深度问题，建议使用高级搜索
        )
        
        # 正确做法 2：直接使用自然语言 query 作为参数进行调用
        response = search_tool.invoke({"query": query})
        
        # 格式化输出为规范的字符串返回给大模型（LLM 读 JSON 字符串更稳定）
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return f"调用 TavilySearch 搜索失败，错误原因: {str(e)}"
