# 业务服务

`planning.py` 调用 DeepSeek 并检查结果；`code_request.py` 导出手动代码生成任务并预留 Opus 配置；`workflow.py` 编排流程，向订阅者推送项目创建和代码导入事件。这里不读取命令行输入，也不打印界面文字。
