from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from langchain_community.cache import SQLiteCache
from tools.search_replace_tool import apply_search_replace
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.filer import read_file, create_file,inspect_project,write_to_file
from tools.git import git_tool
from tools.pyright_check import static_check
from tools.rag import knowledge_search
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
import os
from langchain_core.tools import tool
from langchain_core.messages import messages_to_dict,AnyMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from logging import Logger
# set_llm_cache(SQLiteCache())
set_llm_cache(InMemoryCache())

deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

tools = [git_tool, knowledge_search, write_to_file,static_check,
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
base_llm = ChatDeepSeek(
    api_key=deepseek_key,
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0,
)

# 2. 编写动态绑定工具的函数
def get_llm_with_tools(tools: list):
    """
    为传入的 LLM 实例动态绑定不同的 tool 能力。
    """
    return base_llm.bind_tools(tools=tools)

from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
import json

def fmt_messages(messages: list[AnyMessage]) -> str:
    """
    格式化消息列表. (一般就是历史, 作为prompt)
    """
    msgs = []
    for msg in messages:
        # 1. 获取基础角色标签（System, Human, AI, Tool 等）
        role = msg.__class__.__name__.replace("Message", "").replace("Chunk", "")
        
        # 2. 初始化单条消息的文本段落
        msg_lines = []
        
        # 3. 针对不同类型的消息提取核心特征
        if isinstance(msg, SystemMessage):
            msg_lines.append(f"🤖 [{role}]: {msg.content}")
            
        elif isinstance(msg, HumanMessage):
            msg_lines.append(f"👤 [{role}]: {msg.content}")
            
        elif isinstance(msg, AIMessage):
            # 💡 提取 DeepSeek 特有的思维链思考过程
            reasoning = msg.additional_kwargs.get("reasoning_content", "")
            if reasoning:
                msg_lines.append(f"🤔 [AI 思考过程]:\n{reasoning.strip()}")
            
            # 💡 提取最终文本回答
            if msg.content:
                msg_lines.append(f"✨ [{role} 回答]:\n{msg.content.strip()}")
                
            # 💡 提取工具调用请求 (关键点)
            if msg.tool_calls:
                msg_lines.append(f"⚙️ [{role} 请求调用工具]:")
                for tool in msg.tool_calls:
                    # 美化格式化参数字典，使其在日志中易读
                    try:
                        args_str = json.dumps(tool.get('args', {}), ensure_ascii=False, indent=2)
                    except Exception:
                        args_str = str(tool.get('args', {}))
                    msg_lines.append(f"   - 工具名: {tool.get('name')}\n   - 唯一ID: {tool.get('id')}\n   - 参  数:\n{args_str}")
                    
        elif isinstance(msg, ToolMessage):
            # 💡 提取工具执行结果，并关联它是对哪一个 call_id 的回应
            tool_name = getattr(msg, 'name', '未知工具')
            msg_lines.append(f"🛠️ [{role} 结果返回] (关联ID: {msg.tool_call_id} | 工具名: {tool_name}):")
            # 裁剪过长的执行结果，防止日志刷屏（可选）
            content_preview = msg.content if len(msg.content) < 1000 else f"{msg.content[:1000]}\n... (此处省略 {len(msg.content)-1000} 字)"
            msg_lines.append(content_preview)
            
        else:
            # 兜底通用解析
            msg_lines.append(f"❓ [{role}]: {msg.content}")
            
        # 组合成当前单条消息的完整文本
        if msg_lines:
            msgs.append("\n".join(msg_lines))
            
    # 用双虚线分隔每一轮对话，极大提升日志的可读性与排版美感
    return "\n\n" + "="*50 + " 📜 消息列表 " + "="*50 + "\n" + "\n\n--------------------------------------------------------------------------------\n\n".join(msgs) + "\n\n" + "="*124 + "\n"

from functools import wraps
from datetime import datetime
import queue
import threading
import sqlite3

LLM_TOKEN_LOGS_PATH = "llm_token_logs.jsonl" 
_telemetry_queue = queue.Queue()

def _background_worker():
    """后台消费者线程：常驻，专门负责把队列里的数据追加到本地文件中"""
    while True:
        try:
            # 1. 从队列里拿数据（没有数据时会在这里挂起，不吃 CPU）
            log_data = _telemetry_queue.get()
            
            # 毒丸机制：收到 None 说明要关机，退出线程
            if log_data is None: 
                break
                
            # 2. 核心改动：使用 'a' (append) 模式直接追加到文件末尾
            # 这种写法极其高效，哪怕文件以后长到几个G，写入也只需要不到 1 毫秒
            with open(LLM_TOKEN_LOGS_PATH, 'a', encoding='utf-8') as f:
                # 将你的 log_entry 转成单行 json 字符串，并加上换行符 \n
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                
        except Exception as e:
            print(f"❌ 后台持久化 Token 失败: {e}")
        finally:
            # 告诉队列，这个任务我处理完了
            _telemetry_queue.task_done()

# 启动后台守护线程（服务一启动就会常驻在后台，随时等待入队）
worker_thread = threading.Thread(target=_background_worker, daemon=True)
worker_thread.start()

def track_llm_usage(func):
    """
    无侵入式的 Token 统计装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        full_content, full_chunk = func(*args, **kwargs)
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "model_name": getattr(full_chunk, 'model_name', None) or getattr(base_llm, 'model'),
                'usage': full_chunk.usage_metadata
            }
            
            _telemetry_queue.put(log_entry)
            
        except Exception as e:
            print(f"❌ 装饰器解析 Token 失败: {e}")
            
        return full_content, full_chunk
        
    return wrapper

@track_llm_usage
def call_llm(llm, prompt: list[AnyMessage], logger: Logger) -> str:
    # logger.info(f'prompt: {fmt_messages(prompt)}')

    dict_list = messages_to_dict(prompt)

    # 3. 转换为 JSON 字符串（处理好中文编码）
    json_str = json.dumps(dict_list, ensure_ascii=False, indent=2)
    logger.info(f'prompt:\n{json_str}')


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
    logger.info(f'full chunk:\n {full_chunk}')
    logger.info(f'full content:\n {full_content}')
    logger.info('====LLM done ====')
    return full_content, full_chunk
