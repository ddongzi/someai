# ============================================================
# Test QA Node 测试代码审计
# ============================================================
from globals import GraphState
from typing import Dict
import re
from globals import llm

QA_PROMPT = ""
with open("test/prompts/qa_prompt.md", "r", encoding="utf-8") as f:
    QA_PROMPT = f.read()


def test_qa_node(state: GraphState) -> Dict:
    """
    测试代码审计节点
    
    任务：识别测试代码是否符合要求
    1. 测试代码是否符合软件说明文档中的测试说明部分
    2. 测试代码是否捏造了不存在的错误、异常情况、边界条件等
    3. 测试代码是否强行捏造了类、方法、函数等
    """
    print("\n🔍 [TestQA] 正在审计测试代码质量")
    print("=" * 60)

    spec = state.get("spec", "")
    code = state.get("code", "")
    test_code = state.get("test_code", "")

    prompt = QA_PROMPT.format(spec=spec, code=code, test_code=test_code)

    full_content = ""
    # 流式输出
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    print("\n" + "-" * 40)

    pattern = re.compile(r"TEST_QA_REVIEW:\s*(.*?)\s*$", re.MULTILINE)
    qa_reviews = pattern.findall(full_content)
    qa_reviews = [i.strip() for i in qa_reviews if i.strip()]
    qa_reviews_str = "\n".join(qa_reviews)

    if qa_reviews:
        print(f"⚠️ [TestQA] 发现 {len(qa_reviews)} 个测试代码质量问题")
        return {"test_qa_review": qa_reviews_str}
    else:
        print("✅ [TestQA] 测试代码审计通过，未发现问题")
        return {}
