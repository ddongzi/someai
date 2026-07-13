from tools.rag import get_knowledge
from typing import Dict
from tools.git import git_tool
from utils import get_first_pending_task
from globals.state import GraphState, Issue, FileMetadata
from globals.logger import run_logger
prod_file_path = "prod.md"
spec_file_path = "spec.md"
dd_file_path = "dd.md"


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
    # 设置requirement
    task = get_first_pending_task()

    # file_ledger
    app_meta = FileMetadata(
        path='app/app.py',
        description='源代码.',
        permission='none'
    )
    test_meta = FileMetadata(
        path='test/test.py',
        description='测试代码.',
        permission='none'
    )

    return {
        'requirement': task['description'],
        'file_ledger':{
            app_meta['path']: app_meta,
            test_meta['path']: test_meta
        }
    }