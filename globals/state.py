from typing import Annotated, List, TypedDict, Dict, Optional
import operator
from pathlib import Path

from pydantic import BaseModel, Field

# reducer for shared state

def any_write(left, right):
    """
    更新为最后一个状态。
    left：上一个
    right：下一个
    """
    return right if right is not None else left
def merge_dicts(left: dict, right: dict) -> dict:
    left = left or {}
    right = right or {}
    new_dict = left.copy()
    
    for k, v in right.items():
        if v is None:
            new_dict.pop(k, None)
        else:
            new_dict[k] = v
            
    return new_dict
def replace_dict(left: dict, right: dict) -> dict:
    # 只要右边传了东西（即使是空字典 {}），就完全以右边为准
    if right is not None:
        return right
    return left or {}

class Issue(TypedDict):
    issue_id: str # 修复建议ID，唯一标识
    source: str # qaer, judger
    type: str # 类型：CODE_BUG, DESIGN_BUG, TEST_CODE_BUG
    assign: str # coder, test_coder, human
    review: str # 修复建议


# 从tasks.md通过llm解析出来
class Task(BaseModel):
    """任务，使用 Pydantic 进行约束校验"""
    id: str = Field(
        default="", 
        description="任务ID.必须提取自 Txxx格式.如T001.不为空"
        )
    content: str = Field(
        default="", 
        description="任务内容.去除ID,[P]等前缀标记后的内容.不为空"
        )
    status: str = Field(
        default="pending",
        description="任务状态: pending | in_progress | completed.默认即可,手动设置.",
    )
    task_type: str = Field(
        default="",
        description="""任务类型.可选: setup, code, test_code.
        - setup: 基础配置,目录和文件创建,初始化. 相关文档修改
        - code: 编写或修改业务代码.
        - test_code: 编写或修改测试代码.
        """,
    )
    phase: str = Field(
        default="", 
        description="所属阶段全名. 如Phase 1: User Story 1 - Create a new user (Priority: P1)"
        )
    target_files: List[str] = Field(
        default_factory=list, 
        description="需要操作、创建或修改的具体目标文件或目录路径列表。不为空."
    )
    reference_files: List[str] = Field(
        default_factory=list, 
        description="需要参考的文件列表。留空即可,手动设置."
    )

    # 兼容 TypedDict 的下标访问方式，如 state['current_task']['title']
    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class TaskList(BaseModel):
    """任务列表，用于 LLM structured output 解析"""
    tasks: List[Task] = Field(default_factory=list, description="任务列表")

class FileSnapshot(TypedDict):
    file_name: str
    file_path: str
    last_read_time: str = ''
    last_modified_time: str = ''
    file_hash: str = ''
    description: str = ''
    allowed_read_nodes: List[str] = []   # 哪些节点（角色）可以读取此文件
    allowed_write_nodes: List[str] = []  # 哪些节点（角色）可以修改/写入此文件

class GraphState(TypedDict):

    attempts: Annotated[int, operator.add] # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_output: Annotated[str, any_write] # 测试代码输出

    is_issueing: bool # 是否正在处理修复建议

    issues: Annotated[list[Issue], operator.add] # 修复建议列表

    issue_buckets: Annotated[dict[str, list[Issue]], merge_dicts] #

    human_source: str # human 来源，比如max_attempts, no issue

    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]

    # 子图状态
    coder_subgraph_status: Annotated[str, any_write] # success
    test_coder_subgraph_status:Annotated[str, any_write]

    # 任务调度
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务


def create_initial_state() -> GraphState:

    return GraphState(
        code="",
        attempts=0,
        test_code="",
        test_output="",
        issue_buckets = {
            'coder_graph':[],
            'test_coder_graph':[],
            'human_node':[]
        },
        is_issueing=False,
        issues=[],
        file_ledger={}
    )

