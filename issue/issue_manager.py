from globals import GraphState, Issue 

def issue_manager_node(state: GraphState) -> dict:
    """
    issue任务队列管理器
    根据上一步的 patch_success 状态，安全消费队列。
    """
    completed_nodes = state.get("issue_manager_wait", set())
    if "judger" not in completed_nodes or "qaer" not in completed_nodes:
        return {}

    issues = list(state.get('issues', []))
    print(f'issue manager is running!, there are {len(issues)} issues')
    
    if not issues:
        return {
            "issue_manager_wait":set(),
            "is_issueing": False,
            "issues": [],
            "current_issue": None,
        }
        
    # 4. 获取当前需要处理的第一个任务
    next_issue = issues[0]
    issues.pop(0)
    
    return {
        "issue_manager_wait":set(),
        "is_issueing": True,
        "issues": issues,   # 更新图里的剩余任务队列
        "current_issue": next_issue, # 声明当前正在攻坚的任务
    }