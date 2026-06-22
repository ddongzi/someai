from globals import llm, GraphState, Issue, PatchOperation
from typing import Dict
import re
from globals import GENERATED_DIR
from utils import extract_python_code, get_all_files_in_dir
FIRST_PROMPT = ""
with open("test/prompts/writer_first_prompt.md", "r", encoding="utf-8") as f:
    FIRST_PROMPT = f.read()

QA_REVIEW_PROMPT = ""
with open("test/prompts/writer_qa_review_prompt.md", "r", encoding="utf-8") as f:
    QA_REVIEW_PROMPT = f.read()

ISSUE_REVIEW_PROMPT = ""
with open("test/prompts/writer_issue_review_prompt.md", "r", encoding="utf-8") as f:
    ISSUE_REVIEW_PROMPT = f.read()


def _get_parse_llm_out(prompt: str) -> str:
    # =====================================================================
    # 流式流式输出与清洗回写
    # =====================================================================
    full_content = ""
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content
    print("\n" + "=" * 60)

    # 调用你的标准 Python 提取函数
    test_code = extract_python_code(full_content)

    # 鲁棒性清洗：彻底剥离 Markdown 标记
    test_code = test_code.strip()
    if test_code.startswith("```"):
        test_code = re.sub(r"^```[a-zA-Z]*\n", "", test_code)
        test_code = re.sub(r"\n```$", "", test_code)

    return test_code

def _deal_qa_review(test_qa_review: str, test_code: str, spec: str) -> str:
    prompt = QA_REVIEW_PROMPT.format(test_qa_review=test_qa_review, test_code=test_code, spec=spec)
    test_code = _get_parse_llm_out(prompt)
    return test_code

def _write_test_code(test_code: str) -> None:
    with open(f"{GENERATED_DIR}/test.py", "w", encoding="utf-8") as f:
        f.write(test_code)

def _deal_issue_review(issue: Issue) -> str:
    prompt = ISSUE_REVIEW_PROMPT.format(issue=issue)
    test_code = _get_parse_llm_out(prompt)
    return test_code

def test_writer_node(state: GraphState) -> Dict:
    print("\n📝 [TestWriter] 正在生成或重构自动化测试")
    print("=" * 60)

    spec = state["spec"]
    code = state["code"]
    test_code = state.get("test_code", "")
    test_qa_review = state.get("test_qa_review", "")

    current_issue = state.get("current_issue", None)

    attempts = state.get("attempts", 0)
    attempts += 1
    print(f"当前尝试次数: {attempts}")

    all_files = get_all_files_in_dir(".")

    # 如果有代码审计意见，先处理代码审计意见
    if test_qa_review:
        print("处理代码审计意见")
        test_code = _deal_qa_review(test_qa_review, test_code, spec)
        _write_test_code(test_code)
        return {
            "attempts": attempts,
            "test_code": test_code,
            "test_qa_review": '',
        }

    # 如果有测试输出评审建议
    if current_issue and current_issue.get('type') == 'TEST_BUG':
        print("处理测试输出评审建议")
        test_code = _deal_issue_review(current_issue)
        _write_test_code(test_code)
        return {
            "attempts": attempts,
            "test_code": test_code,
            "current_issue": None,
        }

    # 第一次生成测试代码
    prompt = FIRST_PROMPT.format(spec=spec, code=code, GENERATED_DIR=GENERATED_DIR)
    test_code = _get_parse_llm_out(prompt)
    _write_test_code(test_code)

    return {
        "attempts": attempts,
        "test_code": test_code.strip(),
    }
    