import os
import json
import shutil
from pathlib import Path
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# 统一获取环境变量，并定义项目的真正根目录
GENERATED_DIR = os.environ.get("GENERATED_DIR", "generated")
# 动态获取当前文件所在的根目录
PROJECT_ROOT = Path.cwd().resolve()

@tool
def setup_spec_environment(feature_name: str) -> str:
    """
    根据传入的 feature_name 初始化规范目录环境，初始化 spec.md文件
    并设置相应的环境变量。

    Args:
        feature_name (str): 外部生成的规范目录名（例如 "001-add-user-auth" 或 "user-auth"）。

    Returns:
        str: summary result
    """
    try:
        # 清洗文件名，防止外部传入带有路径穿越符号（如 ../）的安全隐患
        safe_feature_name = Path(feature_name).name

        base_path = Path(GENERATED_DIR).resolve()
        specs_dir = base_path / "specs"
        specs_dir.mkdir(exist_ok=True, parents=True)

        # 1. 直接使用外部传入的名称作为功能目录名
        feature_directory = specs_dir / safe_feature_name
        feature_directory.mkdir(parents=True, exist_ok=True)
        (feature_directory / "checklists").mkdir(exist_ok=True)
        
        # 更新环境变量：仅记录该功能的文件夹名称
        os.environ["SPECIFY_FEATURE_DIRECTORY"] = safe_feature_name

        # 2. 初始化 spec.md 模板
        template_path = PROJECT_ROOT / ".specify" / "spec-template.md"
        spec_file = feature_directory / "spec.md"

        if template_path.exists():
            shutil.copy(template_path, spec_file)
        else:
            # 如果找不到模板，生成一个标准的 Markdown 规范兜底结构
            spec_file.write_text(
                f"# Feature Spec: {safe_feature_name}\n\n## User Scenarios\n\n## Functional Requirements\n\n## Success Criteria\n", 
                encoding="utf-8"
            )

        # 3. 计算用于后续工具对接的相对路径（相对于 GENERATED_DIR/ 目录）
        relative_spec_path = f"specs/{safe_feature_name}/spec.md"
        os.environ["SPEC_FILE"] = relative_spec_path

        result = {
            "status": "success",
            "feature_directory_name": safe_feature_name,
            "spec_file_path": relative_spec_path,  # 精准传递相对路径给后续的写入工具
            "absolute_path_debug": str(spec_file.resolve()),
            "message": f"Successfully initialized environment for feature directory: '{safe_feature_name}'"
        }

        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"环境初始化失败: {str(e)}"}, ensure_ascii=False)
