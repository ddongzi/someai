from globals import llm
from typing import Dict
import re   
from langchain_ollama import ChatOllama
from globals import GraphState, Issue
import subprocess
import sys
from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)

load_dotenv()

# 读取环境变量，如果 .env 里没配，则自动降级使用默认值 "generated"
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")
# ============================================================
# Tester Node
# ============================================================
def test_code_node(state: GraphState) -> Dict:

    logger.info("\n🧪 [Tester] 执行pytest测试")
    logger.info("=" * 60)



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

        logger.info(output)

        return {
            "attempts":  1,
            "test_output": output,
        }

    except Exception as e:

        return {
            "attempts": 1,
            "test_output": str(e),
        }