"""任务路由节点：从 tasks.json 读取并初始化当前任务，按任务类型进行路由"""

import json
from pathlib import Path
from typing import Dict

from globals.state import GraphState, Task
from globals.logger import run_logger

TASKS_FILE = Path("tasks.json")


def _load_tasks() -> list[dict]:
    """从 tasks.json 加载全部任务"""
    if not TASKS_FILE.exists():
        run_logger.error(f"[task_route] {TASKS_FILE} 不存在")
        return []
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))["tasks"]


def _save_tasks(tasks: list[dict]) -> None:
    """将任务列表写回 tasks.json"""
    data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    data["tasks"] = tasks
    TASKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def task_route_node(state: GraphState) -> Dict:
    """
    初始化当前执行任务：
    1. 从 tasks.json 读取所有任务
    2. 找到第一个 pending 任务，更新状态为 in_progress
    3. 将任务写入 tasks.json 并设为 current_task
    """
    run_logger.info('task route node...')
    tasks = _load_tasks()

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
            )
            tasks[i]["status"] = "in_progress"
            _save_tasks(tasks)

            run_logger.info(
                f"current task: {current_task}"
            )

            return {"current_task": current_task}

    # 没有待处理的任务
    run_logger.info("[task_route] 所有任务已完成")
    return {
        "current_task": Task(
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
        ),
    }


