"""把制作方案转成手动交接任务，并预留代码模型配置。"""

from typing import Optional

CODE_MODEL = {  # 这里只保存环境变量名称；当前不请求 Opus。
    "provider": "manual",
    "model_name": None,
    "base_url": None,
    "api_key_env": "OPUS_API_KEY",
    "protocol": None,
}


class ManualCodeRequester:
    """保留代码生成接口；当前实现仅导出人工可用的提示词。"""

    def __init__(self, config: Optional[dict] = None):
        self.config = CODE_MODEL.copy() if config is None else config.copy()

    def request(self, brief: str, plan: str) -> dict:
        if self.config["provider"] != "manual":
            raise NotImplementedError("该代码模型适配器尚未实现，请保持 provider=manual。")
        prompt = f"""请按照以下需求与方案编写动画或视频项目代码。

原始需求：
{brief}

制作方案：
{plan}

交付要求：
1. 遵循方案的技术路线；必要条件未明确时先询问。
2. 提供文件结构、逐文件完整代码、依赖与安装步骤、预览和导出命令。
3. 统一场景时间轴，保证时长与画面比例符合要求。
4. 列明外部素材，缺少素材时说明需要补充的文件。
5. 提供关键画面的检查点；未运行时说明未验证。
"""
        return {"status": "waiting_for_code", "prompt": prompt, "code_files": [], "model_config": self.config.copy()}
