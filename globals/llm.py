from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from langchain_community.cache import SQLiteCache
from tools.search_replace_tool import apply_search_replace
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.filer import read_file, create_file,inspect_project,write_to_file
from tools.git import git_tool
from tools.rag import knowledge_search
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
import os
from logging import Logger
set_llm_cache(SQLiteCache())
# set_llm_cache(InMemoryCache())

deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

tools = [git_tool, knowledge_search, write_to_file,
          apply_search_replace,ast_search,inspect_project,
          find_symbol_references, find_symbol_definition, 
          read_file, create_file]

# llm = ChatOllama( 
#     model="qwen2.5-coder:3b",   # tool calling 不好，格式部队
#     temperature=0.1,   
#     frequency_penalty=2,       # 避免llm回复循环重复的话语
#     presence_penalty=1.0         # 🌟 辅助：惩罚重复的话题
# )
# llm = llm.bind_tools(tools=tools)

# llm = ChatOllama(
#     model="llama3.2:1b",  
#     temperature=0.1,   
#     frequency_penalty=2,       # 避免llm回复循环重复的话语
#     presence_penalty=1.0         # 🌟 辅助：惩罚重复的话题
# )
# llm = llm.bind_tools(tools=tools)
llm = ChatDeepSeek(
    api_key=deepseek_key,
    base_url="https://api.deepseek.com",
    model="deepseek-chat",  # 云端代码模型
    temperature=0,
    #   frequency_penalty=2
)
llm = llm.bind_tools(tools=tools)

def call_llm(prompt: str, logger: Logger) -> str:
    logger.info(f'prompt :{prompt}')
    full_content = ""
    full_chunk = None
    
    # 状态标记：'thinking', 'answering', 'tool_calling', None
    current_mode = None 
    
    logger.info('====LLM stream ..====')
    for chunk in llm.stream(prompt):
        if full_chunk is None:
            full_chunk = chunk
        else:
            full_chunk += chunk

        # 1. 处理思考过程 (Reasoning)
        reasoning = chunk.additional_kwargs.get('reasoning_content', '')
        if reasoning:
            if current_mode != 'thinking':
                print("\n🤔 [思考中] ", end="", flush=True)
                current_mode = 'thinking'
            print(reasoning, end="", flush=True)
            continue  

        # 2. 处理最终答案 (Content)
        if chunk.content:
            if current_mode != 'answering':
                print("\n✨ [给出回答] ", end="", flush=True)
                current_mode = 'answering'
            print(chunk.content, end="", flush=True)
            full_content += chunk.content

        # 3. 处理工具调用 (Tool Calls)
        # 注意：流式传输中 tool_calls 的首帧可能为空，后续帧只包含参数碎片
        if chunk.tool_calls:
            if current_mode != 'tool_calling':
                print("\n⚙️ [命中工具,构建工具]", end="", flush=True)
                current_mode = 'tool_calling'
            # 流式过程中不重复打印未组装完成的 chunk.tool_calls 结构，保持控制台整洁
            print(".", end="", flush=True) 

    logger.info('====LLM done ====')
    return full_content, full_chunk
