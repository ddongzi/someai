from tools.rag import get_knowledge
from typing import Dict
from tools.git import git_tool
from utils import  get_scene_prompt, draw_workflow_png
from globals.state import GraphState, Issue, FileSnapshot,Task,any_write,merge_dicts
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from tools.filer import write_to_file, create_file, read_file,delete_files
from tools.search_replace_tool import apply_search_replace
from tools.environment import get_environment_variable,set_environment_variable
from tools.time import get_current_time
from langchain.messages import SystemMessage, HumanMessage, AnyMessage,ToolMessage
import json
from globals.llm import call_llm, get_llm_with_tools
from globals.logger import get_file_logger
from langgraph.graph import StateGraph, END
from langgraph.graph.message import RemoveMessage
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Dict, TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages,AnyMessage

load_dotenv()
GRAPH_NAME='setup'
graph_logger = get_file_logger(
    logger_name='setup',
    filename='setup.log',
    so=True
)
PROMPT_FILE_NAME = "setup"
tools= [
      write_to_file, create_file, read_file, 
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
            task = state['current_task']['title']
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
    else:
        # 执行完毕, 清除消息
        graph_logger.info("给出结果...")
        existing_messages = state['messages']
        return {
            "messages": [RemoveMessage(id=m.id) for m in existing_messages]
        }

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
