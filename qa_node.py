# ============================================================
# Test QA Node 测试代码审计
# ============================================================
import re
from typing import Dict
from utils import get_scene_prompt,parse_llm_json
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from globals.state import GraphState, Issue
from globals.llm import llm,call_llm
from globals.logger import run_logger


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
            assign = 'coder_graph'
        if type == 'test_code':
            assign = 'test_coder_graph'
        issues.append(Issue(
            issue_id=uuid.uuid4(),
            source='qa_node',
            type= item['type'],
            review=item['review'],
            assign=assign
        ))
    return {
        'issues': issues,
        'issue_manager_wait':{'qa_node'}, 
        'messages': full_content
        }
