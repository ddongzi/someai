from typing import Dict
import re   
from langchain_ollama import ChatOllama
import subprocess
import sys
from dotenv import load_dotenv
import os
from globals.state import GraphState, Issue
from globals.logger import run_logger
from globals.llm import get_llm_with_tools,call_llm
from utils import get_file_logger
from tools.rag import knowledge_search
from tools.filer import write_to_file,create_file,read_file, inspect_file_summary,inspect_project,delete_files
from tools.ast import ast_search
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.pytest_tool import run_pytest
from utils import get_scene_prompt
from langchain.messages import SystemMessage, HumanMessage
load_dotenv()
NODE_NAME = __name__

PROMPT_FILE_NAME = 'test_execer'
tools=[
    inspect_project,
]
llm = get_llm_with_tools(tools)

test_execer_logger = get_file_logger(
    logger_name='test_execer',
    filename=NODE_NAME,
    so=True
)

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")
# ============================================================
# Tester Node
# ============================================================
def test_exec_node(state: GraphState) -> Dict:
    system_prompt, user_prompt  = get_scene_prompt(
            file_name=PROMPT_FILE_NAME,
            scene_name='base',
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    for msg in state['messages']:
        messages.append(msg)
    full_content, full_chunk = call_llm(llm, messages, logger=test_execer_logger)
    full_chunk.name = NODE_NAME

    return {
        'test_output': full_content
    }