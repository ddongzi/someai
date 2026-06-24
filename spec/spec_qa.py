from globals import llm
from globals import GraphState, Issue, PatchOperation, update_attampts, WorkflowStatus
from typing import Dict
import re
from globals import GENERATED_DIR
import logging

logger = logging.getLogger(__name__)


QA_PROMPT = ""
with open("spec/prompts/qa_prompt.md", "r", encoding="utf-8") as f:
    QA_PROMPT = f.read()


def spec_qa_node(state: GraphState) -> Dict:
    """
    审计软件规格说明文档，识别文档缺陷并输出结构化的审查意见。
    """
    logger.info(f"📋 [SpecQA] 正在审计 spec 文档...")
    logger.info("=" * 60)

    requirement = state.get("requirement", "").strip()
    spec = state.get("spec", "").strip()
    prompt = QA_PROMPT.format(requirement=requirement, spec=spec)
    full_content = ""
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    logger.info("\n" + "=" * 60)

    clean_content = full_content.strip()
    if clean_content.startswith("```"):
        clean_content = re.sub(r"^```\w*\n|```$", "", clean_content, flags=re.MULTILINE).strip()

    pattern = re.compile(r"SPEC_QA_REVIEW:\s*(.*?)\s*$", re.MULTILINE)
    qa_reviews = [item.strip() for item in pattern.findall(clean_content) if item.strip()]

    qa_review = "\n".join(qa_reviews)
    current_issue = state['current_issue']

    if not qa_review:
        state['status'] = WorkflowStatus.SPEC_QA_DONE
    elif current_issue:
        state['status'] = WorkflowStatus.IS_ISSUEING
    else:
        state['status'] = WorkflowStatus.TO_SPEC


    return {
        'status':state['status'],
        'spec_qa_review': qa_review,
    }
