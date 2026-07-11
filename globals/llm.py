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


def call_llm(prompt:str, logger:Logger)->str:
    logger.info(f'prompt :{prompt}')
    full_content = ""
    full_chunk = None
    logger.info('====LLM stream ..====')
    for chunk in llm.stream(prompt):
        if full_chunk is None:
            full_chunk = chunk
        else:
            full_chunk += chunk
        # 1. 如果有思考内容（思维链），打印出来
        if 'reasoning_content' in chunk.additional_kwargs and chunk.additional_kwargs['reasoning_content']:
            print(chunk.additional_kwargs['reasoning_content'], end="", flush=True)
            
        # 2. 如果思考结束，开始输出真正的文本回答
        if chunk.content:
            # 如果是刚从思考切换到正文，可以加个换行（选加）
            # print("\n\n🤖 最终回答：") 
            print(chunk.content, end="", flush=True)
            full_content += chunk.content

        # 3. 如果触发了工具调用
        if chunk.tool_calls:
            print(f"⚙️ 命中工具: {chunk.tool_calls}")

    logger.info(f'llm full chunks.\n{full_chunk}')
    logger.info(f'llm full content.\n{full_content}')
    logger.info('====LLM done ====')
    return full_content, full_chunk

