# ============================================================
# Test Judge Node 测试输出 分析判别， 生成issue
# ============================================================
from typing import Dict
import re
import uuid
from utils import get_scene_prompt,parse_llm_json
from langchain_core.messages import SystemMessage, HumanMessage
from globals.state import GraphState, Issue
from globals.logger import run_logger
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,create_file,read_file, inspect_file_summary,inspect_project,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references


llm = get_llm_with_tools(tools=[
    ast_search,inspect_project,
    find_symbol_references, find_symbol_definition, 
    read_file,inspect_file_summary
])
def judge_node(state: GraphState) -> Dict:
    run_logger.info("\n⚖️ [Judge] 正在分析失败原因")
    run_logger.info("=" * 60)

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
    
    full_content, full_chunk = call_llm(llm, messages, logger=run_logger)

    result = parse_llm_json(full_content)

    issues = []

    for issue in result:
        type = issue['type']
        assign = 'unknown'
        if type == 'CODE_BUG':
            assign = 'coder_graph'
        if type == 'TEST_BUG':
            assign = 'test_coder_graph'
        if type == "DESIGN_BUG":
            assign = 'human_node'

        issues.append(Issue(
                issue_id=uuid.uuid4(),
                source='judge_node',
                type= issue['type'],
                review=issue['review'],
                assign=assign
            ))
    return {
        "issues": issues,
        "test_output": '', # 我们已经转化为issue了，所以test_output为空字符串
        'issue_manager_wait':{'judge_node'},
        'messages':[full_content]
    }
