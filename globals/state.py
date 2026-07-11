from typing import Annotated, List, TypedDict,Dict
import operator

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
    new_dict = left.copy()
    
    for k, v in right.items():
        # 模式一：【删除】如果新传进来的值明确是 None，直接把这个键拔掉
        if v is None:
            new_dict.pop(k, None)
        # 模式三：【新增 或 整体覆盖】如果是新文件，或者不是字典类型，直接赋值
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

class FileMetadata(TypedDict):
    path:str
    description: str  
    permission: str   

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

    file_ledger: Annotated[dict[str, FileMetadata], merge_dicts]

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
        file_ledger={}
    )

