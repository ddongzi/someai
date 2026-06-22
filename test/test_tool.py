from globals import llm
from typing import Dict
import re   
from langchain_ollama import ChatOllama
from globals import GraphState, Issue, PatchOperation, GENERATED_DIR
import subprocess
import sys

# ============================================================
# Tester Node
# ============================================================
def test_code_node(state: GraphState) -> Dict:

    print("\n🧪 [Tester] 执行pytest测试")
    print("=" * 60)

    attempts = state.get("attempts", 0) + 1

    app_file = f"{GENERATED_DIR}/app.py"
    test_file = f"{GENERATED_DIR}/test.py"

    with open(app_file, "w", encoding="utf-8") as f:
        f.write(state["code"])

    with open(test_file, "w", encoding="utf-8") as f:
        f.write(state["test_code"])

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_file,
                "-q"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        output = result.stdout + "\n" + result.stderr

        print(output)

        return {
            "attempts": attempts,
            "test_output": output,
        }

    except Exception as e:

        return {
            "attempts": attempts,
            "test_output": str(e),
        }