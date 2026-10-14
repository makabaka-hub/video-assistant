"""命令行输入与展示：订阅后端事件，不实现业务逻辑。"""

import argparse
from pathlib import Path


def show_event(event: str, data: dict) -> None:
    """将服务事件显示给命令行用户。"""
    if event == "code_imported":
        print(f"玛卡巴卡来了！代码已导入：{data['target']}\n当前状态：code_imported，尚未运行或渲染。")
    elif event == "project_created":
        project_dir = data["project_dir"]
        print(f"\n玛卡巴卡来了！\n{data['plan']}\n\n项目已保存：{project_dir}\n代码生成提示词：{project_dir / 'code_request.md'}\n当前状态：waiting_for_code")


def run(service) -> None:
    """解析命令行选项，调用服务，并处理面向用户的错误显示。"""
    parser = argparse.ArgumentParser(description="DeepSeek 视频策划 + 手动代码交接")
    parser.add_argument("--offline", action="store_true", help="不调用模型，仅导出基于原始需求的提示词")
    parser.add_argument("--project", type=Path, help="已有项目目录")
    parser.add_argument("--import-code", type=Path, help="手动获得的代码文件")
    args = parser.parse_args()
    service.subscribe(show_event)
    try:
        if bool(args.project) != bool(args.import_code):
            raise ValueError("导入代码时请同时提供 --project 和 --import-code。")
        if args.import_code:
            service.import_code(args.project, args.import_code)
            return
        brief = input("请输入视频需求（主题、时长、比例、技术路线）：\n").strip()
        if not brief:
            raise ValueError("视频需求不能为空。")
        service.create_project(brief, offline=args.offline)
    except Exception as error:
        # API 异常只显示类型，避免输出可能包含敏感信息的请求正文。
        print(str(error) if isinstance(error, (ValueError, NotImplementedError)) else f"操作未完成（{type(error).__name__}），请检查配置、网络或文件。")
        raise SystemExit(1)
