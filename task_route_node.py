"""任务路由节点：从 tasks.json 读取并初始化当前任务，按任务类型进行路由"""

from pathlib import Path
from typing import Dict

from globals.state import GraphState, TaskList
from globals.logger import run_logger
from globals.llm import get_llm
from utils import get_scene_prompt
from task_helper import (
    save_tasks,
    load_tasks,
    get_feature_dir,
    get_generated_dir,
    get_reference_files,
    make_completed_task,
)

from globals.state import Task
from langchain.messages import SystemMessage, HumanMessage

TASKS_FILE = Path("tasks.json")

llm = get_llm().with_structured_output(TaskList)


def task_route_node(state: GraphState) -> Dict:
    """
    任务路由节点：
    1. 如果 tasks.json 不存在，从 generated/specs/{SPECIFY_FEATURE_DIRECTORY}/tasks.md
       读取内容并让 LLM 解析成结构化任务列表，保存到 tasks.json
    2. 从 tasks.json 中找到第一个 pending 状态的任务，设为 in_progress 并返回
    3. 如果没有待处理任务，返回 completed 状态的空任务
    """

    run_logger.info("task route node...")

    if not TASKS_FILE.exists():
        feature_dir = get_feature_dir()
        if not feature_dir:
            run_logger.warning(
                "[task_route] SPECIFY_FEATURE_DIRECTORY 未设置，无法生成任务"
            )
            return {"current_task": make_completed_task()}

        # 读取 tasks.md 内容
        tasks_md_path = (
            Path(get_generated_dir()) / "specs" / feature_dir / "tasks.md"
        )

        if not tasks_md_path.exists():
            run_logger.warning(
                f"[task_route] tasks.md 不存在: {tasks_md_path}"
            )
            return {"current_task": make_completed_task()}

        tasks_content = tasks_md_path.read_text(encoding="utf-8")
        reference_files = get_reference_files(feature_dir)
        reference_files_str = "\n".join(reference_files)

        run_logger.info(
            f"[task_route] 读取 tasks.md 成功，参考文件数: {len(reference_files)}"
        )

        # 构造 prompt 并调用 LLM 解析任务
        system_prompt, user_prompt = get_scene_prompt(
            file_name="task_parse_prompt",
            scene_name="base",
            tasks_content=tasks_content,
            reference_files=reference_files_str,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # 使用 structured output，invoke 直接返回 TaskList 对象
        result: TaskList = llm.invoke(messages)
        # result.tasks 是 List[Task]（Pydantic model），转为 dict 列表方便后续处理
        tasks = [t.model_dump() for t in result.tasks]

        run_logger.info(f"[task_route] LLM 解析出 {len(tasks)} 个任务")

        # 写入 tasks.json
        save_tasks(tasks)
    else:
        tasks = load_tasks()

    # 先找 in_progress 的任务
    for i, task_dict in enumerate(tasks):
        if task_dict.get("status") == "in_progress":
            current_task = Task(**task_dict)
            run_logger.info(f"current task: {current_task}")
            return {"current_task": current_task}

    # 再找第一个 pending 的任务，设为 in_progress
    for i, task_dict in enumerate(tasks):
        if task_dict.get("status") == "pending":
            task_dict["status"] = "in_progress"
            current_task = Task(**task_dict)
            tasks[i]["status"] = "in_progress"
            save_tasks(tasks)

            run_logger.info(f"current task: {current_task}")

            return {"current_task": current_task}

    # 没有待处理的任务
    run_logger.info("[task_route] 所有任务已完成")
    return {"current_task": make_completed_task()}
