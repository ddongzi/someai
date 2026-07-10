from langchain_ollama import ChatOllama
from typing import TypedDict
import os
from dotenv import load_dotenv
import logging
from enum import Enum
from tools.git import git_tool,GitAction
from rag.rag import knowledge_search
import operator
from tools.search_replace_tool import apply_search_replace
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.filer import read_file, create_file,inspect_project_structure
from typing import Annotated, List, TypedDict
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langgraph.graph.message import add_messages,AnyMessage
import operator
from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from langchain_community.cache import SQLiteCache
from logger import run_logger

# 1. 自动加载项目根目录下的 .env 文件到环境变量中
load_dotenv()

set_llm_cache(SQLiteCache())

deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

tools = [git_tool, knowledge_search, inspect_project_structure,
          apply_search_replace,ast_search,
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

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

MAX_ATTAMPTS= 1

# ============================================================
# State
# ============================================================
# reducer for shared state

def any_write(left, right):
    """
    更新为最后一个状态。
    left：上一个
    right：下一个
    """
    return right if right is not None else left
def merge_dicts(left: dict, right: dict) -> dict:
    # 强力容错：防止其中一方为 None
    left = left or {}
    right = right or {}
    
    # 合并逻辑（根据你的业务调整）
    new_dict = left.copy()
    for k, v in right.items():
        if k in new_dict and isinstance(new_dict[k], list) and isinstance(v, list):
            new_dict[k] = new_dict[k] + v  # 列表合并
        else:
            new_dict[k] = v
    return new_dict


class Issue(TypedDict):
    issue_id: str # 修复建议ID，唯一标识
    source: str # qaer, judger
    type: str # 类型：CODE_BUG, DESIGN_BUG, TEST_CODE_BUG
    assign: str # coder, test_coder, human
    review: str # 修复建议

from typing import TypedDict, Optional



class Git(TypedDict):
    action: GitAction      # 例如: 动作 'commit'
    target: str      # 例如: 动作承受者 'branch', 'file'
    reason: str      # git意图说明
    result: str  # 💡 新增：用来存放这条命令的执行结果（成功/失败的具体日志）

class QAReview(TypedDict):
    target: str # test_code, code
    result: list[str]
    
class GraphState(TypedDict):

    requirement: Annotated[str, any_write]  # 需求，原始文本

    code: Annotated[str, any_write]
    attempts: Annotated[int, operator.add] # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_code: Annotated[str, any_write]  # 测试代码
    test_output: str # 测试代码输出

    is_issueing: bool # 是否正在处理修复建议

    issue_manager_wait: Annotated[set[str], operator.or_] # judger, qaer
    issues: Annotated[list[Issue], operator.add] # 修复建议列表

    issue_buckets: Annotated[dict[str, list[Issue]], merge_dicts] # {'coder' [], 'test_coder':}

    pyright_target: Annotated[set[str], operator.or_] # code, test_code
    pyright_result:  Annotated[dict, merge_dicts]  # {'code':[.., ..], 'test_code':[..,..]} 

    human_source: str # human 来源，比如max_attempts, no issue

    # 子图状态
    coder_subgraph_status: Annotated[str, any_write] # success
    test_coder_subgraph_status:Annotated[str, any_write]


def create_initial_state() -> GraphState:

    return GraphState(
        code="",
        attempts=0,
        test_code="",
        test_output="",
        issue_buckets = {
            'coder':[],
            'test_coder':[],
            'human':[]
        },
        is_issueing=False,
        issues=[],
        pyright_result={
            'code':[],
            'test_code':[]
        },
        pyright_target=set(),
    )



class GraphStatus(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    INTERRUPTED = "INTERRUPTED"
    FINISHED = "FINISHED"

def get_graph_status(snapshot) -> GraphStatus:
    """
    判断 LangGraph 当前状态
    """

    # 从未运行
    if (
        not snapshot.next
        and not snapshot.tasks
        and not snapshot.values
    ):
        return GraphStatus.NEW

    # interrupt挂起
    if snapshot.tasks:
        for task in snapshot.tasks:
            if getattr(task, "interrupts", None):
                if len(task.interrupts) > 0:
                    return GraphStatus.INTERRUPTED

    # 还有后续节点
    if snapshot.next:
        return GraphStatus.RUNNING

    # 没有后续节点
    return GraphStatus.FINISHED

def call_llm(prompt:str)->str:
    run_logger.info(f'prompt :{prompt}')
    full_content = ""
    full_chunk = None
    run_logger.info('====LLM stream ..====')
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

    run_logger.info(f'llm full chunks.\n{full_chunk}')
    run_logger.info(f'llm full content.\n{full_content}')
    run_logger.info('====LLM done ====')
    return full_content, full_chunk

