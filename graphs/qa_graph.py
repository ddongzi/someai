import re
from typing import Dict
from utils import get_scene_prompt,parse_llm_json
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from globals.state import GraphState, Issue,Task
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,read_file, inspect_file_summary,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from typing_extensions import TypedDict
from typing import Annotated
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from utils import draw_workflow_png
import operator
from langgraph.graph.message import add_messages,AnyMessage
from globals.state import GraphState, Issue,any_write,merge_dicts,FileSnapshot
GRAPH_NAME = 'qa_graph'

QA_NODE_NAME = "qa_node"

PROMPT_FILE_NAME ='qaer'
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
# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

class QAGraphState(TypedDict):
    issues: Annotated[list[Issue], operator.add] # 修复建议列表
    file_ledger: Annotated[dict[str, FileSnapshot], merge_dicts]
    current_task: Annotated[Task, any_write]       # 当前正在执行的任务

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]
def qa_node(state: QAGraphState) -> Dict:
    """
    代码审计节点
    """
    graph_logger.info("\n🔍 [QA] 正在审计代码")
    current_task =  state['current_task']

    system_prompt, user_prompt  = get_scene_prompt(
        file_name='qaer',
        scene_name='base',
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
    if full_chunk.tool_calls:
        # 
        graph_logger.info(f'there are some tool calls. {full_chunk.tool_calls}')
        return {
            'messages': [full_chunk],
        }
    issues = []

    result = parse_llm_json(full_content)
    if current_task['task_type'] == 'code':
        assign = 'coder_graph'
    if current_task['task_type'] == 'test_code':
        assign = 'test_coder_graph'

    for item in result:
        issues.append(Issue(
            issue_id=uuid.uuid4(),
            source='qa_node',
            type= item['type'],
            review=item['review'],
            assign=assign
        ))
    return {
        'issues': issues,
        'messages': full_content
        }

def router_node(state: QAGraphState) :
    # 状态初始化

    return {
        'messages':[],
    }

graph = StateGraph(QAGraphState)
graph.add_node('router_node', router_node)

graph.add_node(QA_NODE_NAME, qa_node)

graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

graph.set_entry_point('router_node')

graph.add_edge('router_node', QA_NODE_NAME)
def decide_after_qa(state:QAGraphState):
    if tools_condition(state) != END:
        graph_logger.info(' goto tools exec.')
        return 'tools_executor'
    return 'success'     

graph.add_edge(
    'tools_node', 
        QA_NODE_NAME
    )
graph.add_conditional_edges(
     QA_NODE_NAME,
     decide_after_qa,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


graph = graph.compile()
draw_workflow_png(graph.get_graph(), GRAPH_NAME)
