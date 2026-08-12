"""任务操作相关工具函数：加载、保存、任务状态管理"""

import json
import os
from pathlib import Path

from globals.state import Task

TASKS_FILE = Path("tasks.json")


def save_tasks(tasks: list) -> None:
    """保存任务列表到 tasks.json"""
    TASKS_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_tasks() -> list[dict]:
    """从 tasks.json 加载任务列表，返回原始 dict 列表"""
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def save_task(task: Task) -> None:
    """将单个任务的当前状态更新到 tasks.json 中对应的任务"""
    if not task.id:
        return
    tasks = load_tasks()
    for i, task_dict in enumerate(tasks):
        if task_dict.get("id") == task.id:
            tasks[i] = task.model_dump()
            save_tasks(tasks)
            return


def get_feature_dir() -> str:
    """获取 SPECIFY_FEATURE_DIRECTORY 环境变量"""
    return os.environ.get("SPECIFY_FEATURE_DIRECTORY", "")


def get_generated_dir() -> str:
    """获取 GENERATED_DIR 环境变量，默认 'generated'"""
    return os.environ.get("GENERATED_DIR", "generated")


def get_reference_files(feature_dir: str) -> list[str]:
    """获取 generated/specs/{feature_dir}/ 下所有文件相对于 generated/ 的路径列表"""
    specs_dir = Path(get_generated_dir()) / "specs" / feature_dir
    if not specs_dir.exists():
        return []

    ref_files = []
    for root, _dirs, files in os.walk(specs_dir):
        for f in files:
            abs_path = Path(root) / f
            rel_path = abs_path.relative_to(get_generated_dir())
            ref_files.append(str(rel_path))
    return ref_files


def make_completed_task() -> Task:
    """构造一个表示已完成的空任务"""
    return Task(status="completed")
