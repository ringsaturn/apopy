# OAPY: Simple Apollo Config Client for Python.

```python
from oapy import Client

client = Client(
    config_server_url="http://81.68.181.139:8080",
    app_id="apollo-common",
    cluster_name="default",
    secret="5fdc723621054e0f945cb441561687eb",
    ip="192.168.1.4",
)
print(client.get("test"))
```
