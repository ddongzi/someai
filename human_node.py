from langgraph.types import interrupt
from globals import GraphState,WorkflowStatus,GitAction
from typing import Dict
import logging
logger = logging.getLogger(__name__)
def human_node(state: GraphState) -> Dict:
    logger.info("进入人工干预节点")
    human_input = interrupt({
        'warning': '请手动输入state',
        'state': state
    })
    logger.info(f"✍️ 收到人工修正的数据: {human_input}")

    if human_input == 'approved':
        git = state['git']
        git['action'] = GitAction.COMMIT
        git['reason'] = 'ai no reason....'
        git['target'] = 'all'

        state['status'] = WorkflowStatus.TO_COMMIT
        logger.info(f"human status : {state['status']}")

    return {
        'status': state['status'],
        'git': git
    }
