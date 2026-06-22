from langgraph.types import interrupt
from globals import GraphState
def human_node(state: GraphState) -> GraphState:
    # 1. 挂起并暴露当前的错误现场给外部
    human_input = interrupt({
        'warning': '请手动输入state',
        'state': state
    })
    
    print(f"✍️ 收到人工修正的数据: {human_input}")
    
    # 2. ❌ 错误：return state (数据没变)
    # 2.  正确：返回人工修正后的数据字典。
    # LangGraph 会自动将返回的字典与原 State 进行 Merge（合并更新）
    return human_input  
