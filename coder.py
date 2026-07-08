from globals import GraphState, Issue,call_llm,tools,any_write,merge_dicts
from typing import Dict
import re
from utils import extract_python_code,get_scene_prompt,draw_workflow_png
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from tools.search_replace_tool import apply_search_replace
from dotenv import load_dotenv
import os
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages,AnyMessage
from typing import Annotated, List, TypedDict
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

logger = logging.getLogger(__name__)

load_dotenv()

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")
llm_type = __name__



class CoderGraphState(TypedDict,total=False):
    # 共享 with parent
    requirement: Annotated[str, any_write] # 需求，原始文本

    attempts: Annotated[int, operator.add] # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    pyright_result: Annotated[dict, merge_dicts] # {'code':[.., ..], 'test_code':[..,..]} 

    code:  Annotated[str, any_write] 
    pyright_target: Annotated[set[str], operator.or_] # code, test_code


    issue_buckets: Annotated[dict[str, list[Issue]], merge_dicts]

    coder_subgraph_status: Annotated[str, any_write] 

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]



def _do_first_write(state:CoderGraphState) -> Dict:
        # 提取代码
    system_prompt, user_prompt  = get_scene_prompt(
            file_name='coder',
            scene_name='write_code',
            requirement = state['requirement']
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(messages)
    full_chunk.name = 'coder'

    if full_chunk.tool_calls:
        # 
        return {
            'messages': [full_chunk],
            'attempts':1
        }
    
    
    clean_code = extract_python_code(full_content)

    with open(f"{GENERATED_DIR}/app.py", "w") as f:
        f.write(clean_code)
    
    return {
        'pyright_target':{'code'},
        "code": clean_code.strip(),
        'messages': [full_chunk],
            'attempts':1,
            'coder_subgraph_status': 'success'

    }

def _do_pyright_repair(state: CoderGraphState) -> Dict:
    system_prompt, user_prompt  = get_scene_prompt(
        file_name='coder',
        scene_name='pyright_error',
        pyright_result = state['pyright_result']['code']
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)
    full_content, full_chunk = call_llm(messages)
    full_chunk.name = 'coder'

    code = state['code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':full_content
    })
    state['code'] = modified_code
    return {
        'code': state['code'],
        'messages': [full_chunk],
            'attempts':1,
            'coder_subgraph_status': 'success'


    }

def _do_fix_bug(state: CoderGraphState)->Dict:
    issues = state['issue_buckets'].get('coder', [])
    reviews = [iss.review for iss in issues]

    system_prompt, user_prompt = get_scene_prompt(
        file_name='coder',
        scene_name='fix_bug',
        review = '\n'.join(reviews)
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)
    full_content, full_chunk = call_llm(messages)
    full_chunk.name = 'coder'

    code = state['code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':full_content
    })
    state['code'] = modified_code
    return {
        'code': state['code'],
        'issue_buckets':{'coder':[]},
        'messages': [full_chunk],
            'attempts':1,
            'coder_subgraph_status': 'success'

    }


def write_code_node(state: CoderGraphState) -> Dict:
    print("\n🤖 [Coder] 开始生成或重构业务代码")
    print("=" * 60)
    state['coder_subgraph_status'] = 'failed'

    # 1. 处理pyright 静态 错误up
    if  state['pyright_result'].get('code', None):
        return _do_pyright_repair(state=state)
    
    # 2. 是否有issue
    issues = state['issue_buckets'].get('coder', [])
    if issues:
        return _do_fix_bug(state)

    print("[Coder] 第一次写代码")
    return _do_first_write(state)


def router_node(state: CoderGraphState) :
    return {}

coder_graph = StateGraph(CoderGraphState)
coder_graph.add_node('router_node', router_node)

coder_graph.add_node('writer', write_code_node)
coder_graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))

coder_graph.set_entry_point('router_node')

coder_graph.add_edge('router_node', 'writer')
def decide_after_writer(state:CoderGraphState):
    if tools_condition(state) != END:
        logger.info('after writer. goto tools exec.')
        return 'tools_executor'
    return 'success'     

coder_graph.add_edge(
    'tools_node', 
        'writer'
    )
coder_graph.add_conditional_edges(
     'writer',
     decide_after_writer,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)


coder_graph = coder_graph.compile()
draw_workflow_png(coder_graph.get_graph(), __name__)
