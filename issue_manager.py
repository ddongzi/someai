from globals.state import GraphState, Issue
from globals.logger import run_logger

# issue_buckets 的三个固定 bucket key
BUCKET_KEYS = ['coder_graph', 'test_coder_graph', 'human_node']

def _empty_buckets() -> dict:
    return {k: [] for k in BUCKET_KEYS}

def issue_manager_node(state: GraphState) -> dict:
    """
    """
    all_issues = list(state.get('issues', []))
    run_logger.info(f'Issue manager is running! Total remaining issues: {len(all_issues)}')

    # 1. 如果全局没有任务了，清空所有人的篮子并结束
    if not all_issues:
        return {
            "is_issueing": False,
            "issues": [],
            "issue_buckets": _empty_buckets(),
        }

    # 2. 按 assign 分发到对应 Agent 的篮子
    buckets = _empty_buckets()
    for issue in all_issues:
        assignee = issue['assign']
        if assignee in buckets:
            buckets[assignee].append(issue)

    # 3. 塞进对应 Agent 的专属篮子里
    return {
        "is_issueing": True,
        "issues": [],  # 清空全局队列（已分发到各 bucket）
        "issue_buckets": buckets
    }
