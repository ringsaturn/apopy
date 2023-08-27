import base64
import hashlib
import hmac
import json
import time
from enum import Enum
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx


def _signature(timestamp: str, uri: str, secret: str):
    # Refer: https://github.com/xhrg-product/apollo-client-python/blob/1.0.1/apollo/util.py#L25-L31
    string_to_sign = "" + timestamp + "\n" + uri
    hmac_code = hmac.new(
        secret.encode(), string_to_sign.encode(), hashlib.sha1
    ).digest()
    return base64.b64encode(hmac_code).decode()


Configurations = Dict[str, str]


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
        cluster_name: str = "default",
        ip: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: int = 90,
    ) -> "Client":
        """Apollo Client.

        Args:
            config_server_url (str): config server url
            app_id (str): app id
            cluster_name (str, optional): cluster name. Defaults to "default".
            ip (Optional[str], optional): ip. Defaults to None.
            secret (Optional[str], optional): secret. Defaults to None.
            timeout (int, optional): timeout. Defaults to 90.
        Returns:
            Client: apollo client
        """
        self.config_server_url = config_server_url
        self.app_id = app_id
        self.cluster_name = cluster_name
        self.timeout = timeout
        self.ip = ip
        self.secret = secret
        self.cache: Dict[str, Configurations] = {}

        # Key: namespaceName
        # Value: notificationId
        self.read_notification_cache: Dict[str, str] = {}

    def _get_auth(self, url: str) -> Tuple[int, str]:
        # Refer: https://github.com/xhrg-product/apollo-client-python/blob/1.0.1/apollo/util.py#L25-L31
        ms = str(int(time.time() * 1000))
        uri = url[len(self.config_server_url) : len(url)]
        sign = _signature(ms, uri, self.secret)
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
        """Update cache.

        Args:
            namespace (str, optional): namespace. Defaults to "application".
            namespace_type (NamespaceType, optional): namespace type. Defaults to NamespaceType.PROPERTIES.
            call_cache_api (bool, optional): call cache api. Defaults to True.
        """
        root_key = f"{namespace}.{namespace_type.value}"
        if call_cache_api:
            self.cache[root_key] = self.read_namespace_with_cache(
                namespace, namespace_type
            )
        self.cache[root_key] = self.read_namespace_without_cache(
            namespace, namespace_type
        )["configurations"]

    def _read(
        self, api_path: str, namespace: str, namespace_type: NamespaceType
    ) -> dict:
        _namespace = namespace
        if namespace_type != NamespaceType.PROPERTIES:
            _namespace = f"{_namespace}.{namespace_type.value}"
        url = "{config_server_url}/{api_path}/{app_id}/{cluster_name}/{namespace}?ip={ip}".format(
            config_server_url=self.config_server_url,
            api_path=api_path,
            app_id=self.app_id,
            cluster_name=self.cluster_name,
            namespace=_namespace,
            ip=self.ip,
        )
        r = httpx.get(
            url,
            headers=self._prepare_header(url),
            timeout=self.timeout,
        )
        if r.status_code != 200:
            raise Exception(f"failed: status_code={r.status_code}, text={r.text}")
        return r.json()

    def read_namespace_with_cache(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
    ) -> Configurations:
        """
        该接口会从缓存中获取配置，适合频率较高的配置拉取请求，如简单的每30秒轮询一次配置。

        由于缓存最多会有一秒的延时，所以如果需要配合配置推送通知实现实时更新配置的话，
        请参考 `read_namespace_without_cache` 。

        Args:
            namespace (str, optional): namespace. Defaults to "application".
            namespace_type (NamespaceType, optional): namespace type. Defaults to NamespaceType.PROPERTIES.
        Returns:
            Configurations: configurations
        """
        return self._read("configfiles/json", namespace, namespace_type)

    def read_namespace_without_cache(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
    ) -> Configurations:
        """
        该接口会直接从数据库中获取配置，可以配合配置推送通知实现实时更新配置。
        Args:
            namespace (str, optional): namespace. Defaults to "application".
            namespace_type (NamespaceType, optional): namespace type. Defaults to NamespaceType.PROPERTIES.
        Returns:
            Configurations: configurations
        """
        # appId: str
        # cluster: str
        # namespaceName: str
        # configurations: Configurations
        # releaseKey: str
        return self._read("configs", namespace, namespace_type)

    def get(
        self,
        key: str,
        default=None,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
        call_cache_api: bool = True,
    ) -> Optional[str]:
        """Get key from config.

        Args:

            key (str): key
            default (Any, optional): default value. Defaults to None.
            namespace (str, optional): namespace. Defaults to "application".
            namespace_type (NamespaceType, optional): namespace type. Defaults to NamespaceType.PROPERTIES.
            call_cache_api (bool, optional): call cache api. Defaults to True.

        Returns:
            Optional[str]: value
        """
        if not call_cache_api:
            return self.read_namespace_without_cache(
                namespace=namespace, namespace_type=namespace_type
            )["configurations"].get(key, default)
        root_key = f"{namespace}.{namespace_type.value}"
        if root_key not in self.cache:
            self.update(
                namespace=namespace,
                namespace_type=namespace_type,
                call_cache_api=call_cache_api,
            )
        return self.cache[root_key].get(key, default)

    def _read_notification(self, namespace: str = "application"):
        """Read notification.

        Returns:
            Notification: notification
        """
        url = "{config_server_url}/notifications/v2".format(
            config_server_url=self.config_server_url
        )
        notifications = []
        if namespace in self.read_notification_cache:
            notifications.append(
                {
                    "namespaceName": namespace,
                    "notificationId": self.read_notification_cache[namespace],
                }
            )
        else:
            notifications.append(
                {
                    "namespaceName": namespace,
                    "notificationId": -1,
                }
            )
        query_string = urlencode(
            {
                "appId": self.app_id,
                "cluster": self.cluster_name,
                "notifications": json.dumps(notifications),
            }
        )
        full_url = url + "?" + query_string
        r = httpx.get(
            full_url,
            headers=self._prepare_header(full_url),
            timeout=self.timeout,
        )
        if r.status_code == 304:
            # Nothing changed
            return []
        if r.status_code != 200:
            raise Exception(f"failed: status_code={r.status_code}, text={r.text}")
        # [
        #     {
        #         "namespaceName": "application",
        #         "notificationId": 17135,
        #         "messages": {"details": {"apollo-common+default+application": 17135}},
        #     }
        # ]
        return r.json()

    def read_notification_and_update(
        self,
        namespace: str = "application",
        namespace_type: NamespaceType = NamespaceType.PROPERTIES,
    ):
        notification_msgs = self._read_notification(namespace)
        if len(notification_msgs) == 0:
            return
        for msg in notification_msgs:
            self.update(
                namespace=namespace, namespace_type=namespace_type, call_cache_api=True
            )
            self.read_notification_cache[namespace] = msg["notificationId"]
