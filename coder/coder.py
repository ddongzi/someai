from globals import llm, GENERATED_DIR
from globals import GraphState, Issue, PatchOperation
from typing import Dict
import re
from utils import extract_python_code

FIRST_PROMPT = ""
with open("coder/prompts/first_prompt.md", "r", encoding="utf-8") as f:
    FIRST_PROMPT = f.read()
REVIEW_PROMPT = ""
with open("coder/prompts/review_prompt.md", "r", encoding="utf-8") as f:
    REVIEW_PROMPT = f.read()


def write_code_node(state: GraphState) -> Dict:
    print("\n🤖 [Coder] 开始生成或重构业务代码")
    print("=" * 60)

    spec = state["spec"]
    code_history = state.get("code", "")
    
    current_issue = state.get("current_issue", None)
    review = ""
    
    # 判定当前是否有代码修复单（CODE_BUG）
    if current_issue and current_issue.get('type') == 'CODE_BUG':
        review = current_issue.get('review', '').strip()
        print('🐞 [Coder] 收到业务代码评审修复建议:', review)

    # =====================================================================
    # 动态双轨道路由（Dual-Track Prompting）
    # =====================================================================
    if not review:
        # --------------------------------------------------
        # 轨道 A：初次从零编写（专注无中生有的全量创造）
        # --------------------------------------------------
        print("🆕 [Coder] 当前无评审意见，执行 -> 【首次全新业务代码构建】")
        prompt = FIRST_PROMPT.format(spec=spec)
    else:
        # --------------------------------------------------
        # 轨道 B：改错重构模式（专注对齐、消灭 Review 里的具体缺陷）
        # --------------------------------------------------
        print("🩹 [Coder] 当前存在代码Bug，执行 -> 【强制改错重构】")
        prompt = REVIEW_PROMPT.format(review=review, code_history=code_history)

    # =====================================================================
    # 流式输出与清洗回写
    # =====================================================================
    full_content = ""
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    print("\n" + "=" * 60)

    # 提取代码
    clean_code = extract_python_code(full_content)

    # 鲁棒性清洗：彻底剥离可能产生的多余 Markdown 标记
    clean_code = clean_code.strip()
    if clean_code.startswith("```"):
        clean_code = re.sub(r"^```[a-zA-Z]*\n", "", clean_code)
        clean_code = re.sub(r"\n```$", "", clean_code)

    with open(f"{GENERATED_DIR}/app.py", "w") as f:
        f.write(clean_code)

    return {
        "code": clean_code.strip(),
        "current_issue": None  # 标记当前单个 issue 已经处理完成
    }
