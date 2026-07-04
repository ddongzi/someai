from globals import llm, GENERATED_DIR
from globals import GraphState, Issue
from typing import Dict
import re
from utils import extract_python_code,get_scene_prompt
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from tools.search_replace_tool import apply_search_replace
logger = logging.getLogger(__name__)

def _call_llm(prompt:str)->str:
    full_content = ""
    for chunk in llm.stream(prompt):
        if chunk.content:
            full_content += chunk.content
    return full_content

def _do_first_write(state:GraphState) -> Dict:
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
    response = _call_llm(messages)
    clean_code = extract_python_code(response)

    with open(f"{GENERATED_DIR}/app.py", "w") as f:
        f.write(clean_code)
    
    return {
        'pyright_target':{'code'},
        "code": clean_code.strip(),
    }

def _do_pyright_repair(state: GraphState) -> Dict:
    system_prompt, user_prompt  = get_scene_prompt(
        file_name='coder',
        scene_name='pyright_error',
        pyright_result = state['pyright_result']['code']
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = _call_llm(messages)
    code = state['code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':response
    })
    state['code'] = modified_code
    return {
        'code': state['code']
    }

def _do_qa_bug(state: GraphState)->Dict:
    current_issue = state['current_issue']
    system_prompt, user_prompt = get_scene_prompt(
        file_name='coder',
        scene_name='qa_bug',
        review = current_issue['review']
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = _call_llm(messages)
    code = state['code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':response
    })
    state['code'] = modified_code
    return {
        'code': state['code'],
        'current_issue': None
    }

def _do_test_bug(state: GraphState)->Dict:
    print(f"[Coder] 有review, 修复代码。")
    
    current_issue = state['current_issue']
    system_prompt, user_prompt = get_scene_prompt(
        file_name='coder',
        scene_name='fix_bug',
        review = current_issue['review']
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = _call_llm(messages)
    code = state['code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':response
    })
    state['code'] = modified_code
    return {
        'code': state['code'],
        'current_issue': None
    }

def write_code_node(state: GraphState) -> Dict:
    print("\n🤖 [Coder] 开始生成或重构业务代码")
    print("=" * 60)

    # 1. 处理pyright 静态 错误
    if  state['pyright_result'].get('code', None):
        return _do_pyright_repair(state=state)
    
    current_issue = state.get("current_issue", None)
    # 2. 是否有issue
    if current_issue and current_issue['assign'] == 'coder':
        if current_issue['source'] == 'qa':
            return _do_qa_bug(state=state)
        
        if current_issue['source'] == 'judger':
            return _do_test_bug(state=state)

    print("[Coder] 第一次写代码")
    return _do_first_write(state)
    