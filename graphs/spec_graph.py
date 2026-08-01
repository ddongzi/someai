"""
按照speckit思考, 我们目前可以把 spec-plan-task 这种任务放在子图中.

作为全图的开端.他会检查当前task状态.不是每次全图都要执行

下方执行图仍然保持 只执行一个task.
"""
from typing import Dict
from globals.llm import get_llm_with_tools,call_llm
from tools.setup_spec_environment import setup_spec_environment
from tools.filer import write_to_file, create_file, read_file,delete_files
from tools.search_replace_tool import apply_search_replace
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
from langgraph.graph.message import add_messages,AnyMessage,RemoveMessage
from globals.state import GraphState, Issue,any_write,merge_dicts,FileSnapshot
from tools.environment import get_environment_variable
from tools.time import get_current_time
from globals.state import merge_dicts, FileSnapshot
GRAPH_NAME = 'spec'
graph_logger = get_file_logger(
    logger_name=f'{GRAPH_NAME}',
    filename=f'{GRAPH_NAME}.log',
    so=True
)
tools= [
     setup_spec_environment, write_to_file, 
         create_file, read_file, apply_search_replace,delete_files, 
         get_environment_variable, get_current_time   
]
llm = get_llm_with_tools( [write_to_file, 
         create_file, read_file, apply_search_replace,delete_files, 
         get_environment_variable, get_current_time])

spec_llm = get_llm_with_tools([
    setup_spec_environment, write_to_file, 
         create_file, read_file, apply_search_replace,delete_files, 
         get_environment_variable, get_current_time
])

WAIT_FOR_USER_RESPONSE = '_[Wait for user response]_'


class SpecGraphState(TypedDict):
    file_ledger: Annotated[Dict[str, FileSnapshot], merge_dicts]# file_path -> FileSnapshot

    # 私有
    user_req: str = ''
    messages:Annotated[list[AnyMessage], add_messages]
    current_tool_caller: str = ''


def constitution_node(state: SpecGraphState) -> Dict:
    """
    constitution
    """
    graph_logger.info("\n constitution build...")
    
    prompt_file = Path('.specify/constitution_prompt.md')
    system_prompt = prompt_file.read_text()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'User input: {state["user_req"]}')
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
            'current_tool_caller': 'constitution_node'
        }
    else:
        # 执行完毕, 清除消息
        graph_logger.info("给出结果...")
        existing_messages = state['messages']
        return {
            'current_tool_caller':'', 
            "messages": [RemoveMessage(id=m.id) for m in existing_messages]  # 清除消息
        }

def spec_node(state: SpecGraphState) -> Dict:
    """
    spec
    """
    graph_logger.info("\n spec build...")
    
    prompt_file = Path('.specify/spec_prompt.md')
    system_prompt = prompt_file.read_text()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'User input: {state["user_req"]}')
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(spec_llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
            'current_tool_caller':'spec_node'
        }
    else:
        # 工具调用完毕, 给出结果
        if WAIT_FOR_USER_RESPONSE in full_content:
            # 等待用户输入
            graph_logger.info("等待用户输入...")
            user_input = input("请输入你的命令: ")
            return {
                'messages': [full_chunk],
            }
        # 执行完毕, 清除消息
        graph_logger.info("给出结果...")
        existing_messages = state['messages']
        return {
            'current_tool_caller':'',
            "messages": [RemoveMessage(id=m.id) for m in existing_messages]
        }


def plan_node(state: SpecGraphState) -> Dict:
    """
    plan
    """
    graph_logger.info("\n plan build...")
    
    prompt_file = Path('.specify/plan_prompt.md')
    system_prompt = prompt_file.read_text()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'User input: {state["user_req"]}')
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
            'current_tool_caller':'plan_node'
        }
    else:

        graph_logger.info("给出结果...")
        existing_messages = state['messages']
        return {
            'current_tool_caller':'',
            "messages": [RemoveMessage(id=m.id) for m in existing_messages]
        }

def tasks_node(state: SpecGraphState) -> Dict:
    """
    tasks
    """
    graph_logger.info("\n tasks build...")
    
    prompt_file = Path('.specify/tasks_prompt.md')
    system_prompt = prompt_file.read_text()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'User input: {state["user_req"]}')
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(llm, messages, logger=graph_logger)

    if full_chunk.tool_calls:
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
            'current_tool_caller':'tasks_node'
        }
    else:

        graph_logger.info("给出结果...")
        existing_messages = state['messages']
        return {
            'current_tool_caller':'',
            "messages": [RemoveMessage(id=m.id) for m in existing_messages]
        }

def router_node(state: SpecGraphState) :
    # 状态初始化

    return {
        'messages':[],
        'user_req': '我想要一个游戏地图生成组件',
        'current_tool_caller': ''
    }

graph = StateGraph(SpecGraphState)
graph.add_node('router_node', router_node)

graph.add_node('constitution_node', constitution_node)

graph.add_node('spec_node', spec_node)
graph.add_node('plan_node', plan_node)
graph.add_node('tasks_node', tasks_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', 'constitution_node')

def decide_after_spec(state:SpecGraphState):
    if  state['messages'] and tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'

def decide_after_constitution(state:SpecGraphState):
    if  state['messages'] and tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     

def decide_after_plan(state:SpecGraphState):
    if  state['messages'] and tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     
def decide_after_tasks(state:SpecGraphState):
    if  state['messages'] and tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     
def decide_after_tools(state:SpecGraphState):
    if state['current_tool_caller'] == 'spec_node':
        return 'spec_node'
    if state['current_tool_caller'] == 'constitution_node':
        return 'constitution_node'
    if state['current_tool_caller'] == 'plan_node':
        return 'plan_node'
    if state['current_tool_caller'] == 'tasks_node':
        return 'tasks_node'
    graph_logger.info('unexpected tool_caller. .')     
    return 'unexpected'     

graph.add_conditional_edges(
    'tools_node', 
    decide_after_tools,
    {
        'spec_node': 'spec_node',
        'constitution_node': 'constitution_node',
        'plan_node': 'plan_node',
        'tasks_node': 'tasks_node',
        'unexpected': END 
    }
)
graph.add_conditional_edges(
    'constitution_node',
    decide_after_constitution,
    {
        'tools_executor':'tools_node',
        'success': 'spec_node'
    }     

)
graph.add_conditional_edges(
     'spec_node',
     decide_after_spec,
     {
          'tools_executor':'tools_node',
          'success': 'plan_node'
     }

)
graph.add_conditional_edges(
    'plan_node',
    decide_after_plan,
    {
          'tools_executor':'tools_node',
          'success': 'tasks_node'
    }
)
graph.add_conditional_edges(
    'tasks_node',
    decide_after_tasks,
    {
          'tools_executor':'tools_node',
          'success': END
    }
)
graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
