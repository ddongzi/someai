from langchain_tavily import TavilySearch
import os
from dotenv import load_dotenv
load_dotenv()

    
search_tool = TavilySearch(
    max_result = 1
    )
def query(query: str = "python最新版本中注解有什么变化？"):

    result = search_tool.invoke(
        {
            "query": query,
            "include_domains": ["https://docs.python.org/zh-cn/3/"] 
        }
    )
    return result