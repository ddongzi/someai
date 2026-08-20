from typing import Dict
import re
from utils import extract_python_code,get_scene_prompt,draw_workflow_png
import logging
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage
from tools.search_replace_tool import apply_search_replace
from dotenv import load_dotenv
import os
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages,AnyMessage
from typing import Annotated, List, TypedDict
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from globals import MAX_ATTAMPTS
from globals.state import GraphState, Issue,any_write,merge_dicts,FileSnapshot,Task
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,read_file, inspect_file_summary,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.pyright_check import static_check
load_dotenv()

GRAPH_NAME = 'coder_graph'

CODER_NODE_NAME = "coder_node"

PROMPT_FILE_NAME ='coder'

tools=[
    write_to_file,static_check,
    apply_search_replace,ast_search,
    find_symbol_references, find_symbol_definition, 
    read_file,inspect_file_summary, delete_files
]
llm = get_llm_with_tools(tools)

graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)
# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

class CoderGraphState(TypedDict,total=False):
    # 共享 with parent
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务

    attempts: Annotated[int, operator.add] # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]

    issue_buckets: dict[str, list[Issue]]

    coder_subgraph_status: Annotated[str, any_write] 


    # 私有
    messages:Annotated[list[AnyMessage], add_messages]



def _do_first_write(state:CoderGraphState) -> Dict:
        # 提取代码
    system_prompt, user_prompt  = get_scene_prompt(
            file_name=PROMPT_FILE_NAME,
            scene_name='write_code',
            requirement = state['current_task']['content']
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    for msg in state['messages']:
        messages.append(msg)


    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)
    full_chunk.name = CODER_NODE_NAME

    if full_chunk.tool_calls:
        # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }
    

    return {
        'messages': [full_chunk],
            'coder_subgraph_status': 'success'

    }


def _do_fix_bug(state: CoderGraphState)->Dict:
    issues = state['issue_buckets'].get(GRAPH_NAME, [])
    reviews = [iss['review'] for iss in issues]

    system_prompt, user_prompt = get_scene_prompt(
        file_name=PROMPT_FILE_NAME,
        scene_name='fix_bug',
        review = '\n'.join(reviews)
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)
    full_chunk.name = CODER_NODE_NAME
    if full_chunk.tool_calls:
        # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }
    
    return {
        'issue_buckets':{'coder_graph':[]},
        'messages': [full_chunk],
        'coder_subgraph_status': 'success'

    }


def write_code_node(state: CoderGraphState) -> Dict:
    graph_logger.info("🤖 [Coder] 开始生成或重构业务代码")
    state['coder_subgraph_status'] = 'failed'

    issues = state['issue_buckets'].get(GRAPH_NAME, [])
    if issues:
        return _do_fix_bug(state)

    graph_logger.info("[Coder] 第一次写代码")
    return _do_first_write(state)


def router_node(state: CoderGraphState) :
    # 状态初始化

    return {
        'messages':[],
        'attempts':1,

    }

graph = StateGraph(CoderGraphState)
graph.add_node('router_node', router_node)

graph.add_node(CODER_NODE_NAME, write_code_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', CODER_NODE_NAME)
def decide_after_writer(state:CoderGraphState):
    if tools_condition(state) != END:
        graph_logger.info('after writer. goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        CODER_NODE_NAME
    )
graph.add_conditional_edges(
     CODER_NODE_NAME,
     decide_after_writer,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
