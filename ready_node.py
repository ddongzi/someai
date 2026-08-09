from tools.rag import get_knowledge
from typing import Dict
from tools.git import git_tool
from utils import get_first_pending_task
from globals.state import GraphState, Issue, FileSnapshot
from globals.logger import run_logger
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")


def init_file_ledger() -> Dict[str, FileSnapshot]:
    base_path = Path(GENERATED_DIR).resolve()
    generated_ledger = {}
    
    # 定义需要排除的目录名
    exclude_dirs = {'.git', '.idea', '.vscode', 'node_modules', 'venv', '__pycache__', 'dist'}
    
    # rglob('*') 会递归遍历所有文件和文件夹
    for path in base_path.rglob('*'):
        if any(part.startswith('.') or part in exclude_dirs for part in path.relative_to(base_path).parts):
            continue
            
        if path.is_file():
            rel_path = str(path.relative_to(base_path))
                
            generated_ledger[rel_path] = FileSnapshot(
                file_name=path.name,
                file_path=str(rel_path),
            )
    return generated_ledger

def ready_node(state: GraphState) -> Dict:
    knowledge = get_knowledge()
    # # 1. 加载prod, dd, spec 到向量库
    # for file_path in [prod_file_path, spec_file_path, dd_file_path]:
    #     with open(file_path, mode='r') as f:
    #         knowledge.add_text(f.read(), source=file_path, type='local')
    # 切换到分支 git
    result = git_tool.invoke({
        'action': '',
        'reason': '',
        'target': ''
    })
    run_logger.info(f'git result: {result}')

    file_ledger = init_file_ledger()

    run_logger.info('init file_ledger: ', file_ledger)
            
    return {
        'file_ledger': file_ledger,
    }