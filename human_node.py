from langgraph.types import interrupt
from typing import Dict
from tools.git import git_tool
from globals import MAX_ATTAMPTS
from globals.state import GraphState, Issue
from globals.logger import run_logger

def human_node(state: GraphState) -> Dict:
    run_logger.info(f"进入人工干预节点, {state['attempts']}")
    tip = ''
    # human意图？TODO。需要识别意图，引导。

    # if 判断有先后,不要改变
    
    if  state['issue_buckets'].get('human_node', []):
        tip = f'有issue相关问题。{state['issue_buckets']['human_node']}. 请修改设计相关部分部文档，或其他未知。然后会自动结束此次流程。重新运行。'
        human_input = interrupt({
            'tip': tip,
            'type': 'modify_design',
            'input_type': 'all',
        })
        run_logger.info(f"人工干预输入: {human_input}")
        return {
            'issue_buckets': {
                'human_node':[]
            }
        }


    if state['attempts'] > MAX_ATTAMPTS:
        tip = f'图内节点尝试{state['attempts']}, 次数过多，检查最近的checkpoint 的state, 并修改state,从该checkpoint执行。此次流程将结束，请time-travel fork。'
        human_input = interrupt({
            'tip': tip,
            'type': 'modify_and_time_travel',
            'input_type': 'all',
        })
        run_logger.info(f"人工干预输入: {human_input}")
        return {}
    
    if not state['issue_buckets']['human_node'] and not state['issue_buckets']['coder_graph'] and not state['issue_buckets']['test_coder_graph'] :
        tip = f'no issue. 成功完成。请人工确认是否提交代码。如果拒绝，提供理由。'
        human_input = interrupt({
            'tip': tip,
            'type': 'approval',
            'input_type': 'choice',
        })
        if human_input == 'approved':
            git_tool.invoke({
                'action': 'commit',
                    'reason': 'No issue.! Human approved, commit.',
                    'target': ''
            })
        run_logger.info(f"人工干预输入: {human_input}")

        return {}
    human_input = interrupt({
        'tip': 'unexpected!!',
    })
    return {}