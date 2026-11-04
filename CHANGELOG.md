# Change Log

## 1.0.0

- 导入 `trpc_metrics_runtime` 即注册运行时版本上报插件。
- 上报框架版本，以及标记了 `report=True` 的插件版本。worker 启动约 3 秒后第一次上报，之后每 24 小时一次。
