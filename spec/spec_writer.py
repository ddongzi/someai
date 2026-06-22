from globals import llm
from globals import GraphState, Issue, PatchOperation
from typing import Dict
import re
from globals import GENERATED_DIR
import logging

logger = logging.getLogger(__name__)


FIRST_PROMPT = ""
with open("spec/prompts/first_prompt.md", "r", encoding="utf-8") as f:
    FIRST_PROMPT = f.read()

QA_REVIEW_PROMPT = ""
with open("spec/prompts/writer_qa_review_prompt.md", "r", encoding="utf-8") as f:
    QA_REVIEW_PROMPT = f.read()


REPAIR_PROMPT = """
- 角色：高级软件工程师 & 架构设计专家
- 目标：根据下面的 [必须立刻修复的评审建议]，对已有的历史软件说明文档进行增量重构与精密修复。

【最高行动红线】
1. 你必须逐字阅读下面的 [必须立刻修复的评审建议]，并在新输出的文档中将其完全彻底解决（例如：如果评审说规格未定义最大密码长度，你必须在第5部分追加对应的常量配置，并在第1或第2部分的检查条件中加上对应的长度限制约束）。
2. 你必须原封不动地保留原本已经设计好的其他正确功能、类、接口和异常定义，绝对禁止删减或无故推翻原有的优秀架构设计。

### 1. 【必须立刻修复的评审建议】
============================================================
{review}
============================================================

### 2. 待重构修复的历史说明文档旧版本（在这个底盘的基础上去打补丁、纠正错误）
============================================================
{spec_history}
============================================================

### 3. 原始开发需求背景
============================================================
{requirement}
============================================================

# [输出规范提示]
请不要输出任何多余的寒暄语、大白话解释或 Markdown 代码块框。直接从修改完的全新的“1 系统基本功能”开始输出，完整覆盖 1 到 5 部分的全新规格书。
"""

def _get_spec_history(state: GraphState) -> str:
    return state.get("spec", "").strip()


def _build_writer_prompt(requirement: str, spec_history: str, state: GraphState) -> str:
    current_issue = state.get("current_issue", None)
    spec_qa_review = state.get("spec_qa_review", "").strip()

    if spec_qa_review:
        return QA_REVIEW_PROMPT.format(spec=spec_history, spec_qa_review=spec_qa_review,requirement=requirement)

    if current_issue and current_issue.get("type") == "DESIGN_BUG":
        review = current_issue.get("review", "").strip()
        if review:
            return REPAIR_PROMPT.format(review=review, spec_history=spec_history, requirement=requirement)

    logger.info("🆕 [SpecWriter] 当前无评审意见，执行 -> 【首次全新架构设计构建】")
    return FIRST_PROMPT.format(requirement=requirement)


def _stream_llm_response(prompt: str) -> str:
    full_content = ""
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    print("\n" + "=" * 60)
    return full_content


def _clean_spec_content(raw_content: str) -> str:
    clean_content = raw_content.strip()
    if clean_content.startswith("```"):
        clean_content = re.sub(r"^```\w*\n|```$", "", clean_content, flags=re.MULTILINE).strip()
    return clean_content


def _persist_spec_content(clean_content: str) -> None:
    with open(f"{GENERATED_DIR}/spec.md", "w", encoding="utf-8") as f:
        f.write(clean_content)


def spec_writer_node(state: GraphState) -> Dict:
    """
    根据用户需求
    """
    attempts = state.get("attempts", 0)
    logger.info(f"\n📋 [SpecWriter] 正在编写或重构软件规格说明书...{attempts}")
    logger.info("=" * 60)

    requirement = state.get("requirement", "").strip()
    spec_history = _get_spec_history(state)
    prompt = _build_writer_prompt(requirement, spec_history, state)

    raw_content = _stream_llm_response(prompt)
    clean_content = _clean_spec_content(raw_content)
    _persist_spec_content(clean_content)

    attempts = state.get("attempts", 0) + 1

    return {
        "attempts": attempts,
        "spec": clean_content,
        "current_issue": None
    }
