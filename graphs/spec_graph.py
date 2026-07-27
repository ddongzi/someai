"""
按照speckit思考, 我们目前可以把 spec-plan-task 这种任务放在子图中.

作为全图的开端.他会检查当前task状态.不是每次全图都要执行

下方执行图仍然保持 只执行一个task.
"""
from typing import Dict
from globals.llm import get_llm_with_tools,call_llm
from tools.setup_spec_environment import setup_spec_environment
from tools.filer import write_to_file, create_file
from pathlib import Path
from langchain.messages import SystemMessage, HumanMessage, AnyMessage,ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import get_file_logger
from typing_extensions import TypedDict
from typing import Annotated
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from utils import draw_workflow_png
import operator
from langgraph.graph.message import add_messages,AnyMessage
from globals.state import GraphState, Issue,any_write,merge_dicts,FileMetadata
GRAPH_NAME = 'spec'
graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)
tools = [setup_spec_environment, write_to_file, create_file]
llm = get_llm_with_tools(tools)



class SpecGraphState(TypedDict):
    # 私有
    messages:Annotated[list[AnyMessage], add_messages]
def spec_node(state: SpecGraphState) -> Dict:
    """
    spec
    """
    graph_logger.info("\n spec build...")
    
    prompt_file = Path('.specify/spec_prompt.md')
    system_prompt = prompt_file.read_text()

    human_input = '我想要一个游戏地图生成组件'
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_input)
    ]
    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
    # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }


def plan_node(state: SpecGraphState) -> Dict:
    """
    plan
    """
    graph_logger.info("\n plan build...")

    prompt_file = Path('.specify/plan_prompt.md')
    system_prompt = prompt_file.read_text()

    human_input = '我想要一个游戏地图生成组件'
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_input)
    ]
    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
    # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }

def router_node(state: SpecGraphState) :
    # 状态初始化

    return {
        'messages':[],
    }

graph = StateGraph(SpecGraphState)
graph.add_node('router_node', router_node)

graph.add_node('spec_node', spec_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', 'spec_node')
def decide_after_qa(state:SpecGraphState):
    if tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        'spec_node'
    )
graph.add_conditional_edges(
     'spec_node',
     decide_after_qa,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
