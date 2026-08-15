from typing import Dict
import re   
from langchain_ollama import ChatOllama
import subprocess
import sys
from dotenv import load_dotenv
import os
from globals.state import GraphState, Issue,Task
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,read_file, inspect_file_summary,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.pytest_tool import run_pytest
from utils import get_scene_prompt
from langchain.messages import SystemMessage, HumanMessage
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages,AnyMessage
from globals.state import any_write
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from utils import draw_workflow_png
from globals.state import GraphState, Issue,any_write,merge_dicts,FileSnapshot

load_dotenv()

GRAPH_NAME = 'test_exec_graph'

EXEC_NODE_NAME = 'test_exec_node'

PROMPT_FILE_NAME = 'test_execer'
tools=[
    run_pytest
]
llm = get_llm_with_tools(tools)

graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)
# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

class TestExecGraphState(TypedDict):
    test_output: Annotated[str, any_write] # 测试代码输出
    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]

# ============================================================
# Tester Node
# ============================================================
def test_exec_node(state: TestExecGraphState) -> Dict:
    graph_logger.info("🤖 [TestExec] 开始执行测试")
    test_files = state['current_task']['target_files']
    system_prompt, user_prompt  = get_scene_prompt(
            file_name=PROMPT_FILE_NAME,
            scene_name='base',
            test_files = test_files
        )


    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    for msg in state['messages']:
        messages.append(msg)
    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)
    full_chunk.name = EXEC_NODE_NAME
    if full_chunk.tool_calls:
        # 
        return {
            'messages': [full_chunk],
        }
    
    return {
        'test_output': full_content
    }

def router_node(state: TestExecGraphState) :
    # 状态初始化

    return {
        'messages':[],
    }

graph = StateGraph(TestExecGraphState)
graph.add_node('router_node', router_node)

graph.add_node(EXEC_NODE_NAME, test_exec_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', EXEC_NODE_NAME)
def decide_after_texec(state:TestExecGraphState):
    if tools_condition(state) != END:
        graph_logger.info('after writer. goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        EXEC_NODE_NAME
    )
graph.add_conditional_edges(
     EXEC_NODE_NAME,
     decide_after_texec,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
