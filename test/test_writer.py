from globals import llm, GraphState, Issue,update_attampts
from typing import Dict
import re
from globals import GENERATED_DIR
from utils import extract_python_code, get_all_files_in_dir
from globals import llm, GENERATED_DIR
from globals import GraphState, Issue
from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
import re
from utils import extract_python_code,get_scene_prompt
import logging
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
    system_prompt, user_prompt = get_scene_prompt(
            file_name='test_coder',
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
        'pyright_target':{'test_code'},
        "test_code": clean_code.strip(),
    }

def _do_pyright_repair(state: GraphState) -> Dict:
    system_prompt, user_prompt = get_scene_prompt(
        file_name='test_coder',
        scene_name='pyright_error',
        pyright_result = state['pyright_result']['test_code']
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = _call_llm(messages)
    code = state['test_code']
    modified_code = apply_search_replace.invoke({
        'original':code,
        'diff':response
    })
    state['test_code'] = modified_code
    return {
        'test_code': modified_code
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
    system_prompt, user_prompt  = get_scene_prompt(
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
def test_writer_node(state: GraphState) -> Dict:
    print("\n📝 [TestWriter] 正在生成或重构自动化测试")
    print("=" * 60)

    current_issue = state.get("current_issue", None)

    update_attampts(state)

    logger.info(f'pyrgiht : {state['pyright_result']}')
    # 1. 处理pyright 静态 错误
    if  state['pyright_result'].get('test_code', None):
        return _do_pyright_repair(state=state)
    
    current_issue = state.get("current_issue", None)
    # 2. 是否有issue
    if current_issue and current_issue['assign'] == 'coder':
        if current_issue['source'] == 'qa':
            return _do_qa_bug(state=state)
        
        if current_issue['source'] == 'judger':
            return _do_test_bug(state=state)

    print("[TestWriter] 第一次写代码...")
    return _do_first_write(state)
    