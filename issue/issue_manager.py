from globals import GraphState, Issue 

def issue_manager_node(state: GraphState) -> dict:
    """
    """
    completed_nodes = state.get("issue_manager_wait", set())
    if "judger" not in completed_nodes or "qaer" not in completed_nodes:
        return {}

    all_issues = list(state.get('issues', []))
    print(f'Issue manager is running! Total remaining issues: {len(all_issues)}')
    
    # 1. 如果全局没有任务了，清空所有人的篮子并结束
    if not all_issues:
        return {
            "issue_manager_wait": set(),
            "is_issueing": False,
            "issues": [],
            "issue_buckets": {}, 
        }
    
    buckets = {}
    assigns = set()
    remaining_issues = state['issues'].copy()
    
    for issue in all_issues:
        assigns.add(issue.assign)
    
    for assignee in assigns:
        for issue in state['issues']:
            if issue.assign == assignee:
                buckets[assignee].append(issue)
                remaining_issues.remove(issue)
                break

    # 4. 塞进对应 Agent 的专属篮子里
    return {
        "issue_manager_wait": set(),
        "is_issueing": True,
        "issues": remaining_issues,  # 更新全局队列（拿走的那部分被扣除了）
        # 🟢 只更新当前这个人的篮子，其他人因为 merge_issue_buckets 机制不会被影响
        "issue_buckets": buckets
    }
