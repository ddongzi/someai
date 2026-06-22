from langchain_ollama import ChatOllama
from typing import TypedDict
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

if os.getenv("OPENROUTER_API_KEY"):

    llm = ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="poolside/laguna-m.1:free",  # 云端代码模型
        temperature=0
    )
else:
    llm = ChatOpenAI(
        api_key="sk-e0e6b0a59ae14fd18e760afd9d0d9bac",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",  # 云端代码模型
        temperature=0
    )
# 生成目录
GENERATED_DIR = "generated"

# ============================================================
# State
# ============================================================
class PatchOperation(TypedDict):
    file: str
    action: str
    target: str
    reason: str # patch意图

class Issue(TypedDict):
    issue_id: str # 修复建议ID，唯一标识
    review: str # 修复建议
    type: str # 修复建议类型，CODE_BUG/TEST_BUG/DESIGN_BUG
    patch_plan: list[PatchOperation] # 补丁操作列表

from typing import TypedDict, Optional

class GitAction(TypedDict):
    action: str      # 例如: 动作 'commit', 'checkout'
    target: str      # 例如: 动作承受者 'branch', 'file'
    reason: str      # git意图说明
    result: Optional[str]  # 💡 新增：用来存放这条命令的执行结果（成功/失败的具体日志）

    
class GraphState(TypedDict):

    requirement: str # 用户需求，原始文本

    code: str
    attempts: int # 重试次数，目前是只看tester的重试次数的，因为目前都会跑到tester

    test_code: str  # 测试代码
    test_qa_review: str # 测试代码审计结果
    test_output: str # 测试代码输出

    spec: str # 软件规格说明书
    spec_qa_review: str # 规格说明书审计结果


    is_issueing: bool # 是否正在处理修复建议

    issues: list[Issue]  # 修复建议列表
    current_issue: Issue | None # 当前处理的修复建议

    git: GitAction | None # git操作
