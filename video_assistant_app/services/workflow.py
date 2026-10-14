"""编排后端流程，并向订阅者推送完成事件。"""

from pathlib import Path
from typing import Callable


class VideoService:
    """把模型、代码任务和项目存储连接起来。"""

    def __init__(self, planner, code_requester, projects):
        self.planner = planner
        self.code_requester = code_requester
        self.projects = projects
        self._subscribers: list[Callable[[str, dict], None]] = []

    def subscribe(self, callback: Callable[[str, dict], None]) -> None:
        self._subscribers.append(callback)

    def _publish(self, event: str, data: dict) -> None:
        for callback in tuple(self._subscribers):
            callback(event, data)

    def create_project(self, brief: str, offline: bool = False) -> Path:
        plan = (
            "离线需求初稿，尚未经过模型策划；请据此补充场景与技术细节。\n\n" + brief
            if offline else self.planner.plan(brief)
        )
        task = self.code_requester.request(brief, plan)
        project_dir = self.projects.create(brief, plan, task, "offline" if offline else "deepseek")
        self._publish("project_created", {"plan": plan, "project_dir": project_dir})
        return project_dir

    def import_code(self, project_dir: Path, source: Path) -> Path:
        target = self.projects.import_code(project_dir, source)
        self._publish("code_imported", {"target": target})
        return target
