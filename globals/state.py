from typing import Annotated, List, TypedDict,Dict
import operator
from pathlib import Path
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

class Task(TypedDict):
    """当前执行中的任务"""
    id: str                          # 任务ID，如 "T001"
    title: str                       # 任务标题
    status: str                      # pending | in_progress | completed 默认为pending
    task_type: str                   # setup | code | test_code | doc
    phase: str | None                # 所属阶段名称
    phase_number: int | None         # 所属阶段编号
    user_story: str | None           # 所属用户故事
    priority: str | None             # 优先级
    parallel: bool                   # 是否可并行
    tags: List[str]                  # 标签列表
    target_files: List[str]          # 需要操作修改的文件列表
    reference_files: List[str]       # 需要参考的文件列表

class TaskList(TypedDict):
    tasks: List[Task]

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

