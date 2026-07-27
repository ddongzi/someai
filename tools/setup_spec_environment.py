import subprocess
import logging
import os
import sys
from dotenv import load_dotenv
from enum import Enum
from langchain.tools import tool
from typing import Optional
from globals.logger import run_logger
load_dotenv()
import os
import json
import re
import shutil
from pathlib import Path
from langchain_core.tools import tool

@tool
def setup_spec_environment(feature_description: str) -> str:
    """
    Initializes the feature spec directory, creates spec.md from template, 
    and returns absolute paths for the feature folder and spec file.
    Use this tool at the very beginning when creating a new feature specification.

    Args:
        feature_description: The raw natural language user prompt describing the feature.
    """
    project_root = Path.cwd()
    specs_dir = project_root / "specs"
    specs_dir.mkdir(exist_ok=True)

    # 1. 提取短名称 (Slug)
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', feature_description.lower())
    words = clean_text.split()[:4]
    short_name = "-".join(words) if words else "new-feature"

    # 2. 递增获取序号 (001, 002...)
    existing_nums = []
    for item in specs_dir.iterdir():
        if item.is_dir():
            match = re.match(r'^(\d{3})-', item.name)
            if match:
                existing_nums.append(int(match.group(1)))

    next_num = max(existing_nums, default=0) + 1
    prefix = f"{next_num:03d}"

    # 3. 创建目录结构
    feature_directory = specs_dir / f"{prefix}-{short_name}"
    feature_directory.mkdir(parents=True, exist_ok=True)
    (feature_directory / "checklists").mkdir(exist_ok=True)

    # 4. 初始化 spec.md
    template_path = project_root / ".specify" / "spec-template.md"
    spec_file = feature_directory / "spec.md"

    if template_path.exists():
        shutil.copy(template_path, spec_file)
    else:
        spec_file.write_text(
            f"# Feature Spec: {short_name}\n\n## User Scenarios\n\n## Functional Requirements\n\n## Success Criteria\n", 
            encoding="utf-8"
        )

    # 5. 返回结构化上下文信息
    result = {
        "status": "success",
        "feature_directory": str(feature_directory.resolve()),
        "spec_file_path": str(spec_file.resolve()),
        "message": f"Initialized environment for '{short_name}' at {feature_directory.name}"
    }

    return json.dumps(result, ensure_ascii=False)