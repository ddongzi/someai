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
    """从 tasks.json 加载任务列表，返回原始 dict 列表；文件不存在时返回空列表"""
    if not TASKS_FILE.exists():
        return []
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def save_task(task: Task) -> None:
    """将单个任务的当前状态更新到 tasks.json 中对应的任务"""
    if not task['id']:
        return
    tasks = load_tasks()
    for i, task_dict in enumerate(tasks):
        if task_dict.get("id") == task['id']:
            tasks[i]['status'] = task['status']
            save_tasks(tasks)
            return


def get_feature_dir() -> str:
    """获取 SPECIFY_FEATURE_DIRECTORY 环境变量"""
    return os.environ.get("SPECIFY_FEATURE_DIRECTORY", "")


def get_generated_dir() -> str:
    """获取 GENERATED_DIR 环境变量，默认 'generated'"""
    return os.environ.get("GENERATED_DIR", "generated")


def get_unified_reference_files(feature_dir: str) -> list[str]:
    """获取统一参考文件列表（相对于 generated/ 的路径）

    约定所有 task 的参考文件统一为:
        plan.md, contracts/*, research.md, data-model.md, spec.md
    """
    specs_dir = Path(get_generated_dir()) / "specs" / feature_dir
    if not specs_dir.exists():
        return []

    ref_files = []
    # 顶层固定文档
    for name in ["plan.md", "research.md", "data-model.md", "spec.md"]:
        f = specs_dir / name
        if f.exists():
            ref_files.append(str(f.relative_to(get_generated_dir())))

    # contracts 目录下所有文件
    contracts_dir = specs_dir / "contracts"
    if contracts_dir.is_dir():
        for f in sorted(contracts_dir.iterdir()):
            if f.is_file():
                ref_files.append(str(f.relative_to(get_generated_dir())))

    return ref_files


def make_completed_task() -> Task:
    """构造一个表示已完成的空任务"""
    return Task(status="completed")
