# ============================================================
# Test Judge Node 测试输出 分析判别， 生成issue
# ============================================================
from globals import GraphState, Issue
from typing import Dict
import re
import uuid
from globals import llm
from utils import get_scene_prompt,parse_llm_json
from langchain_core.messages import SystemMessage, HumanMessage
def judge_node(state: GraphState) -> Dict:
    print("\n⚖️ [Judge] 正在分析失败原因")
    print("=" * 60)

    test_code = state.get("test_code", "")
    output = state.get("test_output", "")
    system_prompt, user_prompt = get_scene_prompt(
        file_name='judger',
        scene_name='base',
        test_output=output, test_code=test_code
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    full_content = ""
    # 保持流式打印体验
    for chunk in llm.stream(messages):
        if chunk.content:
            full_content += chunk.content

    result = parse_llm_json(full_content)

    issues = []

    for issue in result:
        type = issue['type']
        assign = 'unknown'
        if type == 'CODE_BUG':
            assign = 'coder'
        if type == 'TEST_BUG':
            assign = 'test_coder'
        if type == "DESIGN_BUG":
            assign = 'human'

        issues.append(Issue(
                issue_id=uuid.uuid4(),
                source='judger',
                type= issue['type'],
                review=issue['review'],
                assign=assign
            ))
    return {
        "issues": issues,
        "test_output": '', # 我们已经转化为issue了，所以test_output为空字符串
        'issue_manager_wait':{'judger'}
    }
