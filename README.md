# apopy: Simple Apollo Config Client for Python. [![PyPI](https://img.shields.io/pypi/v/apopy)](https://pypi.org/project/apopy/)

```bash
pip install apopy
```

## Quick Start

> **NOTE**
>
> - 示例里的配置信息仅供测试使用，请勿用于生产环境。
> - 具体的配置可能会变动，仅用于说明使用方法，具体的访问方式见
  > <https://www.apolloconfig.com/#/zh/README>

```python
from apopy import Client, NamespaceType

client = Client(
    config_server_url="http://81.68.181.139:8080",
    app_id="apollo-common",
    cluster_name="default",
    secret="5fdc723621054e0f945cb441561687eb",
    ip="192.168.1.4",
)

# 读取 Namespace 为 application 的配置（接口带缓存）
print(client.read_namespace_with_cache(namespace="application"))

# 读取 Namespace 为 application 的配置（接口无缓存）
print(
    client.read_namespace_without_cache(
        namespace="application", namespace_type=NamespaceType.PROPERTIES
    )
)

# 读取配置
print(client.get("test"))
```

### 配置轮训更新

Apopy 提供了内置的针对单独 namespace 配置轮训更新功能，可以通过以下方式实现：

> **WARNING**
>
> Apopy 本身并没有配置单独的线程锁/进程锁，如果真的需要异步订阅更新，
> 请根据自己的需求在外层加上锁保护。

```python
import time
import threading


def start_background_update(client: Client):

    def _update():
        while True:
            try:
                client.read_notification_and_update(
                    namespace="application", namespace_type=NamespaceType.PROPERTIES
                )
            except Exception:
                pass
            finally:
                time.sleep(3)

    t = threading.Thread(target=_update)
    t.start()


start_background_update(client)
while True:
    print(client.read_namespace_with_cache(namespace="application"))
    time.sleep(5)
```
