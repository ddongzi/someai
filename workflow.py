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

from utils import extract_python_code
from graphs.coder_graph import graph as coder_graph
from graphs.test_coder_graph import graph as test_coder_graph
from graphs.qa_graph import graph as qa_graph
from issue_manager import issue_manager_node
from graphs.test_exec_graph import graph as test_execer_graph
from graphs.judge_graph import graph as judge_graph
from human_node import human_node
import logging

from ready_node import ready_node
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

            issue_buckets = state['issue_buckets']

            if 'coder_graph' in issue_buckets.keys() and issue_buckets['coder_graph']:
                return "code_patcher"
            if 'test_coder_graph' in issue_buckets.keys() and issue_buckets['test_coder_graph']:
                return "test_code_patcher"
            if 'human_node' in issue_buckets.keys() and issue_buckets['human_node']:
                return "design_patcher"

            return 'no_issue'

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

        self.graph.add_node("test_execer_graph", test_execer_graph)
        self.graph.add_node("human_node", human_node)
        self.graph.add_node('qa_graph',qa_graph )

        self.graph.add_node("judge_graph", judge_graph)
        self.graph.add_node("issue_manager_node", issue_manager_node)

        self.graph.set_entry_point("ready_node")
        self.graph.add_edge('ready_node', 'coder_graph')
        self.graph.add_edge('ready_node', 'test_coder_graph')
        

        self.graph.add_conditional_edges(
            'coder_graph', 
            decide_after_coder_graph,
            {
                'max_attempts': 'human_node',
                'success':'qa_graph',
                'unexpected': END
            }                  

        )
        self.graph.add_conditional_edges(
            'test_coder_graph', 
            decide_after_test_coder_graph,
            {
                'max_attempts': 'human_node',
                'success':'qa_graph',
                'unexpected': END
            }                  

        )

        self.graph.add_edge('qa_graph','test_execer_graph')
        self.graph.add_edge('test_execer_graph', 'judge_graph')
        self.graph.add_edge('judge_graph','issue_manager_node')

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
                'no_issue': 'human_node', 
                'test_code_patcher': 'test_coder_graph',
                "code_patcher": "coder_graph",
                "design_patcher": "human_node", # human_node
            }
        )

        
    @asynccontextmanager
    async def setup(self):
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as saver:
            self.graph  = self.graph.compile(checkpointer=saver)
            draw_workflow_png(self.graph.get_graph(), 'workflow')
            yield saver




