from langchain_ollama import ChatOllama
from typing import TypedDict
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import logging
from enum import Enum
from tools.git import git_tool,GitAction
from rag.rag import knowledge_search
import operator
from typing import Annotated, List, TypedDict
logging.basicConfig(level=logging.INFO)

load_dotenv()
tools = [git_tool, knowledge_search]

llm = ChatOllama(
    model="qwen2.5-coder:3b",  
    temperature=0.1,   
    frequency_penalty=2,       # 避免llm回复循环重复的话语
    presence_penalty=1.0         # 🌟 辅助：惩罚重复的话题
)
llm.bind_tools(tools=tools)


# llm = ChatOpenAI(
#     api_key="sk-e0e6b0a59ae14fd18e760afd9d0d9bac",
#     base_url="https://api.deepseek.com",
#     model="deepseek-v4-flash",  # 云端代码模型
#     temperature=0
# )
# 生成目录
GENERATED_DIR = "generated"
MAX_ATTAMPTS= 1

# ============================================================
# State
# ============================================================

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

    requirement: str # 需求，原始文本

    code: str
    attempts: int # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_code: str  # 测试代码
    test_output: str # 测试代码输出

    is_issueing: bool # 是否正在处理修复建议

    issue_manager_wait: Annotated[set[str], operator.or_] # judger, qaer
    issues: Annotated[list[Issue], operator.add] # 修复建议列表
    current_issue: Issue | None # 当前处理的修复建议

    pyright_target: Annotated[set[str], operator.or_] # code, test_code
    pyright_result: dict # {'code':[.., ..], 'test_code':[..,..]} 

    human_source: str # human 来源，比如max_attempts, no issue


def create_initial_state() -> GraphState:

    return GraphState(
        code="",
        attempts=0,
        test_code="",
        test_output="",

        is_issueing=False,
        issues=[],
        current_issue=None,
        pyright_result={},
        pyright_target=set()
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


def update_attampts(state: GraphState) -> GraphState:
    """
    更新尝试次数
    """
    state['attempts'] += 1

    return state