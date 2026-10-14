# 从你的 DeepSeek 代码改成视频制作助手

这个版本完成“需求输入 → DeepSeek 制作策划 → 导出代码生成提示词 → 手动导入代码”的交接流程。Opus 接口为手动模式，不需要 Opus 会员或密钥；目前尚未实现自动生成代码、MCP 工具循环、渲染或视觉检查。

## 和原代码相比改了什么

| 原来的写法 | 当前写法 | 原因 |
|---|---|---|
| 源码里设置 OPENAI_API_KEY | 本机 .env 中填写 DEEPSEEK_API_KEY | 真实密钥与源码分开；公开过的旧密钥仍需要撤销 |
| OpenAI() 隐式读取设置 | OpenAI(api_key=..., base_url=...) | 明确说明当前请求 DeepSeek，不把其他模型的地址混在一起 |
| 固定写诗的人设和请求 | 视频策划提示词 + input 输入需求 | 让模型生成分镜、时间轴、素材需求和检查标准 |
| temperature=2 | temperature=0.4，并关闭思考模式 | 方案表达相对稳定；思考模式下温度无效 |
| 调用结束直接 print | 保存 plan.md、code_request.md 和 project.json | 下一步可以让 MCP 工具读取任务和状态 |
| 只有一个模型调用位置 | plan_video 与 request_video_code 分开 | DeepSeek 策划与未来 Opus 写代码分别接入 |

现在按功能拆分代码：根目录 `video_assistant.py` 只组装模块；`video_assistant_app/services/` 负责策划、代码交接和流程事件；`video_assistant_app/storage/` 保存项目与代码版本；`video_assistant_app/ui/` 负责命令行输入、订阅和显示。每个功能目录有自己的简短 README，Python 文件顶部有用途说明。

命令行界面只通过 `VideoService` 调用业务能力，并订阅 `project_created`、`code_imported` 事件显示结果。当前是进程内事件订阅；项目还没有网页前端或网络推送。功能和运行命令保持一致：仍支持 DeepSeek 策划、离线导出、项目保存、手动导入和版本保留。两段提示词、模型调用参数和输出文件格式保持原样。

## 安装

需要 Python 3.10 或更高版本（与锁定的依赖要求一致）。进入本项目目录后执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

打开 .env，只填写自己重新生成的 DEEPSEEK_API_KEY。DEEPSEEK_MODEL 默认是 deepseek-flash，OPUS_API_KEY 当前保持为空。

Windows 可以用 py -m venv .venv，再使用 .venv\Scripts\python.exe 安装依赖和运行脚本。

## 运行

```bash
python video_assistant.py
```

示例输入：

```text
用 HTML/Canvas 制作一个 20 秒的冒泡排序动画，16:9，面向编程初学者。用柱状图表现数字，每次比较时高亮两个柱子，交换时有移动动画，结尾总结规则。
```

程序将通过 DeepSeek 返回制作方案，并建立独立的 projects/project-... 文件夹。其中有：

- plan.md：制作方案。
- code_request.md：可交给代码模型或人工开发者的生成任务。
- project.json：原始需求、策划模式、代码模型预留配置、当前状态。

你暂时没有任何模型凭据时，可以运行：

```bash
python video_assistant.py --offline
```

离线模式仅基于原始需求导出提示词，不会声称已由模型完成分镜策划。它也不调用 DeepSeek。

## 手动导入已有代码

取得一个 HTML、Python、TSX 等代码文件后运行：

```bash
python video_assistant.py --project "/你的项目目录/projects/project-实际编号" --import-code "/你的代码路径/animation.html"
```

代码会存到项目的 code/version-... 子文件夹，每次导入都保留一个新版本。它只复制文件，状态变为 code_imported，不执行或渲染源码。

目前这是单文件导入入口，适合 HTML 或单个 Manim 脚本；多文件 Remotion 工程导入以及环境检查需要在选择渲染技术后另行实现。

## Opus 接口怎样预留

`video_assistant_app/services/code_request.py` 中的 CODE_MODEL 定义了 provider、model_name、base_url、api_key_env 和 protocol。当前 provider=manual。`ManualCodeRequester.request` 的输入是原始需求和制作方案，输出是包含 status、prompt、code_files 等字段的任务字典。

后续接入时实现对应适配器，使它接收同样的输入，再返回真实代码或明确的等待/失败状态。官方服务与中转服务按照实际协议分别处理。

**现在仅修改 provider 或填写地址不会实现自动调用。** 未实现的适配器会明确报错，避免你以为已经接上 Opus。项目文件只保存环境变量名，不保存真实密钥。

## 验证范围

运行 `python verify.py` 可复现 12 项离线检查。本版本使用模拟模型响应和临时目录检查调用参数、事件推送、结果保存、导入状态、版本保留、空结果拒绝与未实现适配器拒绝；另行运行真实命令检查离线任务导出、手动代码导入、参数搭配错误和空需求。没有实际调用 DeepSeek 或 Opus API。

## 文档依据

- [OpenAI Python SDK](https://developers.openai.com/api/reference/python)：客户端、环境配置和 Chat Completions。
- [DeepSeek 官方调用示例](https://api-docs.deepseek.com/)：兼容接口、base_url 与模型名。
- [DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)：extra_body 模式开关及温度参数行为。
