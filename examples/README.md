# tRPC-Metrics-Runtime 示例

本示例起一个 Greeter 服务，并在创建服务之前导入 `trpc_metrics_runtime`。导入会注册运行时版本上报插件。服务监听 `127.0.0.1:8000`。`SayHello` 把请求里的 `msg` 加上 `hello: ` 前缀后返回。

## 关键特性

- **导入即注册**：`trpc_main.py` 在 `create_server` 之前执行 `import trpc_metrics_runtime`
- **一次调用**：`test_service_rpc.py` 默认打一次 `SayHello` 后退出。加上 `--loop` 会一直发送异步请求
- **五种进程/线程模式**：同一套服务配五份 YAML，用来看上报线程落在哪个进程

关键文件：

- [trpc_main.py](trpc_main.py)：导入插件、加载配置、注册 Greeter，然后 `serve`
- [greeter.py](greeter.py)：`SayHello` 返回 `hello: ` 加上请求内容
- [test_service_rpc.py](test_service_rpc.py)：客户端。默认一次同步调用；`--loop` 保持异步循环
- [test_greeter.py](test_greeter.py)：转调 `test_service_rpc.main`
- [run_examples.sh](run_examples.sh)：起服务、等 8000、跑客户端、检查上报线程日志、停服务
- [stub/](stub/)：helloworld 桩代码
- `trpc_python*.yaml`：每种模式一份，都听 `127.0.0.1:8000`

调用关系：

```text
test_service_rpc.py
└── Greeter.SayHello  127.0.0.1:8000
    └── 回复 msg = "hello: " + request.msg

trpc_main.py
└── import trpc_metrics_runtime
    └── RuntimeMetrics.start
        └── runtime metrics reporter started in pid <pid>
```

## 环境要求

- Python >= 3.8
- macOS 或 Linux
- 本机 8000 空闲
- 依赖：`trpc-python`、`aiohttp`、`netifaces`。在仓库根目录执行 `uv sync` 或 `pip install -e .`

上报发往 `stat.trpc.tencent.com`。域名连不上时，服务日志里会有一条 info 级别的失败记录。脚本检查的是 `runtime metrics reporter started in pid`。这行在 worker 的 `start()` 里打出，出现在第一次 HTTP 上报之前。

## 运行步骤

在 `examples` 目录下：

```bash
./run_examples.sh list
./run_examples.sh
./run_examples.sh service
./run_examples.sh service trpc_python_merge_processes.yaml
./run_examples.sh modes
```

`./run_examples.sh` 和 `service` 一样，用 [trpc_python.yaml](trpc_python.yaml)。`service` 后面可以换成本目录里的另一份 YAML，或一个绝对路径。`modes` 按下面表格的顺序各跑一遍。

解释器按 `$PYTHON`、`../.venv/bin/python`、`../venv/bin/python`、`python3` 的顺序选。服务日志写在 `examples/.server_run.log`。上一级目录里有 `trpc_sdk` 包时，脚本把它的父目录放在 `PYTHONPATH` 前面。

手动两步：

```bash
# 终端 1，当前目录是 examples
python trpc_main.py -c trpc_python.yaml

# 终端 2
python test_service_rpc.py
python test_service_rpc.py --loop
```

| 配置 | 模型 |
| --- | --- |
| `trpc_python.yaml` | merge，一个事件循环 |
| `trpc_python_merge_threads.yaml` | merge，两个 serving 线程 |
| `trpc_python_separate_thread.yaml` | merge，一个 I/O 线程和两个 handler 线程 |
| `trpc_python_separate.yaml` | separate，两个 rpc task |
| `trpc_python_merge_processes.yaml` | multi-process merge，两个 worker |

## 运行结果

`./run_examples.sh` 对每一项打印 `[PASS]` 或 `[FAIL]`。

客户端成功时打印类似下面的内容，并以状态码 0 退出：

```text
test_sync_Greeter_SayHello recv result is msg: "hello: hello"
```

服务日志里有：

```text
runtime metrics reporter started in pid <pid>
```

整棵进程树里只有一个进程打出这行。separate 和 multi-process merge 模式下，打出这行的 pid 不固定。

## 适用场景

- 确认插件在 `create_server` 前导入后，Greeter 能返回 `hello: hello`
- 换 YAML 之后确认上报线程仍然只启动一次

## 需要注意什么

1. **先导入插件**。`import trpc_metrics_runtime` 要在 `create_server` 之前。
2. **端口**。五份配置都听 `8000`。一键脚本发现端口已被占用会直接失败。
3. **上报域名**。连不上 `stat.trpc.tencent.com` 时，info 日志仍然是正常现象。脚本只检查 reporter 启动日志。
4. **客户端默认打一次**。要一直发请求时用 `python test_service_rpc.py --loop`。
