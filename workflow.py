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
logger = logging.getLogger(__name__)

MAX_ATTAMPTS= 2
# ============================================================
# Router
# ============================================================

def decide_after_issue_manager_node(state: GraphState):
    current_issue = state.get("current_issue", None)
    if not current_issue:
        return "no_issue"
    # test code 和 code bug 都是代码修复
    if current_issue['type'] == 'TEST_BUG' :
        return "test_code_patcher"
    if current_issue['type'] == 'CODE_BUG':
        return "code_patcher"
    # design bug 是spec.md修复
    if current_issue['type'] == 'DESIGN_BUG':
        return "design_patcher"
    raise ValueError(f"未知的issue类型: {current_issue['type']}")

def decide_after_coder(state: GraphState):
    if state.get('is_issueing', False):
        return 'is_issueing'
    return 'success'

def decide_after_test_writer(state: GraphState):
    attempts = state.get("attempts", 0)
    if attempts >= MAX_ATTAMPTS:
        return 'max_attempts'

    if state.get('is_issueing', False):
        return 'is_issueing'
    
    return "success"

# 检查是否正在处理issue
def decide_after_spec_writer(state: GraphState):
    attempts = state.get("attempts", 0)
    if attempts >= MAX_ATTAMPTS:
        return 'max_attempts'
    return 'success'

def decide_after_judge(state: GraphState):
    issues = state.get("issues", [])
    if not issues:
        return "need_issue"
    else:
        return "failed"

def decide_after_tester(state: GraphState):
    attempts = state.get("attempts", 0)
    if attempts >= MAX_ATTAMPTS:
        return "max_attempts"
    return "success"

def decide_after_test_qa(state: GraphState):
    test_qa_review = state.get("test_qa_review", "")

    if test_qa_review == "":
        if state.get('is_issueing', False):
            return 'is_issueing'
        return "success"
    else:
        return "failed"

def decide_after_spec_qa(state: GraphState):
    spec_qa_review = state.get("spec_qa_review", "")
    if spec_qa_review == "":
        if state.get('is_issueing', False):
            return 'is_issueing'
        return "success"
    else:
        return "failed"
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
workflow.add_edge("git_node", "spec")


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
        'is_issueing': 'issue_manager_node' # 规格审计成功，但当前
    }
)
workflow.add_conditional_edges(
    "test_qa",
    decide_after_test_qa,
    {
        'is_issueing': 'issue_manager_node', #qa成功， 有issue时，继续修复
        "success": "tester", # qa成功，没有issue,正常test
        "failed": 'test_writer'  # qa失败，重新生成测试代码
    }
)


workflow.add_conditional_edges(
    "issue_manager_node",
    decide_after_issue_manager_node,
    {
        'no_issue': 'tester', # 没有issue时，正常test
        'test_code_patcher': 'test_writer',
        "code_patcher": "coder",
        "design_patcher": "spec",
    }
)
workflow.add_conditional_edges(
    "judge",
    decide_after_judge,
    {
        "pass": END,
        "need_issue": "issue_manager_node"
    }
)

if __name__ == "__main__":

    conn = sqlite3.connect("checkpoints.db", check_same_thread=False) 
    memory = SqliteSaver(conn) 
    app = workflow.compile(checkpointer=memory)


def draw_workflow_png(app):
    graph = app.get_graph()
    # 1. 导出原始mermaid字符串
    mermaid_text = graph.draw_mermaid()
    # 替换布局为竖向TD，增加样式
    mermaid_text = mermaid_text.replace(
        "graph LR",
        """graph TD
        classDef node fill:#f0f8ff,stroke:#2c3e50,stroke-width:1.5
        linkStyle all stroke:#555,stroke-width:1
        """
    )
    # 写入mmd文件
    with open("workflow.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_text)
    logger.info("已生成 workflow.mmd")

    png_data = graph.draw_mermaid_png()
    with open("workflow.png", "wb") as f:
        f.write(png_data)
        logger.info("workflow png saved.")
draw_workflow_png(app)