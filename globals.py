from langchain_ollama import ChatOllama
from typing import TypedDict
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import logging
from enum import Enum
logging.basicConfig(level=logging.INFO)

load_dotenv()
llm = ChatOllama(
    model="qwen2.5-coder:3b",  
    temperature=0,
)
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
class PatchOperation(TypedDict):
    file: str
    action: str
    target: str
    reason: str # patch意图

class Issue(TypedDict):
    issue_id: str # 修复建议ID，唯一标识
    review: str # 修复建议
    type: str # 修复建议类型，CODE_BUG/TEST_BUG/DESIGN_BUG
    patch_plan: list[PatchOperation] # 补丁操作列表

from typing import TypedDict, Optional

class GitAction(str, Enum):
    NONE = "none"
    COMMIT = "commit"
    PUSH = "push"

class Git(TypedDict):
    action: GitAction      # 例如: 动作 'commit'
    target: str      # 例如: 动作承受者 'branch', 'file'
    reason: str      # git意图说明
    result: str  # 💡 新增：用来存放这条命令的执行结果（成功/失败的具体日志）
class WorkflowStatus(str, Enum):
    """
    流程内状态，node更新，边 来判断 转移。
    """
    INIT = "INIT"

    TO_SPEC = "TO_SPEC"
    SPEC_DONE = "SPEC_DONE"

    SPEC_QA_DONE = "SPEC_QA_DONE"

    TEST_QA_DONE = "TEST_QA_DONE"

    TO_TEST_WRITER = "TO_TEST_WRITER"

    TO_TESTER = "TO_TESTER"

    TO_PATCHER_CODE = "TO_PATCHER_CODE"
    TO_PATCHER_TEST = "TO_PATCHER_TEST"
    TO_PATCHER_DESIGN = "TO_PATCHER_DESIGN"

    CODE_GENERATED = "CODE_GENERATED"

    TEST_GENERATED = "TEST_GENERATED"

    TEST_PASSED = "TEST_PASSED"

    ISSUE_FOUND = "ISSUE_FOUND"

    TO_COMMIT = "TO_COMMIT"
    GIT_COMMITTED = "GIT_COMMITTED"

    TO_HUMAN = "TO_HUMAN"
    HUMAN_DONE = "HUMAN_DONE"

    IS_ISSUEING = "IS_ISSUEING"

    TO_ISSUE_MANAGER = "TO_ISSUE_MANAGER"

    MAX_ATTEMPTS = "MAX_ATTEMPTS"

    FINISHED = "FINISHED"

    FAILED = "FAILED"
    
class GraphState(TypedDict):

    requirement: str # 用户需求，原始文本

    code: str
    attempts: int # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_code: str  # 测试代码
    test_qa_review: str # 测试代码审计结果
    test_output: str # 测试代码输出

    spec: str # 软件规格说明书
    spec_qa_review: str # 规格说明书审计结果


    is_issueing: bool # 是否正在处理修复建议

    issues: list[Issue]  # 修复建议列表
    current_issue: Issue | None # 当前处理的修复建议

    git: Git | None # git操作

    status: WorkflowStatus | None # 流程内状态，node更新，边 来判断 转移。

def create_initial_state(requirement: str) -> GraphState:
    git = Git(
        action=GitAction.NONE,
        target="",
        reason="",
        result=""
    )
    return GraphState(
        requirement=requirement,
        code="",
        attempts=0,
        test_code="",
        test_qa_review="",
        test_output="",
        spec="",
        spec_qa_review="",
        is_issueing=False,
        issues=[],
        current_issue=None,
        git=git,
        status=WorkflowStatus.INIT
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
    if state['attempts'] > MAX_ATTAMPTS:
        state['status'] = WorkflowStatus.MAX_ATTEMPTS

    return state