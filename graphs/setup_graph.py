from typing import Dict, TypedDict, Annotated
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import json

from tools.rag import get_knowledge
from tools.git import git_tool
from utils import get_scene_prompt, draw_workflow_png
from globals.state import GraphState, Issue, FileSnapshot, Task, any_write, merge_dicts
from tools.filer import write_to_file, create_file, read_file, delete_files,create_directory
from tools.search_replace_tool import apply_search_replace
from tools.environment import get_environment_variable, set_environment_variable
from tools.time import get_current_time
from langchain.messages import SystemMessage, HumanMessage, AnyMessage, ToolMessage
from globals.llm import call_llm, get_llm_with_tools
from globals.logger import get_file_logger
from langgraph.graph import StateGraph, END
from langgraph.graph.message import RemoveMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages, AnyMessage
from task_helper import save_task

load_dotenv()
GRAPH_NAME='setup'
graph_logger = get_file_logger(
    logger_name='setup',
    filename='setup.log',
    so=True
)
PROMPT_FILE_NAME = "setup"
tools= [
      write_to_file, create_file, read_file, create_directory,
      delete_files, 
    get_environment_variable, get_current_time, 
    set_environment_variable
]
llm = get_llm_with_tools(tools)
class SetupGraphState(TypedDict):
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务
    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]

    messages:Annotated[list[AnyMessage], add_messages]


def setup_node(state: SetupGraphState) -> Dict:
    graph_logger.info("Setting up graph...")    

    system_prompt, user_prompt  = get_scene_prompt(
            file_name=PROMPT_FILE_NAME,
            scene_name='execute_setup',
            task_title = state['current_task']['title'],
            target_files = state['current_task']['target_files'],
            reference_files = state['current_task']['reference_files']
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }

    # 任务完成, 更新current_task已完成.
    state['current_task']['status'] = 'completed'
    save_task(state['current_task'])
    return {}

def router_node(state: SetupGraphState) :
    # 状态初始化

    return {
        'messages':[],
    }

graph = StateGraph(SetupGraphState)
graph.add_node('router_node', router_node)

graph.add_node('setup_node', setup_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', 'setup_node')
def decide_after_setup(state:SetupGraphState):
    if tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        'setup_node'
    )
graph.add_conditional_edges(
     'setup_node',
     decide_after_setup,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)

graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
