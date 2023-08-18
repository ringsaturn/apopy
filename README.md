# apopy: Simple Apollo Config Client for Python. [![PyPI](https://img.shields.io/pypi/v/apopy)](https://pypi.org/project/apopy/) [![CI](https://github.com/ringsaturn/apopy/actions/workflows/ci.yaml/badge.svg)](https://github.com/ringsaturn/apopy/actions/workflows/ci.yaml) [![publish](https://github.com/ringsaturn/apopy/actions/workflows/deploy.yaml/badge.svg)](https://github.com/ringsaturn/apopy/actions/workflows/deploy.yaml)

```bash
pip install apopy
```

## Quick Start

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

Apopy 没有提供内置的配置轮训更新功能，但是可以通过以下方式实现：


```python
def start_background_update(client: Client):
    import threading

    def _update():
        while True:
            try:
                client.update()
            except Exception:
                pass
            finally:
                time.sleep(3)

    t = threading.Thread(target=_update)
    t.start()


start_background_update(client)
```
