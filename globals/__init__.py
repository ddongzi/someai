
import os
from enum import Enum
from dotenv import load_dotenv
load_dotenv()


GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")

MAX_ATTAMPTS= 5

class GraphName(str, Enum):
    # 
    CODER_GRAPH = "coder_graph"
    TEST_CODER_GRAPH = "test_coder_graph"
    QA_NODE = 'qa_node'
    JUDGE_NODE = 'judge_node'
    HUMAN_NODE = 'human_node'
