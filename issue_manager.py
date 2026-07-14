from globals.state import GraphState, Issue
from globals.logger import run_logger
from collections import defaultdict

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
            "issue_buckets": {}, 
        }
    # 告诉它：如果遇到没见过的 Key，请自动帮我建一个空列表 []
    buckets = defaultdict(list)
    assigns = set()
    
    for issue in all_issues:
        assigns.add(issue['assign'])
    
    for assignee in assigns:
        for issue in state['issues']:
            if issue["assign"] == assignee:
                buckets[assignee].append(issue)
                break

    # 4. 塞进对应 Agent 的专属篮子里
    return {
        "is_issueing": True,
        "issues": [],  # 更新全局队列（拿走的那部分被扣除了）
        # 🟢 只更新当前这个人的篮子，其他人因为 merge_issue_buckets 机制不会被影响
        "issue_buckets": buckets
    }
