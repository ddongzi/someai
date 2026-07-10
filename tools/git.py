"""
在任何git操作前，先确保当前分支是目标分支，如果不是，则切换到目标分支。
"""

import subprocess
import logging
import os
import sys
from dotenv import load_dotenv
from enum import Enum
from langchain.tools import tool
from typing import Optional
load_dotenv()
project_path = os.getenv("PROJECT_PATH", os.getcwd())
from logger import run_logger

branch_name = 'ai'
class GitAction(str, Enum):
    NONE = "none"
    COMMIT = "commit"
    PUSH = "push"
@tool
def git_tool(
    action: str, 
    target: str,
    reason: Optional[str] = None, 
) -> str:
    """
    执行 Git 相关的操作（如代码提交 Commit）。
    
    Args:
        action (str): 执行的 Git 动作，目前支持 'commit', 为''时仅切换分支
        target (str): 表示git动作的 承受者。 'branch', 'file' 等，暂时不重要
        reason (Optional[str]): 提交代码的原因或 Commit Message。当 action 为 'commit' 时必填。
    
    Returns:
        str: 执行结果的文本描述。
    """
    run_logger.info('git tool')
    # 参数校验（防止 LLM 漏传核心参数）
    if action == GitAction.COMMIT and not reason:
        return "Failed: 'reason' (commit message) is required for a commit action."

    try:
        # 1. 自动前置处理：确保在正确的分支
        _ensure_branch(branch_name)
        
        # 2. 根据核心业务 Action 分流
        if action == GitAction.COMMIT:
            _execute_commit(reason)
            return f"Success: Committed to {branch_name} with reason: '{reason}'"
        
        return f"Warning: Action '{action}' was recognized but no specific execution was triggered."
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        return f"Failed to execute git action: {error_msg}"
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
