[English](README.md) | 中文

# tRPC-Metrics-Runtime

`tRPC-Metrics-Runtime` 是 tRPC-Python 的运行时版本上报插件。导入后注册 `RuntimeMetrics`，在服务进程中上报框架版本，以及所有标记 `report=True` 的插件版本。Worker 启动后等待 3 秒做第一次上报，之后每 24 小时再上报一次。

## 核心特性

- **自动上报**：
    - **导入即注册**：在业务进程中导入 `trpc_metrics_runtime` 即完成插件注册；
    - **框架与插件**：上报 tRPC 框架版本，以及注册时设置 `report=True` 的插件版本；
    - **固定节奏**：首次上报在 worker 启动 3 秒后发出，之后每隔 24 小时上报一次；
- **进程模型**：
    - **单线程上报**：多个 worker 共享一个标记，由最先启动的 worker 拉起名为 `runtime-metrics-reporter` 的 daemon 线程，任何进程/线程模式下整棵进程树都只上报一份，详见「进程/线程模式」；
    - **进程退出**：该线程为 daemon，进程退出时不等待下一次 24 小时休眠结束；
- **上报通道与身份**：
    - **单一域名**：请求发往 `stat.trpc.tencent.com`。返回非 200 时记一条 warning。连接异常时记一条 info 日志，关掉当前客户端，等下一个间隔再用新客户端重试；
    - **进程身份**：`app`、`server`、`ip`、`container` 优先取自 tRPC 配置，缺失或地址不可上报时再从容器环境变量或本机网卡补齐。本插件没有 `plugins.metrics` 配置段，导入即注册。

## 安装方式

### 环境要求

Python 版本: 3.8+

运行依赖：`trpc-python`、`aiohttp`、`netifaces`。


### 安装

使用 `pip` 安装：

```bash
pip install trpc-metrics-runtime
```

## 快速体验

这里假设用户已经生成 tRPC 项目。本仓库自带一份可运行示例，主要文件如下：

```txt
examples/
├── README.md
├── run_examples.sh
├── trpc_main.py
├── trpc_python.yaml
├── trpc_python_merge_threads.yaml
├── trpc_python_separate_thread.yaml
├── trpc_python_separate.yaml
├── trpc_python_merge_processes.yaml
├── greeter.py
├── test_greeter.py
└── test_service_rpc.py
```

#### 1. 导入插件

导入过程会注册 `RuntimeMetrics`，需要放在创建服务之前。参考 [examples/trpc_main.py](./examples/trpc_main.py)：

```python
# 导入过程属于注册插件，需要放在最前面
import trpc_metrics_runtime as _
```

导入后默认上报框架版本，以及所有携带 `report=True` 的插件版本。本插件自身以 `report=True` 注册，包版本会一并出现在上报列表中。

#### 2. 标记需要上报的插件

插件注册时（使用 `register_plugin` 装饰器声明插件时）设置 `version` 和 `report=True`：

```python
from trpc_sdk.abc import BasePlugin
from trpc_sdk.abc import PluginInitPos
from trpc_sdk.abc import PluginType
from trpc_sdk.plugin import register_plugin

PLUGIN_NAME = "my_plugin"
version = "0.1.0"


@register_plugin(PluginType.METRICS, PLUGIN_NAME, init_pos=PluginInitPos.WORKER, version=version, report=True)
class MyPlugin(BasePlugin):

    def start(self):
        """在 WORKER 进程启动时进行初始化"""
        pass
```

`report` 为 `True` 的插件才会进入本次上报。`version` 使用插件自己的版本号，与 tRPC 框架版本分开。

#### 3. 配置文件

本插件没有 `plugins.metrics` 配置段。上报读取的进程身份来自 tRPC 配置里的 `server.app`、`server.server`，以及 global 配置中的 `local_ip`、`container_name`。参考 [examples/trpc_python.yaml](./examples/trpc_python.yaml)：

```yaml
global: # Global configuration.
  namespace: Development # Environment type: production or development.
  env_name: test # Environment name used when namespace is not production.

server: # Server configuration.
  app: test
  server: Greeter
```

示例里的 `app` 为 `test`，`server` 为 `Greeter`。配置中的地址不可用时，插件会按下面「上报说明」里的规则补齐 `ip` 和 `container`。

#### 4. 启动服务

```sh
python3 examples/trpc_main.py
```

示例说明见 [examples/README.md](./examples/README.md)。`./examples/run_examples.sh` 会启动服务、发送一次 SayHello，然后停掉服务。

服务起来约 3 秒后发出第一次版本上报，之后每 24 小时上报一次。返回非 200 时记一条 warning。连接异常时记一条 info 日志并关闭当前 HTTP 客户端，下一轮使用新的客户端。

