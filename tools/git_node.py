"""
在任何git操作前，先确保当前分支是目标分支，如果不是，则切换到目标分支。
"""

import subprocess
from globals import GraphState, PatchOperation, Issue, GENERATED_DIR,WorkflowStatus
from globals import GitAction
import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv()
project_path = os.getenv("PROJECT_PATH", os.getcwd())
logger = logging.getLogger(__name__)

def git_node(state: GraphState):
    git = state["git"]
    action = git['action']
    # 默认兜底分支为 'ai'
    target_branch = git.get('target_branch', 'ai') 
    
    try:
        # 1. 自动前置处理：确保在正确的分支
        _ensure_branch(target_branch)
        
        # 2. 根据核心业务 Action 分流
        if action == GitAction.COMMIT: # 建议使用 Enum
            _execute_commit(git['reason'])
            git['result'] = f"Success: Commited to {target_branch}"
            state['status'] = WorkflowStatus.GIT_COMMITTED
            return {'git': git}
        
        # git node 在开头运行。
        state['status'] = WorkflowStatus.INIT
        return {
        'status':state['status'],
            'git': git
            }
        
    except subprocess.CalledProcessError as e:
        git['result'] = f"Failed: {e.stderr if e.stderr else str(e)}"
        return {
        'status':state['status'],
            'git': git
            }
def _execute_commit(reason: str):
    """执行 git commit 操作"""
    # 1. 添加所有更改
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    
    # 2. 提交更改
    commit_message = f"AI Commit: {reason}"
    subprocess.run(["git", "commit", "-m", commit_message], cwd=project_path, check=True)

def _ensure_branch(branch_name: str):
    """内部私有方法：确保环境切换到目标分支"""
    # 检查当前分支是否已经是目标分支，避免重复 checkout 浪费时间
    current = subprocess.run(["git", "branch", "--show-current"], cwd=project_path, capture_output=True, text=True).stdout.strip()
    if current == branch_name:
        return
        
    # 尝试切换
    res = subprocess.run(["git", "checkout", branch_name], cwd=project_path, capture_output=True, text=True)
    if res.returncode != 0:
        # 不存在则创建并切换
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=project_path, check=True)
