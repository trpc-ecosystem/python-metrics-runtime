English | [中文](README.zh_CN.md)

# tRPC-Metrics-Runtime

`trpc-metrics-runtime` is the runtime version reporter for tRPC-Python. Importing it registers `RuntimeMetrics`, which reports the framework version and the version of every plugin marked `report=True`. The first report is sent 3 seconds after a worker starts, and later reports go out every 24 hours.

## Features

- **Automatic reporting**:
    - **Register on import**: importing `trpc_metrics_runtime` in the business process registers the plugin;
    - **Framework and plugins**: reports the tRPC framework version and the version of every plugin registered with `report=True`;
    - **Fixed schedule**: the first report is sent 3 seconds after the worker starts, then once every 24 hours;
- **Process model**:
    - **One reporter thread**: workers share one flag. The first worker to start launches a daemon thread named `runtime-metrics-reporter`, so the whole process tree reports once in every process and thread model. See "Process and thread models";
    - **Process exit**: the thread is a daemon, so process exit does not wait for the next 24-hour sleep to finish;
- **Report path and identity**:
    - **One host**: reports go to `stat.trpc.tencent.com`. A non-200 response is logged as a warning. A connection error logs one info line, closes the current client, and retries with a new client on the next interval;
    - **Process identity**: `app`, `server`, `ip`, and `container` come from the tRPC config first. Missing values, or an address that cannot be reported, are filled from container environment variables or local NICs. This plugin has no `plugins.metrics` section. Importing it is enough to register it.

## Installation

### Requirements

Python: 3.8+

Runtime dependencies: `trpc-python`, `aiohttp`, and `netifaces`.


### Install

Install with `pip`:

```bash
pip install trpc-metrics-runtime
```

## Quick start

This assumes a tRPC project already exists. This repository includes a runnable example. The main files are:

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

#### 1. Import the plugin

Importing registers `RuntimeMetrics`, and it must happen before the service is created. See [examples/trpc_main.py](./examples/trpc_main.py):

```python
# Importing registers the plugin, so keep this first.
import trpc_metrics_runtime as _
```

After import, the framework version is reported, along with every plugin that carries `report=True`. This plugin registers itself with `report=True`, so its package version is included in the report.

#### 2. Mark plugins that should be reported

When registering a plugin with the `register_plugin` decorator, set `version` and `report=True`:

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
        """Initialize when the WORKER process starts."""
        pass
```

Only plugins with `report` set to `True` are included. `version` is that plugin's own version, separate from the tRPC framework version.

#### 3. Configuration

This plugin has no `plugins.metrics` section. Process identity is read from `server.app` and `server.server` in the tRPC config, and from `local_ip` and `container_name` in the global config. See [examples/trpc_python.yaml](./examples/trpc_python.yaml):

```yaml
global: # Global configuration.
  namespace: Development # Environment type: production or development.
  env_name: test # Environment name used when namespace is not production.

server: # Server configuration.
  app: test # app field in the report payload
  server: Greeter # server field in the report payload
```

In the example, `app` is `test` and `server` is `Greeter`. When the configured address cannot be reported, the plugin fills `ip` and `container` using the rules in "What is reported" below.

#### 4. Start the service

```sh
python3 examples/trpc_main.py
```

[examples/README.md](./examples/README.md) describes the example. `./examples/run_examples.sh` starts the server, sends one SayHello, and stops the server.

About 3 seconds after the service starts, the first version report is sent, then once every 24 hours. A non-200 response is logged as a warning. A connection error logs one info line and closes the current HTTP client. The next round uses a new client.

## Process and thread models

`RuntimeMetrics` is a `WORKER` plugin, so `start()` runs in every process that runs service handlers. The tRPC worker calls it after forking its children and after creating its event loop, so the reporter thread is never alive across a fork. The flag those processes share is a `multiprocessing.Value` created when the package is imported, and the server forks every child, so the first `start()` to claim the flag launches the only reporter thread in the process tree. That process logs `runtime metrics reporter started in pid <pid>`.

Where the reporter runs, by `global.processmodel`:

- **merge, single loop** (the default, no `processmodel`): in the server process.
- **merge, serving threads** (`single_process` with `handle_num > 1`, or `io_handle_type: separate`): in the server process. Plugins are started once, on the main thread, not once per serving or handler thread.
- **separate** (`multi_process`, `io_handle_type: separate`): in one rpc task process. The I/O process only starts `TASK` plugins and never runs the reporter. Which rpc task wins the flag is not fixed.
- **multi-process merge** (`multi_process`, `io_handle_type: merge`): in one worker process. Which worker wins the flag is not fixed.
- **task processes**: never. They only start `TASK` plugins.

The payload is the same in every model; only the pid that sends it differs. Example configs for each model, all serving `127.0.0.1:8000`:

| Config | Model |
| --- | --- |
| [trpc_python.yaml](./examples/trpc_python.yaml) | merge, single loop |
| [trpc_python_merge_threads.yaml](./examples/trpc_python_merge_threads.yaml) | merge, two serving threads |
| [trpc_python_separate_thread.yaml](./examples/trpc_python_separate_thread.yaml) | merge, one I/O thread and two handler threads |
| [trpc_python_separate.yaml](./examples/trpc_python_separate.yaml) | separate, two rpc tasks |
| [trpc_python_merge_processes.yaml](./examples/trpc_python_merge_processes.yaml) | multi-process merge, two workers |

```sh
python3 examples/trpc_main.py --conf examples/trpc_python_separate.yaml
```

## What is reported

Each report is one JSON body, posted to `api/trpc/stat/v3/add`:

```json
{
  "lang": "python",
  "version": "framework version",
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

- `version` is the tRPC framework version from `trpc_sdk`. It is not this package's `__version__`.
- `plugins` is a list of `{plugin name: plugin version}` objects. Only plugins with `report=True` are included, including the `runtime` plugin registered by this package.
- Each request goes to `http://stat.trpc.tencent.com/api/trpc/stat/v3/add`. A non-200 response is logged as a warning. A connection failure logs one info line, closes the client, and retries with a new client on the next interval.
- When the stat service returns 403 because the report was already sent or the daily cap was reached, and the body contains `已上报` or `上报次数限制`, that attempt is treated as success.

A reportable address is one accepted by `is_ip_valid`: it parses, and it is not unspecified (`0.0.0.0`, `::`), loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), `172.16.0.0/12`, or `192.168.0.0/16`, and it is not IPv6 `FC00::/7` or `FEC0::/10`. `10.0.0.0/8` can be reported. Whether the process is inside a container is decided only by the presence of `/.dockerenv`.

How `ip` and `container` are filled:

- When `global.local_ip` is a reportable address, it is used as `ip`.
- Inside a container, if the configured address cannot be used, `ip` is the `NODE_IP` environment variable, and that value must be reportable. Without a usable `NODE_IP`, `ip` is empty. A container bridge address is not used instead. When `global.container_name` is empty, `container` prefers `CLUSTER_ID/POD_NAMESPACE/POD_NAME`, joined only when all three variables are set. Otherwise the container id falls back to an address from config or a local NIC.
- Outside a container, `container` is empty. When the configured address cannot be used, `ip` tries the service listen address, the address of the named NIC, and then local NIC addresses.

## Development setup

```bash
# Install this package and the test dependencies
pip install -e .
pip install -r requirements-test.txt

# Run tests
pytest

# Format the code
./format.sh
```


## License

This project is licensed under Apache-2.0.
