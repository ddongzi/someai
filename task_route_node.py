"""任务路由节点：从 tasks.json 读取并初始化当前任务，按任务类型进行路由"""

import json
import os
from pathlib import Path
from typing import Dict

from globals.state import GraphState, TaskList, Task
from globals.logger import run_logger
from globals.llm import base_llm, call_llm
from utils import get_scene_prompt
from langchain.messages import SystemMessage, HumanMessage

TASKS_FILE = Path("tasks.json")

llm = base_llm.with_structured_output(TaskList)


def _save_tasks(tasks: list) -> None:
    """保存任务列表到 tasks.json"""
    TASKS_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_tasks() -> list:
    """从 tasks.json 加载任务列表"""
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def _get_feature_dir() -> str:
    """获取 SPECIFY_FEATURE_DIRECTORY 环境变量"""
    return os.environ.get("SPECIFY_FEATURE_DIRECTORY", "")


def _get_generated_dir() -> str:
    """获取 GENERATED_DIR 环境变量，默认 'generated'"""
    return os.environ.get("GENERATED_DIR", "generated")


def _get_reference_files(feature_dir: str) -> list[str]:
    """获取 generated/specs/{feature_dir}/ 下所有文件相对于 generated/ 的路径列表"""
    specs_dir = Path(_get_generated_dir()) / "specs" / feature_dir
    if not specs_dir.exists():
        return []

    ref_files = []
    for root, _dirs, files in os.walk(specs_dir):
        for f in files:
            abs_path = Path(root) / f
            rel_path = abs_path.relative_to(_get_generated_dir())
            ref_files.append(str(rel_path))
    return ref_files


def _make_completed_task() -> Task:
    """构造一个表示已完成的空任务"""
    return Task(
        id="",
        title="",
        status="completed",
        task_type="",
        phase=None,
        phase_number=None,
        user_story=None,
        priority=None,
        parallel=False,
        tags=[],
        target_files=[],
        reference_files=[],
    )


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
        feature_dir = _get_feature_dir()
        if not feature_dir:
            run_logger.warning(
                "[task_route] SPECIFY_FEATURE_DIRECTORY 未设置，无法生成任务"
            )
            return {"current_task": _make_completed_task()}

        # 读取 tasks.md 内容
        tasks_md_path = (
            Path(_get_generated_dir()) / "specs" / feature_dir / "tasks.md"
        )

        if not tasks_md_path.exists():
            run_logger.warning(
                f"[task_route] tasks.md 不存在: {tasks_md_path}"
            )
            return {"current_task": _make_completed_task()}

        tasks_content = tasks_md_path.read_text(encoding="utf-8")
        reference_files = _get_reference_files(feature_dir)
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
        tasks = result.get("tasks", [])

        run_logger.info(f"[task_route] LLM 解析出 {len(tasks)} 个任务")

        # 写入 tasks.json
        _save_tasks(tasks)
    else:
        tasks = _load_tasks()

    # 找到第一个 pending 状态的任务
    for i, task in enumerate(tasks):
        if task.get("status") == "pending":
            current_task = Task(
                id=task.get("id", ""),
                title=task.get("title", ""),
                status="in_progress",
                task_type=task.get("task_type", "code"),
                phase=task.get("phase"),
                phase_number=task.get("phase_number"),
                user_story=task.get("user_story"),
                priority=task.get("priority"),
                parallel=task.get("parallel", False),
                tags=task.get("tags", []),
                target_files=task.get("target_files", []),
                reference_files=task.get("reference_files", []),
            )
            tasks[i]["status"] = "in_progress"
            _save_tasks(tasks)

            run_logger.info(f"current task: {current_task}")

            return {"current_task": current_task}

    # 没有待处理的任务
    run_logger.info("[task_route] 所有任务已完成")
    return {"current_task": _make_completed_task()}
