from globals import GraphState, GitAction
import logging
import subprocess
import os
project_path = os.getenv('GIT_PROJECT_PATH', '/home/dong/Documents/hello')
logger = logging.getLogger(__name__)

def git_node(state: GraphState):
    git = state["git"]
    if not git:
        logger.info("No git action")
        # 即使什么都不做，也可以返回一个状态说明
        return {'git': None}
        
    branch_name = 'ai'
    
    try:
        if git['target'] == 'checkout':
            subprocess.run(["git", "checkout", branch_name], cwd=project_path, check=True)
            logger.info(f"Checked out branch: {branch_name}")
            # 💡 返回字典更新 state，告知下游节点成功了
            git['result'] = f"Success: Checked out branch {branch_name}"
            return {'git': git}

        if git['action'] == 'commit':
            subprocess.run(["git", "commit", "-m", git['reason']], cwd=project_path, check=True)
            logger.info(f"Committed: {git['reason']}")
            # 💡 返回字典更新 state
            git['result'] = f"Success: Committed with reason: {git['reason']}"
            return {'git': git}
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running git command: {e}")
        # 💡 建议捕获错误并写入 state，而不是直接 raise e 导致程序崩溃
        # 这样大模型才能看到报错，并尝试自己修复（比如发现没 add 就去 commit 时的报错）
        git['result'] = f"Error: {str(e)}"
        return {'git': git}
