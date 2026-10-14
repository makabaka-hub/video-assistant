"""本地项目文件、代码版本与状态的持久化。"""

import json
import shutil
from pathlib import Path
from uuid import uuid4


class ProjectStore:
    """将每个制作任务保存在独立目录。"""

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir

    @staticmethod
    def _write_state(project_dir: Path, state: dict) -> None:
        (project_dir / "project.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, brief: str, plan: str, task: dict, planning_mode: str) -> Path:
        project_dir = self.projects_dir / f"project-{uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=False)
        for name, content in {"plan.md": plan, "code_request.md": task["prompt"]}.items():
            (project_dir / name).write_text(content, encoding="utf-8")
        self._write_state(project_dir, {"brief": brief, "planning_mode": planning_mode, **task})
        return project_dir

    def import_code(self, project_dir: Path, source: Path) -> Path:
        project_dir = project_dir.resolve()
        if not project_dir.is_relative_to(self.projects_dir.resolve()):
            raise ValueError("--project 必须是当前程序 projects 文件夹内的项目。")
        state = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
        source = source.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in {".html", ".css", ".js", ".ts", ".jsx", ".tsx", ".py", ".json"}:
            raise ValueError("请提供 html/css/js/ts/jsx/tsx/py/json 代码文件。")
        target = project_dir / "code" / f"version-{uuid4().hex[:12]}" / source.name
        target.parent.mkdir(parents=True, exist_ok=False)
        shutil.copy2(source, target)
        state["code_files"].append(target.relative_to(project_dir).as_posix())
        state["status"] = "code_imported"
        self._write_state(project_dir, state)
        return target
