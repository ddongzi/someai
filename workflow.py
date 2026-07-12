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

from utils import extract_python_code
from graphs.coder_graph import graph as coder_graph
from graphs.test_coder_graph import graph as test_coder_graph
from issue_manager import issue_manager_node
from test_exec_node import test_exec_node
from test_judge import judge_node
from human_node import human_node
import logging
from pyright_node import pyright_node

from ready_node import ready_node
from qa_node import qa_node
from utils import draw_workflow_png
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage
from dotenv import load_dotenv

from globals.state import GraphState, Issue
from globals.logger import run_logger


load_dotenv()

class MyWorkflow:
    def __init__(self):
        self.graph = StateGraph(GraphState)
        self.build()
    def build(self):

        def decide_after_issue_manager_node(state: GraphState):
            # 由于这里默认不是并发等待，必须只有齐全了才可以，其余情况下直接pass
            if 'judger' in state['issue_manager_wait'] and 'qaer' in state['issue_manager_wait']: 
                issues = state['issues']
                if not issues:
                    return "no_issue"
                
                issue_buckets = state['issue_buckets']
                if 'coder' in issue_buckets.keys():
                    return "code_patcher"
                if 'test_coder' in issue_buckets.keys():
                    return "test_code_patcher"
                if 'human' in issue_buckets.keys():
                    return "design_patcher"
                run_logger.warning(f"Unexpected issue assign: {issue_buckets.keys()}")
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


        def decide_after_test_coder_graph(state: GraphState):
            run_logger.info(f'test coder graph done!')

            if state['attempts'] > MAX_ATTAMPTS:
                return 'max_attempts'
            if state['test_coder_subgraph_status'] == 'success':
                return 'success'
            return 'unexpected'
        

        def decide_after_coder_graph(state: GraphState):
            run_logger.info(f'coder graph done!')

            if state['attempts'] > MAX_ATTAMPTS:
                return 'max_attempts'
            if state['coder_subgraph_status'] == 'success':
                return 'success'
            return 'unexpected'
        def decide_after_human_node(state: GraphState):
            return "success"

        self.graph.add_node('ready_node', ready_node)

        self.graph.add_node('coder_graph', coder_graph)
        self.graph.add_node('test_coder_graph', test_coder_graph)

        self.graph.add_node('pyright_node', pyright_node)
        self.graph.add_node("tester", test_exec_node)
        self.graph.add_node("human_node", human_node)
        self.graph.add_node('qa_node',qa_node )

        self.graph.add_node("judge", judge_node)
        self.graph.add_node("issue_manager_node", issue_manager_node)

        self.graph.set_entry_point("ready_node")
        self.graph.add_edge('ready_node', 'coder_graph')
        self.graph.add_edge('ready_node', 'test_coder_graph')
        

        self.graph.add_conditional_edges(
            'coder_graph', 
            decide_after_coder_graph,
            {
                'max_attempts': 'human_node',
                'success':'pyright_node',
                'unexpected': END
            }                  

        )
        self.graph.add_conditional_edges(
            'test_coder_graph', 
            decide_after_test_coder_graph,
            {
                'max_attempts': 'human_node',
                'success':'pyright_node',
                'unexpected': END
            }                  

        )
        self.graph.add_conditional_edges(
            'pyright_node',
            decide_after_pyright,
            {   
                'qa_node': 'qa_node',
                'test_code_error': 'test_coder_graph',
                'code_error': 'coder_graph'
            }
        )

        self.graph.add_edge('qa_node','issue_manager_node')

        self.graph.add_edge('qa_node','tester')
        self.graph.add_edge('tester', 'judge')
        self.graph.add_edge('judge','issue_manager_node')

        self.graph.add_conditional_edges(
            "human_node",
            decide_after_human_node,
            {
                "success": END,
                "unexpected": END
            }
        )

        self.graph.add_conditional_edges(
            "issue_manager_node",
            decide_after_issue_manager_node,
            {
                "dropped": END,
                'no_issue': 'human_node', 
                'test_code_patcher': 'test_coder_graph',
                "code_patcher": "coder_graph",
                "design_patcher": "human_node", # human_node
            }
        )

        
    @asynccontextmanager
    async def setup(self):
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as saver:
            # Your code here
            self.graph  = self.graph.compile(checkpointer=saver)
            draw_workflow_png(self.graph.get_graph(), 'workflow')
            yield saver




