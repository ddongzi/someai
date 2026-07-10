from langgraph.types import interrupt
from globals import GraphState,GitAction, MAX_ATTAMPTS
from typing import Dict
from tools.git import git_tool
from logger import run_logger

def human_node(state: GraphState) -> Dict:
    run_logger.info(f"进入人工干预节点, {state['attempts']}")
    tip = ''
    # human意图？TODO。需要识别意图，引导。
    if state['attempts'] > MAX_ATTAMPTS:
        tip = f'图内节点尝试{state['attempts']}, 次数过多，检查最近的checkpoint 的state, 并修改state,从该checkpoint执行。此次流程将结束，请time-travel fork。'
        human_input = interrupt({
            'tip': tip,
            'type': 'modify_and_time_travel',
            'input_type': 'all',
        })
        run_logger.info(f"人工干预输入: {human_input}")
        return {}
    
    if  state['issue_buckets'].get('human', []):
        tip = f'有issue相关问题。{state['issue_buckets']['human']}. 请修改设计相关部分部文档，或其他未知。然后会自动结束此次流程。重新运行。'
        human_input = interrupt({
            'tip': tip,
            'type': 'modify_design',
            'input_type': 'all',
        })
        run_logger.info(f"人工干预输入: {human_input}")
        return {
            'issue_buckets': {
                'human':[]
            }
        }

    if not state['issues']:
        tip = f'no issue. 成功完成。请人工确认是否提交代码。如果拒绝，提供理由。'
        human_input = interrupt({
            'tip': tip,
            'type': 'approval',
            'input_type': 'choice',
        })
        if human_input == 'approved':
            git_tool.invoke({
                'action': GitAction.commit,
                    'reason': 'Human approved, commit.',
                    'target': ''
            })
        run_logger.info(f"人工干预输入: {human_input}")

        return {}


    human_input = interrupt({
        'tip': 'unexpected!!',
    })
    return {}