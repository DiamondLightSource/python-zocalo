import json
import urllib
import urllib.request
from typing import Any, Dict, List, Tuple

from workflows.transport import pika_transport

import zocalo.configuration


def http_api_request(
    zc: zocalo.configuration.Configuration,
    api_path: str,
) -> urllib.request.Request:
    """
    Return a urllib.request.Request to query the RabbitMQ HTTP API.

    Credentials are obtained via zocalo.configuration.

    Args:
        zc (zocalo.configuration.Configuration): Zocalo configuration object
        api_path (str): The path to be combined with the base_url defined by
            the Zocalo configuration object to give the full path to the API
            endpoint.
    """
    if not zc.rabbitmqapi:
        raise zocalo.ConfigurationError(
            "There are no RabbitMQ API credentials configured in your environment"
        )
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(
        realm=None,
        uri=zc.rabbitmqapi["base_url"],
        user=zc.rabbitmqapi["username"],
        passwd=zc.rabbitmqapi["password"],
    )
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)
    urllib.request.install_opener(opener)
    return urllib.request.Request(f"{zc.rabbitmqapi['base_url']}{api_path}")


class RabbitMQAPI:
    def __init__(self, zc: zocalo.configuration.Configuration):
        self._zc = zc

    @property
    def health_checks(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # https://rawcdn.githack.com/rabbitmq/rabbitmq-server/v3.9.7/deps/rabbitmq_management/priv/www/api/index.html
        HEALTH_CHECKS = {
            "/health/checks/alarms",
            "/health/checks/local-alarms",
            "/health/checks/certificate-expiration/1/months",
            f"/health/checks/port-listener/{pika_transport.PikaTransport.defaults['--rabbit-port']}",
            # f"/health/checks/port-listener/1234",
            "/health/checks/protocol-listener/amqp",
            "/health/checks/virtual-hosts",
            "/health/checks/node-is-mirror-sync-critical",
            "/health/checks/node-is-quorum-critical",
        }

        success = {}
        failure = {}
        for health_check in HEALTH_CHECKS:
            try:
                with urllib.request.urlopen(
                    http_api_request(self._zc, health_check)
                ) as response:
                    success[health_check] = json.loads(response.read())
            except urllib.error.HTTPError as e:
                failure[health_check] = str(e)
        return success, failure

    @property
    def connections(self) -> List[Dict[str, Any]]:
        with urllib.request.urlopen(
            http_api_request(self._zc, "/connections")
        ) as response:
            return json.loads(response.read())

    @property
    def nodes(self) -> List[Dict[str, Any]]:
        # https://www.rabbitmq.com/monitoring.html#node-metrics
        with urllib.request.urlopen(http_api_request(self._zc, "/nodes")) as response:
            return json.loads(response.read())

    @property
    def queues(self) -> List[Dict[str, Any]]:
        # https://www.rabbitmq.com/monitoring.html#queue-metrics
        with urllib.request.urlopen(http_api_request(self._zc, "/queues")) as response:
            return json.loads(response.read())
