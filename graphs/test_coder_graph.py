from typing import Dict
from utils import extract_python_code, get_all_files_in_dir,draw_workflow_png
from globals import llm
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage
import re
from utils import extract_python_code,get_scene_prompt
from tools.search_replace_tool import apply_search_replace
from dotenv import load_dotenv
import os
import logging
import operator
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages,AnyMessage
from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from globals.state import get_issue_review,GraphState, Issue,any_write,merge_dicts,FileSnapshot,Task
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.filer import write_to_file,read_file, inspect_file_summary,delete_files,create_file
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references

load_dotenv()

GRAPH_NAME = 'test_coder_graph'

TEST_CODER_NODE_NAME = "test_coder_node"

PROMPT_FILE_NAME ='test_coder'
# 不进行static_check,因为测试先行,很多import问题.
tools=[
     write_to_file,create_file,
    apply_search_replace,ast_search,
    find_symbol_references, find_symbol_definition, 
    read_file, inspect_file_summary, delete_files,
]
llm = get_llm_with_tools(tools)
graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

class TestCoderGraphState(TypedDict,total=False):
        # 共享 with parent
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务

    attempts:int# 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_coder_subgraph_status:Annotated[str, any_write] 
    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts] 

    issue_buckets: dict[str, list[Issue]]
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]


def _do_first_write(state:TestCoderGraphState) -> Dict:
        # 提取代码
    system_prompt, user_prompt = get_scene_prompt(
            file_name=PROMPT_FILE_NAME,
            scene_name='write_code',
            task_content = state['current_task']['content'],
            target_files = state['current_task']['target_files'],
            reference_files = state['current_task']['reference_files']
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)
            
    full_content, full_chunk = call_llm(llm,messages, logger=graph_logger)
    full_chunk.name = TEST_CODER_NODE_NAME
    if full_chunk.tool_calls:
        # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }
    return {
        'messages': [full_chunk],
        'test_coder_subgraph_status':'success'
    }


def _do_fix_bug(state: TestCoderGraphState)->Dict:
    current_task = state['current_task']
    issues = state['issue_buckets'][GRAPH_NAME]

    graph_logger.info(f"[TestCoder] will fix bug. {len(issues)}")

    reviews = [get_issue_review(iss) for iss in issues]
    
    system_prompt, user_prompt  = get_scene_prompt(
        file_name=PROMPT_FILE_NAME,
        scene_name='fix_bug',
        review = '\n'.join(reviews),
        task_content = current_task['content'],
        target_files = current_task['target_files'],
        reference_files = current_task['reference_files'],
    )
 
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)   

    full_content, full_chunk = call_llm(llm,messages, logger=graph_logger)
    full_chunk.name = TEST_CODER_NODE_NAME
    if full_chunk.tool_calls:
        # 
        
        return {
            'messages': [full_chunk],
        }
    
    return {
        'messages': [full_chunk],
        'test_coder_subgraph_status':'success',
        'issue_buckets':{'test_coder_graph':[]},
    }
def test_writer_node(state: TestCoderGraphState) -> Dict:
    graph_logger.info("\n📝 [TestWriter] 正在生成或重构自动化测试")
    graph_logger.info("=" * 60)
    state['test_coder_subgraph_status'] = 'failed'

    issues = state['issue_buckets'].get(GRAPH_NAME, [])
    if issues:
        return _do_fix_bug(state)

    graph_logger.info("[TestWriter] 第一次写代码...")
    return _do_first_write(state)



def router_node(state: TestCoderGraphState) :
    # if start at node a

    return {
        'messages':[],
        'attempts':state['attempts'] + 1,
    }

graph = StateGraph(TestCoderGraphState)
graph.add_node('router_node', router_node)
graph.add_node(TEST_CODER_NODE_NAME, test_writer_node)
graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))
graph.set_entry_point('router_node')

graph.add_edge('router_node', TEST_CODER_NODE_NAME)

def decide_after_writer(state:TestCoderGraphState):
    if tools_condition(state) != END:
        return 'tools_executor'
    return 'success'     

def grade_after_tools(state:TestCoderGraphState):
    graph_logger.info('grade after tools: ')
    messages = state['messages']
    last_msg = messages[-1]
    graph_logger.info(f'last msg: {last_msg}')
    return TEST_CODER_NODE_NAME

graph.add_edge(
    'tools_node', 
    TEST_CODER_NODE_NAME
    )
graph.add_conditional_edges(
     TEST_CODER_NODE_NAME,
     decide_after_writer,
     {
          'tools_executor':'tools_node',
          'success': END
     }
)
graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
