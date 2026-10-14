"""程序入口：组装策划、代码交接、项目存储与命令行界面。"""

from pathlib import Path

from video_assistant_app.services.code_request import ManualCodeRequester
from video_assistant_app.services.planning import DeepSeekPlanner
from video_assistant_app.services.workflow import VideoService
from video_assistant_app.storage.projects import ProjectStore
from video_assistant_app.ui.cli import run


def main() -> None:
    root = Path(__file__).resolve().parent
    service = VideoService(
        planner=DeepSeekPlanner(root),
        code_requester=ManualCodeRequester(),
        projects=ProjectStore(root / "projects"),
    )
    run(service)


if __name__ == "__main__":
    main()
