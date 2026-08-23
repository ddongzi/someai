
from typing import Dict
import re
import uuid
from utils import get_scene_prompt,parse_llm_json
from langchain_core.messages import SystemMessage, HumanMessage
from globals.state import GraphState, Issue,Task
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,read_file, inspect_file_summary,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages,AnyMessage
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from utils import draw_workflow_png
from globals.state import GraphState, Issue,any_write,merge_dicts,FileSnapshot
GRAPH_NAME = 'judge_graph'

JUDGE_NODE_NAME = "judge_node"

PROMPT_FILE_NAME ='judger'
tools=[
    ast_search,
    find_symbol_references, find_symbol_definition, 
    read_file,inspect_file_summary
]
llm = get_llm_with_tools(tools)
graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)
class JudgeGraphState(TypedDict):
    test_output: str # 测试代码输出
    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务
    issues: list[Issue] # 修复建议列表

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]
def judge_node(state: JudgeGraphState) -> Dict:
    graph_logger.info("\n⚖️ [Judge] Analyze the test output...")
    graph_logger.info("=" * 60)

    output = state.get("test_output", "")
    current_task = state['current_task']
    reference_files =  current_task['reference_files']
    if current_task['task_type'] == 'code':
        expected_result = "Expect all test cases to pass."
        test_files = current_task['target_files']
    if current_task['task_type'] == 'test_code':
        expected_result = "Expect all test cases to fail, or Process failed."
        # TODO
        test_files = ''

    system_prompt, user_prompt = get_scene_prompt(
        file_name='judger',
        scene_name='base',
        test_output=output,
        expected_result=expected_result,
        test_files=test_files,
        reference_files=reference_files
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)
    if full_chunk.tool_calls:
        # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }
    result = parse_llm_json(full_content)

    issues = list(state.get('issues', []))
    if current_task['task_type'] == 'code':
        assign = 'coder_graph'
    if current_task['task_type'] == 'test_code':
        assign = 'test_coder_graph'
        
    for issue in result:

        issues.append(Issue(
                issue_id=uuid.uuid4(),
                source='judge_node',
                assign=assign,

                gap_type="contradicts",
                evidence=output,
                source_ref="",
                how_to_fix="",
                severity="HIGH"
            ))
    return {
        "issues": issues,
        "test_output": '', # 我们已经转化为issue了，所以test_output为空字符串
        'messages':[full_content]
    }

def router_node(state: JudgeGraphState) :
    # 状态初始化

    return {
        'messages':[],
    }

graph = StateGraph(JudgeGraphState)
graph.add_node('router_node', router_node)

graph.add_node(JUDGE_NODE_NAME, judge_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', JUDGE_NODE_NAME)
def decide_after_judge(state:JudgeGraphState):
    if tools_condition(state) != END:
        graph_logger.info('after writer. goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        JUDGE_NODE_NAME
    )
graph.add_conditional_edges(
     JUDGE_NODE_NAME,
     decide_after_judge,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
