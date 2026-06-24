from globals import GraphState, Issue, PatchOperation,WorkflowStatus

def issue_manager_node(state: GraphState) -> dict:
    """
    issue任务队列管理器（纯函数无副作用模式）：
    根据上一步的 patch_success 状态，安全消费队列。
    """
    # 1. 浅拷贝一份当前队列，防止直接修改内存引发并发冲突
    current_issues = list(state.get('issues', []))
    print(f'issue manager is running!, there are {len(current_issues)} issues')
        
    if not current_issues:
        state['status'] = WorkflowStatus.TO_TESTER
        return {
            "is_issueing": False,
            "issues": [],
            "current_issue": None,
        }
        
    # 4. 获取当前需要处理的第一个任务
    next_issue = current_issues[0]
    current_issues.pop(0)
    
    if next_issue['type'] == 'CODE_DEBUG':
        state['status'] = WorkflowStatus.TO_PATCHER_CODE
    if next_issue['type'] == 'DESIGN_BUG':
        state['status'] = WorkflowStatus.TO_PATCHER_DESIGN
    if next_issue['type'] == 'TEST_BUG':
        state['status'] = WorkflowStatus.TO_PATCHER_TEST
    
    return {
        'status':state['status'],

        "is_issueing": True,
        "issues": current_issues,   # 更新图里的剩余任务队列
        "current_issue": next_issue, # 声明当前正在攻坚的任务
    }