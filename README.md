# apopy: Simple Apollo Config Client for Python.

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
