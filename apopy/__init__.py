import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

import httpx


def signature(timestamp, uri, secret):
    # Refer: https://github.com/xhrg-product/apollo-client-python/blob/1.0.1/apollo/util.py#L25-L31
    string_to_sign = "" + timestamp + "\n" + uri
    hmac_code = hmac.new(
        secret.encode(), string_to_sign.encode(), hashlib.sha1
    ).digest()
    return base64.b64encode(hmac_code).decode()


Configurations = Dict[str, str]


@dataclass
class ReadConfigWithoutCache:
    appId: str
    cluster: str
    namespaceName: str
    configurations: Configurations
    releaseKey: str


class NamespaceType(Enum):
    PROPERTIES: str = "properties"
    XML: str = "xml"
    JSON: str = "json"
    YML: str = "yml"
    YAML: str = "yaml"
    TXT: str = "txt"


class Client(object):
    def __init__(
        self,
        config_server_url: str,
        app_id: str,
        cluster_name: str,
        ip: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: int = 60,
    ):
        self.config_server_url = config_server_url
        self.app_id = app_id
        self.cluster_name = cluster_name
        self.timeout = timeout
        self.ip = ip
        self.secret = secret
        self.cache: Dict[str, Configurations] = {}

    def _get_auth(self, url: str) -> Tuple[int, str]:
        # Refer: https://github.com/xhrg-product/apollo-client-python/blob/1.0.1/apollo/util.py#L25-L31
        ms = str(int(time.time() * 1000))
        uri = url[len(self.config_server_url) : len(url)]
        sign = signature(ms, uri, self.secret)
        return ms, sign

    def _prepare_header(self, url: str) -> dict:
        headers = {}
        if not self.secret:
            return headers
        ms, sign = self._get_auth(url)
        headers["Authorization"] = f"Apollo {self.app_id}:{sign}"
        headers["Timestamp"] = ms
        return headers

    def update(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
        call_cache_api: bool = True,
    ):
        root_key = f"{namespace}.{namespace_type.value}"
        if call_cache_api:
            self.cache[root_key] = self.read_configs_with_cache(
                namespace, namespace_type
            )
        else:
            self.cache[root_key] = self.read_configs_without_cache(
                namespace, namespace_type
            ).configurations

    def _read(
        self, api_path: str, namespace: str, namespace_type: NamespaceType
    ) -> Dict:
        _namespace = namespace
        if namespace_type != NamespaceType.PROPERTIES:
            _namespace = f"{_namespace}.{namespace_type.value}"
        url = f"{self.config_server_url}/{api_path}/{self.app_id}/{self.cluster_name}/{_namespace}?ip={self.ip}"
        query = {}
        if self.ip:
            query["ip"] = self.ip
        r = httpx.get(
            url,
            params=query,
            headers=self._prepare_header(url),
            timeout=self.timeout,
        )
        if r.status_code != 200:
            raise Exception(f"failed: status_code={r.status_code}, text={r.text}")
        return r.json()

    def read_configs_with_cache(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
    ) -> Configurations:
        """
        该接口会从缓存中获取配置，适合频率较高的配置拉取请求，如简单的每30秒轮询一次配置。

        由于缓存最多会有一秒的延时，所以如果需要配合配置推送通知实现实时更新配置的话，请参考「通过不带缓存的Http接口从Apollo读取配置」。
        """
        return self._read("configfiles", namespace, namespace_type)

    def read_configs_without_cache(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
    ) -> ReadConfigWithoutCache:
        """
        该接口会直接从数据库中获取配置，可以配合配置推送通知实现实时更新配置。
        """
        return ReadConfigWithoutCache(
            **self._read("configs", namespace, namespace_type)
        )

    def get(
        self,
        key: str,
        default=None,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
        call_cache_api: bool = False,
    ):
        root_key = f"{namespace}.{namespace_type.value}"
        if root_key not in self.cache:
            self.update(
                namespace=namespace,
                namespace_type=namespace_type,
                call_cache_api=call_cache_api,
            )
        return self.cache[root_key].get(key, default)


if __name__ == "__main__":
    client = Client(
        config_server_url="http://81.68.181.139:8080",
        app_id="apollo-common",
        cluster_name="default",
        secret="5fdc723621054e0f945cb441561687eb",
        ip="192.168.1.4",
    )
    print(client.read_configs_without_cache())
    print(client.get("test", call_cache_api=False))
