from tkinter import NO
from typing import TypedDict, Dict
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import os
import re
import sys
import subprocess

from langgraph.graph.state import RunnableConfig
from test.test_qa import test_qa_node

from globals import GraphState, PatchOperation, Issue, GENERATED_DIR
from utils import extract_python_code
from coder.coder import write_code_node
from issue.issue_manager import issue_manager_node
from test.test_writer import test_writer_node
from test.test_tool import test_code_node
from test.test_judge import judge_node
from spec.spec_writer import spec_writer_node
from globals import llm, GENERATED_DIR
from spec.spec_qa import spec_qa_node
from human_node import human_node
from tools.git_node import git_node
import logging
from globals import  WorkflowStatus
logger = logging.getLogger(__name__)


# ============================================================
# Router
# ============================================================

def decide_after_issue_manager_node(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.TO_TESTER:
        return "no_issue"
    if status == WorkflowStatus.TO_PATCHER_CODE:
        return "code_patcher"
    if status == WorkflowStatus.TO_PATCHER_TEST:
        return "test_code_patcher"
    if status == WorkflowStatus.TO_PATCHER_DESIGN:
        return "design_patcher"

    logger.warning(f"issue_manager_node 未知的状态: {status}")
    return "unexpected"

def decide_after_coder(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.IS_ISSUEING:
        return 'is_issueing'
    return 'success'

def decide_after_test_writer(state: GraphState):
    status = state.get('status', None)
    if status == WorkflowStatus.MAX_ATTEMPTS:
        return 'max_attempts'
    if status == WorkflowStatus.IS_ISSUEING:
        return 'is_issueing'

    return "success"

def decide_after_spec_writer(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.MAX_ATTEMPTS:
        return 'max_attempts'
    return 'success'

def decide_after_judge(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.TO_ISSUE_MANAGER:
        return "need_issue"
    if status == WorkflowStatus.TO_COMMIT:
        return "pass"
    logger.warning(f"judge_node 未知的状态: {status}")
    return "unexpected"
def decide_after_tester(state: GraphState):

    status = state['status']
    if status == WorkflowStatus.MAX_ATTEMPTS:
        return "max_attempts"
    return "success"


def decide_after_test_qa(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.IS_ISSUEING:
        return 'is_issueing'
    if status == WorkflowStatus.TEST_QA_DONE:
        return "success"
    if status == WorkflowStatus.TO_TEST_WRITER:
        return "failed"
    logger.warning(f"test_qa_node 未知的状态: {status}")

    return "unexpected"

def decide_after_spec_qa(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.IS_ISSUEING:
        return 'is_issueing'
    if status == WorkflowStatus.SPEC_QA_DONE:
        return "success"
    if status == WorkflowStatus.TO_SPEC:
        return "failed"
    logger.warning(f"spec_qa_node 未知的状态: {status}")
    return "unexpected"
def decide_after_git(state: GraphState):
    status = state['status']
    if status == WorkflowStatus.GIT_COMMITTED:
        return "success"
    if status == WorkflowStatus.INIT:
        return "to_spec"
    logger.warning(f"git_node 未知的状态: {status}")
    return "unexpected"

def decide_after_human_node(state: GraphState):
    logger.info(f'after human node , {state['status']}')
    if state['status'] == WorkflowStatus.TO_COMMIT:
        return "to_git"
    if state['status'] == WorkflowStatus.GIT_COMMITTED:
        return "success"
    logger.warning(f"human node 未知的状态: {state['status']}")
    return "unexpected"

# ============================================================
# Build Graph
# ============================================================
workflow = StateGraph(GraphState)
workflow.add_node("git_node", git_node)

workflow.add_node("spec", spec_writer_node)
workflow.add_node('spec_qa', spec_qa_node)
workflow.add_node("coder", write_code_node)
workflow.add_node("test_writer", test_writer_node)
workflow.add_node('test_qa', test_qa_node)
workflow.add_node("tester", test_code_node)
workflow.add_node("human_node", human_node)

workflow.add_node("judge", judge_node)
workflow.add_node("issue_manager_node", issue_manager_node)

workflow.set_entry_point("git_node")

workflow.add_conditional_edges(
    "human_node",
    decide_after_human_node,
    {
        "to_git": "git_node",
        "success": END,
        "unexpected": END
    }
)

workflow.add_conditional_edges(
    "git_node",
    decide_after_git,
    {
        'success': 'human_node', # COMMIT成功了
        "to_spec": "spec",
        'unexpected': END
    }
)


workflow.add_conditional_edges(
    "tester",
    decide_after_tester,
    {
        "success": "judge",
        "max_attempts": "human_node"
    }
)

workflow.add_conditional_edges(
    "coder",
    decide_after_coder,
    {
        "success": "test_writer", # 无issue时，正常生成测试代码
        "is_issueing": 'issue_manager_node' # 有issue时，继续修复
    }
)
workflow.add_conditional_edges(
    "test_writer",
    decide_after_test_writer,
       {
        "max_attempts": "human_node",
        "success": "test_qa",
    }
)
workflow.add_conditional_edges(
    'spec',
    decide_after_spec_writer,
    {
        'max_attempts': "human_node",
        'success': 'spec_qa'
    }
)
workflow.add_conditional_edges(
    "spec_qa",
    decide_after_spec_qa,
    {
        'failed': 'spec', # 规格审计失败，回到spec重写
        'success': 'coder', # 规格审计成功，进入代码生成
        'is_issueing': 'issue_manager_node', # 规格审计成功，但当前
        'unexpected': END
    }
)
workflow.add_conditional_edges(
    "test_qa",
    decide_after_test_qa,
    {
        'is_issueing': 'issue_manager_node', #qa成功， 有issue时，继续修复
        "success": "tester", # qa成功，没有issue,正常test
        "failed": 'test_writer',  # qa失败，重新生成测试代码
        'unexpected': END
    }
)


workflow.add_conditional_edges(
    "issue_manager_node",
    decide_after_issue_manager_node,
    {
        'no_issue': 'tester', 
        'test_code_patcher': 'test_writer',
        "code_patcher": "coder",
        "design_patcher": "spec",
        'unexpected': END
    }
)
workflow.add_conditional_edges(
    "judge",
    decide_after_judge,
    {
        "pass": 'human_node',
        "need_issue": "issue_manager_node",
        'unexpected': END
    }
)


from utils import draw_workflow_png

conn = sqlite3.connect("checkpoints.db", check_same_thread=False) 
memory = SqliteSaver(conn) 
app = workflow.compile(checkpointer=memory)
draw_workflow_png(app)

logger.info("workflow compiled !")