## 进程/线程模式

`RuntimeMetrics` 是 `WORKER` 插件，`start()` 会在每个运行业务 handler 的进程里执行。tRPC worker 先 fork 子进程、再创建事件循环，最后才调用它，所以上报线程不会跨越 fork 存在。这些进程共用的标记是导入本包时创建的 `multiprocessing.Value`，子进程都由服务端 fork 出来，因此第一个抢到标记的 `start()` 会拉起整棵进程树里唯一的上报线程，并在该进程记一条 `runtime metrics reporter started in pid <pid>` 日志。

按 `global.processmodel` 区分，上报线程所在的位置：

- **merge 单循环**（默认，不配 `processmodel`）：服务进程。
- **merge 多线程**（`single_process` 且 `handle_num > 1`，或 `io_handle_type: separate`）：服务进程。插件只在主线程启动一次，不会每个服务线程或 handler 线程各启动一次。
- **separate**（`multi_process`，`io_handle_type: separate`）：某一个 rpc task 进程。I/O 进程只启动 `TASK` 插件，不运行上报线程。具体落在哪个 rpc task 不固定。
- **multi-process merge**（`multi_process`，`io_handle_type: merge`）：某一个 worker 进程。具体落在哪个 worker 不固定。
- **task 进程**：不上报，只启动 `TASK` 插件。

各模式的上报内容相同，只是发出上报的 pid 不同。每种模式都有示例配置，均监听 `127.0.0.1:8000`：

| 配置 | 模式 |
| --- | --- |
| [trpc_python.yaml](./examples/trpc_python.yaml) | merge 单循环 |
| [trpc_python_merge_threads.yaml](./examples/trpc_python_merge_threads.yaml) | merge，两个服务线程 |
| [trpc_python_separate_thread.yaml](./examples/trpc_python_separate_thread.yaml) | merge，一个 I/O 线程加两个 handler 线程 |
| [trpc_python_separate.yaml](./examples/trpc_python_separate.yaml) | separate，两个 rpc task |
| [trpc_python_merge_processes.yaml](./examples/trpc_python_merge_processes.yaml) | multi-process merge，两个 worker |

```sh
python3 examples/trpc_main.py --conf examples/trpc_python_separate.yaml
```

## 上报说明

每次上报是一条 JSON，发往 `api/trpc/stat/v3/add`：

```json
{
  "lang": "python",
  "version": "框架版本",
  "app": "test",
  "server": "Greeter",
  "ip": "10.0.0.1",
  "container": "",
  "plugins": [
    {"runtime": "0.1.0"},
    {"my_plugin": "0.1.0"}
  ]
}
```

- `version` 是 tRPC 框架版本，来自 `trpc_sdk`，与本包的 `__version__` 不同。
- `plugins` 是一组 `{插件名: 插件版本}`。列表里只包含 `report=True` 的插件，其中包含本包注册的 `runtime`。
- 请求发往 `http://stat.trpc.tencent.com/api/trpc/stat/v3/add`。返回的 HTTP 状态不是 200 时记一条 warning。连接失败等异常时，上报循环会记一条 info 日志、关掉客户端，等下一个间隔再用新客户端重试。
- 统计服务对已上报或达到当日上限返回 403，且响应正文包含「已上报」或「上报次数限制」时，本次按成功处理。

可上报地址由 `is_ip_valid` 判断：能被解析，且不是未指定地址（`0.0.0.0`、`::`）、回环（`127.0.0.0/8`、`::1`）、链路本地（`169.254.0.0/16`、`fe80::/10`）、`172.16.0.0/12`、`192.168.0.0/16`，也不是 IPv6 的 `FC00::/7`、`FEC0::/10`。`10.0.0.0/8` 可以上报。是否在容器内只看根目录是否存在 `/.dockerenv`。

`ip` 与 `container` 的补齐规则：

- `global.local_ip` 是可上报地址时，直接作为 `ip`。
- 进程在容器内且配置中的地址不可用时，`ip` 取环境变量 `NODE_IP`（需为可上报地址）。没有可用的 `NODE_IP` 时 `ip` 为空，不会改用容器网桥地址。`container` 在 `global.container_name` 为空时，优先使用 `CLUSTER_ID/POD_NAMESPACE/POD_NAME`，三项环境变量都存在时才拼接；否则使用配置或本机网卡上的地址作为容器标识。
- 进程在容器外时，`container` 为空。配置中的地址不可用时，`ip` 依次尝试服务监听地址、网卡名对应地址，以及本机网卡地址。


## 许可证

本项目采用 Apache-2.0 许可证。
