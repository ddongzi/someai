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
from globals import MAX_ATTAMPTS

from langgraph.graph.state import RunnableConfig
from qa_node import qa_node

from globals import GraphState, Issue, GENERATED_DIR
from utils import extract_python_code
from coder.coder import write_code_node
from issue.issue_manager import issue_manager_node
from test.test_writer import test_writer_node
from test.test_tool import test_code_node
from test.test_judge import judge_node
from globals import llm, GENERATED_DIR
from human_node import human_node
from globals import GitAction
import logging
from tools.pyright_node import pyright_node
logger = logging.getLogger(__name__)
from ready_node import ready_node
from qa_node import qa_node
from utils import draw_workflow_png
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
class MyWorkflow:
    def __init__(self):
        self.workflow = StateGraph(GraphState)
        self.build()
    def build(self):

        def decide_after_issue_manager_node(state: GraphState):
            # 由于这里默认不是并发等待，必须只有齐全了才可以，其余情况下直接pass
            if 'judger' in state['issue_manager_wait'] and 'qaer' in state['issue_manager_wait']: 
                logger.info(f'decide : issues {state['issues']}. current: {state['current_issue']}')
                issues = state['issues']
                if not issues:
                    return "no_issue"
                
                current_issue = state['current_issue']
                if current_issue['assign'] == 'coder':
                    return "code_patcher"
                if current_issue['assign'] == 'test_coder':
                    return "test_code_patcher"
                if current_issue['assign'] == 'human':
                    return "design_patcher"
                logger.warning(f"Unexpected issue assign: {current_issue['assign']}")
                return 'dropped'
            else:
                return "dropped"

        def decide_after_pyright(state: GraphState):
            result = state['pyright_result']
            
            next_steps = []



            # --- 1. 判断业务代码 (Code) ---
            if 'code' in result.keys():
                if len(result['code']) != 0:
                    # 实际上，有code 就有结果，不可能是 []
                    next_steps.append('code_error') 
            else:
                next_steps.append('qa_node')
                    
            # --- 2. 判断测试代码 (Test Code) ---
            if 'test_code' in result.keys():
                if len(result.get('test_code', [])) != 0:
                    # 测试代码有错，加入测试修复队列
                    next_steps.append('test_code_error')
            else:
                next_steps.append('qa_node')

            return list(set(next_steps))


        def decide_after_test_writer(state: GraphState):
            if state['attempts'] > MAX_ATTAMPTS:
                return 'max_attempts'

            return "success"
        def decide_after_coder(state: GraphState):
            if state['attempts'] > MAX_ATTAMPTS:
                return 'max_attempts'
            return "success"
        def decide_after_human_node(state: GraphState):
            return "success"

        self.workflow.add_node('ready_node', ready_node)
        self.workflow.add_node('pyright_node', pyright_node)
        self.workflow.add_node("coder", write_code_node)
        self.workflow.add_node("test_writer", test_writer_node)
        self.workflow.add_node("tester", test_code_node)
        self.workflow.add_node("human_node", human_node)
        self.workflow.add_node('qa_node',qa_node )

        self.workflow.add_node("judge", judge_node)
        self.workflow.add_node("issue_manager_node", issue_manager_node)

        self.workflow.set_entry_point("ready_node")
        self.workflow.add_edge('ready_node', 'coder')
        self.workflow.add_edge('ready_node', 'test_writer')

        self.workflow.add_conditional_edges(
            'coder', 
            decide_after_coder,
            {
                'max_attempts': 'human_node',
                'success':'pyright_node'
            }                  

        )
        self.workflow.add_conditional_edges(
            'test_writer', 
            decide_after_test_writer,
            {
                'max_attempts': 'human_node',
                'success':'pyright_node'
            }                  

        )
        self.workflow.add_conditional_edges(
            'pyright_node',
            decide_after_pyright,
            {   
                'qa_node': 'qa_node',
                'test_code_error': 'test_writer',
                'code_error': 'coder'
            }
        )

        self.workflow.add_edge('qa_node','issue_manager_node')

        self.workflow.add_edge('qa_node','tester')
        self.workflow.add_edge('tester', 'judge')
        self.workflow.add_edge('judge','issue_manager_node')

        self.workflow.add_conditional_edges(
            "human_node",
            decide_after_human_node,
            {
                "success": END,
                "unexpected": END
            }
        )

        self.workflow.add_conditional_edges(
            "issue_manager_node",
            decide_after_issue_manager_node,
            {
                "dropped": END,
                'no_issue': 'human_node', 
                'test_code_patcher': 'test_writer',
                "code_patcher": "coder",
                "design_patcher": "human_node", # human_node
            }
        )
    @asynccontextmanager
    async def setup(self):
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as saver:
            # Your code here
            graph = self.workflow.compile(checkpointer=saver)
            draw_workflow_png(graph)
            self.graph = graph
            yield saver



# ============================================================
# Build Graph
# ============================================================






