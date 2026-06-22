# ============================================================
# Test Judge Node 测试输出 分析判别， 生成issue
# ============================================================
from globals import GraphState, Issue, PatchOperation
from typing import Dict
import re
from globals import llm

JUDGE_PROMPT = ""
with open("test/prompts/judge_prompt.md", "r", encoding="utf-8") as f:
    JUDGE_PROMPT = f.read()
def judge_node(state: GraphState) -> Dict:
    print("\n⚖️ [Judge] 正在分析失败原因")
    print("=" * 60)

    spec = state.get("spec", "")
    test_code = state.get("test_code", "")
    output = state.get("test_output", "")
    prompt = JUDGE_PROMPT.format(spec=spec, test_code=test_code, output=output)
    
    full_content = ""
    # 保持流式打印体验
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    print("\n" + "-" * 40)

    pattern = re.compile(
        r"ISSUE:\s*"
        r"TYPE:\s*(CODE_BUG|TEST_BUG|DESIGN_BUG)\s*"
        r"REVIEW:\s*(.*?)(?=ISSUE:|$)",
        re.DOTALL | re.IGNORECASE
    )

    matches = pattern.findall(full_content)

    issues = []

    for bug_type, review in matches:

        issues.append(
            {
                "type": bug_type.upper(),
                "review": review.strip()
            }
        )
    return {
        "issues": issues,
        "test_output": '' # 我们已经转化为issue了，所以test_output为空字符串
    }
