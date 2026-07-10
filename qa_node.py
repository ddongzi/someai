# ============================================================
# Test QA Node 测试代码审计
# ============================================================
from globals import GraphState
import re
from globals import llm,call_llm
from typing import Dict
from utils import get_scene_prompt,parse_llm_json
from globals import Issue
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from logger import run_logger

def qa_node(state: GraphState) -> Dict:
    """
    代码审计节点
    """
    run_logger.info("\n🔍 [QA] 正在审计代码质量")

    code = state.get("code", "")
    test_code = state.get("test_code", "")

    system_prompt, user_prompt  = get_scene_prompt(
        file_name='qaer',
        scene_name='base',
        code=code,
        test_code= test_code
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    full_content, full_chunk = call_llm(messages)

    issues = []

    result = parse_llm_json(full_content)
    for item in result:
        type = item['type']
        assign = 'unknown'
        if type == 'code':
            assign = 'coder'
        if type == 'test_code':
            assign = 'test_coder'
        issues.append(Issue(
            issue_id=uuid.uuid4(),
            source='qaer',
            type= item['type'],
            review=item['review'],
            assign=assign
        ))
    return {
        'issues': issues,
        'issue_manager_wait':{'qaer'}, 
        'messages': full_content
        }
