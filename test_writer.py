from globals import llm, Issue, call_llm,tools
from typing import Dict
import re
from utils import extract_python_code, get_all_files_in_dir,draw_workflow_png
from globals import llm
from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage
import re
from utils import extract_python_code,get_scene_prompt
import logging
from tools.search_replace_tool import apply_search_replace
from dotenv import load_dotenv
import os
import logging
import operator
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages,AnyMessage
from typing import Annotated, List, TypedDict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import ToolNode, tools_condition
from globals import GraphState, Issue,call_llm,tools,any_write,merge_dicts
from logger import run_logger

load_dotenv()

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

class TestWriterGraphState(TypedDict,total=False):
        # 共享 with parent
    requirement: Annotated[str, any_write] # 需求，原始文本

    attempts: Annotated[int, any_write] # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    pyright_result: Annotated[dict, merge_dicts] # {'code':[.., ..], 'test_code':[..,..]} 

    test_code:  Annotated[str, any_write] 
    pyright_target: Annotated[set[str], operator.or_] # code, test_code
    test_coder_subgraph_status:Annotated[str, any_write] 

    pyright_target: Annotated[set[str], operator.or_] # code, test_code
    issue_buckets: Annotated[dict[str, list[Issue]], merge_dicts]

    # 私有
    messages:Annotated[list[AnyMessage], add_messages]



def _do_first_write(state:TestWriterGraphState) -> Dict:
        # 提取代码
    system_prompt, user_prompt = get_scene_prompt(
            file_name='test_coder',
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
    full_chunk.name = 'test_writer'
    if full_chunk.tool_calls:
        # 
        return {
            'messages': [full_chunk],
        }
    clean_code = extract_python_code(full_content)

    with open(f"{GENERATED_DIR}/app.py", "w") as f:
        f.write(clean_code)
    
    return {
        'pyright_target':{'test_code'},
        "test_code": clean_code.strip(),
        'messages': [full_chunk],
        'test_coder_subgraph_status':'success'
    }

def _do_pyright_repair(state: TestWriterGraphState) -> Dict:
    system_prompt, user_prompt = get_scene_prompt(
        file_name='test_coder',
        scene_name='pyright_error',
        pyright_result = state['pyright_result']['test_code']
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    for msg in state['messages']:
        messages.append(msg)

    full_content, full_chunk = call_llm(messages)
    full_chunk.name = 'test_writer'
    if full_chunk.tool_calls:
        # 
        return {
            'messages': [full_chunk],
        }
    
    code = state['test_code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':full_content
    })
    state['test_code'] = modified_code
    return {
        'test_code': modified_code,
        'messages': [full_chunk],
        'test_coder_subgraph_status':'success'

    }

def _do_fix_bug(state: TestWriterGraphState)->Dict:
    run_logger.info(f"[Coder] 有review, 修复代码。")
    
    issues = state['issue_buckets']['coder']
    reviews = [iss.review for iss in issues]
    system_prompt, user_prompt  = get_scene_prompt(
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
    full_chunk.name = 'test_writer'
    if full_chunk.tool_calls:
        # 
        return {
            'messages': [full_chunk],
        }
    
    code = state['code']
    
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':full_content
    })
    state['code'] = modified_code
    return {
        'code': state['code'],
        'messages': [full_chunk],
        'test_coder_subgraph_status':'success',
        'issue_buckets':{'coder':[]},

    }
def test_writer_node(state: TestWriterGraphState) -> Dict:
    run_logger.info("\n📝 [TestWriter] 正在生成或重构自动化测试")
    run_logger.info("=" * 60)
    state['test_coder_subgraph_status'] = 'failed'

    run_logger.info(f'pyrgiht : {state['pyright_result']}')
    # 1. 处理pyright 静态 错误
    if  state['pyright_result'].get('test_code', None):
        return _do_pyright_repair(state=state)
    
    # 2. 是否有issue
    issues = state['issue_buckets'].get('test_coder', [])
    if issues:
        return _do_fix_bug(state)

    run_logger.info("[TestWriter] 第一次写代码...")
    return _do_first_write(state)



def router_node(state: TestWriterGraphState) :
    # if start at node a

    return {
        'messages':[]
    }

test_coder_graph = StateGraph(TestWriterGraphState)
test_coder_graph.add_node('router_node', router_node)
test_coder_graph.add_node('test_writer', test_writer_node)
test_coder_graph.add_node('tools_node', ToolNode(tools=tools, handle_tool_errors=True))
test_coder_graph.set_entry_point('router_node')

test_coder_graph.add_edge('router_node', 'test_writer')

def decide_after_writer(state:TestWriterGraphState):
    if tools_condition(state) != END:
        return 'tools_executor'
    return 'success'     

def grade_after_tools(state:TestWriterGraphState):
    run_logger.info('grade after tools: ')
    messages = state['messages']
    last_msg = messages[-1]
    run_logger.info(f'last msg: {last_msg}')
    return 'test_writer'

test_coder_graph.add_edge(
    'tools_node', 
    'test_writer'
    )
test_coder_graph.add_conditional_edges(
     'test_writer',
     decide_after_writer,
     {
          'tools_executor':'tools_node',
          'success': END
     }

)
test_coder_graph = test_coder_graph.compile()
draw_workflow_png(test_coder_graph.get_graph(), __name__)
