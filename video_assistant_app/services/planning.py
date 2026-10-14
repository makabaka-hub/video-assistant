"""用 DeepSeek 将视频需求整理成制作方案。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """你是玛卡巴卡视频制作策划助手，帮助用户用代码生成动画或视频。
根据需求输出 Markdown 制作方案，包含：主题与受众、时长与比例、技术路线、
逐场景时间轴、画面内容、屏幕文字、动画与转场、素材清单和检查标准。
保持总时长与场景时长一致；未明确的信息标为待确认。
遵循用户明确指定的技术路线；没有指定时提出一个推荐并解释理由。
当前 Opus 尚未接入，方案用于导出代码生成提示词。
不能声称已经生成代码、渲染视频或观看了画面。
玛卡巴卡是助手人设，不要擅自将人设或开场语写进视频内容。
"""


class DeepSeekPlanner:
    """从本地配置取得密钥，并调用 DeepSeek 策划模型。"""

    def __init__(self, root: Path, client_factory=None):
        self.root = root
        self.client_factory = client_factory or OpenAI

    def plan(self, brief: str) -> str:
        load_dotenv(self.root / ".env", override=False)  # 已有环境变量优先。
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("请在 .env 填写新 DEEPSEEK_API_KEY；暂不调用模型可使用 --offline。")
        with self.client_factory(api_key=api_key, base_url="https://api.deepseek.com", timeout=60.0, max_retries=1) as client:
            completion = client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL") or "deepseek-flash",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": brief},
                ],
                temperature=0.4,
                max_tokens=3000,
                extra_body={"thinking": {"type": "disabled"}},
            )
        if not completion.choices or completion.choices[0].finish_reason != "stop":
            raise ValueError("模型未完整返回方案，请缩小任务后重试。")
        plan = (completion.choices[0].message.content or "").strip()
        if not plan:
            raise ValueError("模型返回了空方案，请重试。")
        return plan
