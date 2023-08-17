# apopy: Simple Apollo Config Client for Python.

```python
from apopy import Client

client = Client(
    config_server_url="http://81.68.181.139:8080",  # http://81.68.181.139/system_info.html
    app_id="apollo-common",
    cluster_name="default",
    secret="5fdc723621054e0f945cb441561687eb",
    ip="192.168.1.4",
)
print(client.get("test"))
```
