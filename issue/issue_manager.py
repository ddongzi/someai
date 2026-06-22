from globals import GraphState, Issue, PatchOperation

def issue_manager_node(state: GraphState) -> dict:
    """
    issue任务队列管理器（纯函数无副作用模式）：
    根据上一步的 patch_success 状态，安全消费队列。
    """
    # 1. 浅拷贝一份当前队列，防止直接修改内存引发并发冲突
    current_issues = list(state.get('issues', []))
    print(f'issue manager is running!, there are {len(current_issues)} issues')
        
    # 3. 边界检查：如果队列已经全空了，说明所有任务修复完毕，准备走向图的结束节点
    if not current_issues:
        return {
            "is_issueing": False,
            "issues": [],
            "current_issue": None,
        }
        
    # 4. 获取当前需要处理的第一个任务
    next_issue = current_issues[0]
    current_issues.pop(0)
    
    # 5. 严格采用 return 模式，把更新后的队列和当前任务一起返回给框架
    return {
        "is_issueing": True,
        "issues": current_issues,   # 更新图里的剩余任务队列
        "current_issue": next_issue, # 声明当前正在攻坚的任务
    }