import datetime
import enum
import logging
import urllib
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from pydantic import BaseModel, Field
from workflows.transport import pika_transport

import zocalo.configuration

logger = logging.getLogger("workflows.transport.pika_transport")


class MessageStats(BaseModel):
    publish: Optional[int] = Field(None, description="Count of messages published.")

    publish_in: Optional[int] = Field(
        None,
        description='Count of messages published "in" to an exchange, i.e. not taking account of routing.',
    )
    publish_out: Optional[int] = Field(
        None,
        description='Count of messages published "out" of an exchange, i.e. taking account of routing.',
    )
    confirm: Optional[int] = Field(None, description="Count of messages confirmed.")
    deliver: Optional[int] = Field(
        None,
        description="Count of messages delivered in acknowledgement mode to consumers.",
    )
    deliver_no_ack: Optional[int] = Field(
        None,
        description="Count of messages delivered in no-acknowledgement mode to consumers.",
    )
    get: Optional[int] = Field(
        None,
        description="Count of messages delivered in acknowledgement mode in response to basic.get.",
    )
    get_no_ack: Optional[int] = Field(
        None,
        description="Count of messages delivered in no-acknowledgement mode in response to basic.get.",
    )
    deliver_get: Optional[int] = Field(
        None, description="Sum of all four of the above."
    )
    redeliver: Optional[int] = Field(
        None,
        description="Count of subset of messages in deliver_get which had the redelivered flag set.",
    )
    drop_unroutable: Optional[int] = Field(
        None, description="Count of messages dropped as unroutable."
    )
    return_unroutable: Optional[int] = Field(
        None, description="Count of messages returned to the publisher as unroutable."
    )


class ExchangeType(enum.Enum):
    direct = "direct"
    topic = "topic"
    headers = "headers"
    fanout = "fanout"


class ExchangeSpec(BaseModel):
    name: str = Field(
        ...,
        description="The name of the exchange with non-ASCII characters escaped as in C.",
    )
    type: ExchangeType = Field(..., description="The exchange type")
    durable: Optional[bool] = Field(
        False, description="Whether or not the exchange survives server restarts."
    )
    auto_delete: Optional[bool] = Field(
        False,
        description="Whether the exchange will be deleted automatically when no longer used.",
    )
    internal: Optional[bool] = Field(
        False,
        description="Whether the exchange is internal, i.e. cannot be directly published to by a client.",
    )
    arguments: dict[str, Any] = Field(..., description="Exchange arguments.")


class ExchangeInfo(ExchangeSpec):
    policy: Optional[str] = Field(
        None, description="Policy name for applying to the exchange."
    )
    message_stats: Optional[MessageStats] = None
    incoming: Optional[Dict] = Field(
        None,
        description="Detailed message stats (see section above) for publishes from channels into this exchange.",
    )
    outgoing: Optional[Dict] = Field(
        None,
        description="Detailed message stats for publishes from this exchange into queues.",
    )


class QueueState(str, enum.Enum):
    'The state of the queue. Normally "running", but may be "{syncing, message_count}" if the queue is synchronising.'

    running = "running"
    syncing = "syncing"
    message_count = "message_count"


class QueueSpec(BaseModel):
    name: str = Field(
        ...,
        description="The name of the queue with non-ASCII characters escaped as in C.",
    )
    durable: Optional[bool] = Field(
        False, description="Whether or not the queue survives server restarts."
    )
    auto_delete: Optional[bool] = Field(
        False,
        description="Whether the queue will be deleted automatically when no longer used.",
    )
    arguments: Optional[dict[str, Any]] = Field(None, description="Queue arguments.")


class QueueInfo(QueueSpec):
    policy: Optional[str] = Field(
        None, description="Effective policy name for the queue."
    )
    pid: Optional[int] = Field(
        None, description="Erlang process identifier of the queue."
    )
    owner_pid: Optional[int] = Field(
        None,
        description="Id of the Erlang process of the connection which is the exclusive owner of the queue. Empty if the queue is non-exclusive.",
    )
    exclusive: bool = Field(
        ...,
        description="True if queue is exclusive (i.e. has owner_pid), false otherwise.",
    )
    exclusive_consumer_pid: Optional[int] = Field(
        None,
        description="Id of the Erlang process representing the channel of the exclusive consumer subscribed to this queue. Empty if there is no exclusive consumer.",
    )
    exclusive_consumer_tag: Optional[str] = Field(
        None,
        description="Consumer tag of the exclusive consumer subscribed to this queue. Empty if there is no exclusive consumer.",
    )
    messages_ready: Optional[int] = Field(
        None, description="Number of messages ready to be delivered to clients."
    )
    messages_unacknowledged: Optional[int] = Field(
        None,
        description="Number of messages delivered to clients but not yet acknowledged.",
    )
    messages: Optional[int] = Field(
        None, description="Sum of ready and unacknowledged messages (queue depth)."
    )
    messages_ready_ram: Optional[int] = Field(
        None,
        description="Number of messages from messages_ready which are resident in ram.",
    )
    messages_unacknowledged_ram: Optional[int] = Field(
        None,
        description="Number of messages from messages_unacknowledged which are resident in ram.",
    )
    messages_ram: Optional[int] = Field(
        None, description="Total number of messages which are resident in ram."
    )
    messages_persistent: Optional[int] = Field(
        None,
        description="Total number of persistent messages in the queue (will always be 0 for transient queues).",
    )
    message_bytes: Optional[int] = Field(
        None,
        description="Sum of the size of all message bodies in the queue. This does not include the message properties (including headers) or any overhead.",
    )
    message_bytes_ready: Optional[int] = Field(
        None,
        description="Like message_bytes but counting only those messages ready to be delivered to clients.",
    )
    message_bytes_unacknowledged: Optional[int] = Field(
        None,
        description="Like message_bytes but counting only those messages delivered to clients but not yet acknowledged.",
    )
    message_bytes_ram: Optional[int] = Field(
        None,
        description="Like message_bytes but counting only those messages which are currently held in RAM.",
    )
    message_bytes_persistent: Optional[int] = Field(
        None,
        description="Like message_bytes but counting only those messages which are persistent.",
    )
    head_message_timestamp: Optional[datetime.datetime] = Field(
        None,
        description="The timestamp property of the first message in the queue, if present. Timestamps of messages only appear when they are in the paged-in state.",
    )
    disk_reads: Optional[int] = Field(
        None,
        description="Total number of times messages have been read from disk by this queue since it started.",
    )
    disk_writes: Optional[int] = Field(
        None,
        description="Total number of times messages have been written to disk by this queue since it started.",
    )
    consumers: Optional[int] = Field(None, description="Number of consumers.")
    consumer_utilisation: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Fraction of the time (between 0.0 and 1.0) that the queue is able to immediately deliver messages to consumers. This can be less than 1.0 if consumers are limited by network congestion or prefetch count.",
    )
    memory: Optional[int] = Field(
        None,
        description="Bytes of memory allocated by the runtime for the queue, including stack, heap and internal structures.",
    )
    state: Optional[QueueState] = None
    message_stats: Optional[MessageStats] = None
    incoming: Optional[dict] = Field(
        None,
        description="Detailed message stats (see section above) for publishes from exchanges into this queue.",
    )
    deliveries: Optional[dict] = Field(
        None,
        description="Detailed message stats for deliveries from this queue into channels.",
    )
    consumer_details: Optional[List[Any]] = Field(
        None,
        description="List of consumers on this channel, with some details on each.",
    )


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
    def __init__(self, url: str, user: str, password: str):
        self._auth = (user, password)
        self._url = url

    @classmethod
    def from_zocalo_configuration(cls, zc: zocalo.configuration.Configuration):
        return cls(
            url=zc.rabbitmqapi["base_url"],
            user=zc.rabbitmqapi["username"],
            password=zc.rabbitmqapi["password"],
        )

    @property
    def health_checks(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # https://rawcdn.githack.com/rabbitmq/rabbitmq-server/v3.9.7/deps/rabbitmq_management/priv/www/api/index.html
        HEALTH_CHECKS = {
            "health/checks/alarms",
            "health/checks/local-alarms",
            "health/checks/certificate-expiration/1/months",
            f"health/checks/port-listener/{pika_transport.PikaTransport.defaults['--rabbit-port']}",
            # f"health/checks/port-listener/1234",
            "health/checks/protocol-listener/amqp",
            "health/checks/virtual-hosts",
            "health/checks/node-is-mirror-sync-critical",
            "health/checks/node-is-quorum-critical",
        }

        success = {}
        failure = {}
        for health_check in HEALTH_CHECKS:
            response = self._get(health_check)
            if response.status_code == requests.codes.ok:
                success[health_check] = response.json()
            else:
                failure[health_check] = response.text
        return success, failure

    @property
    def connections(self) -> List[Dict[str, Any]]:
        return self._get("connections").json()

    @property
    def nodes(self) -> List[Dict[str, Any]]:
        # https://www.rabbitmq.com/monitoring.html#node-metrics
        return self._get("nodes").json()

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> requests.Response:
        return requests.get(f"{self._url}/{endpoint}", auth=self._auth, params=params)

    def _put(
        self, endpoint: str, params: Dict[str, Any] = None, json: Dict[str, Any] = None
    ) -> requests.Response:
        return requests.put(
            f"{self._url}/{endpoint}", auth=self._auth, params=params, json=json
        )

    def _delete(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> requests.Response:
        return requests.delete(
            f"{self._url}/{endpoint}", auth=self._auth, params=params
        )

    def exchanges(
        self, vhost: Optional[str] = None, name: Optional[str] = None
    ) -> Union[List[ExchangeInfo], ExchangeInfo]:
        endpoint = "exchanges"
        if vhost is not None and name is not None:
            endpoint = f"{endpoint}/{vhost}/{name}/"
            response = self._get(endpoint)
            print(response.url)
            print(response)
            return ExchangeInfo(**response.json())
        elif vhost is not None:
            endpoint = f"{endpoint}/{vhost}/"
        elif name is not None:
            raise ValueError("name can not be set without vhost")
        response = self._get(endpoint)
        logger.debug(response)
        return [ExchangeInfo(**qi) for qi in response.json()]

    def exchange_declare(self, vhost: str, exchange: ExchangeSpec):
        endpoint = f"exchanges/{vhost}/{exchange.name}"
        response = self._put(
            endpoint, json=exchange.dict(exclude_defaults=True, exclude={"name"})
        )
        logger.debug(response)

    def exchange_delete(self, vhost: str, name: str, if_unused: bool = False):
        endpoint = f"exchanges/{vhost}/{name}"
        response = self._delete(endpoint)
        logger.debug(response)

    def queues(
        self, vhost: Optional[str] = None, name: Optional[str] = None
    ) -> Union[List[QueueInfo], QueueInfo]:
        endpoint = "queues"
        if vhost is not None and name is not None:
            endpoint = f"{endpoint}/{vhost}/{name}/"
            response = self._get(endpoint)
            return QueueInfo(**response.json())
        elif vhost is not None:
            endpoint = f"{endpoint}/{vhost}/"
        elif name is not None:
            raise ValueError("name can not be set without vhost")
        response = self._get(endpoint)
        # print(response.url)
        logger.debug(response)
        return [QueueInfo(**qi) for qi in response.json()]

    def queue_declare(self, vhost: str, queue: QueueSpec):
        endpoint = f"queues/{vhost}/{queue.name}"
        response = self._put(
            endpoint, json=queue.dict(exclude_defaults=True, exclude={"name"})
        )
        logger.debug(response)

    def queue_delete(
        self, vhost: str, name: str, if_unused: bool = False, if_empty: bool = False
    ):
        endpoint = f"queues/{vhost}/{name}"
        response = self._delete(endpoint)
        logger.debug(response)


if __name__ == "__main__":
    import time

    zc = zocalo.configuration.from_file()
    zc.activate()
    rmq = RabbitMQAPI.from_zocalo_configuration(zc)
    print(rmq.queues())
    print(rmq.queues(vhost="zocalo", name="processing_recipe"))
    # time.sleep(5)
    rmq.queue_declare(
        vhost="zocalo",
        queue=QueueSpec(
            name="foo", auto_delete=True, arguments={"x-single-active-consumer": True}
        ),
    )
    time.sleep(5)
    print(rmq.queues(vhost="zocalo", name="foo"))
    rmq.queue_delete(vhost="zocalo", name="foo")
    # print(rmq.queues(vhost="zocalo", name="foo"))
    for q in rmq.queues():
        print(q.message_stats)
    print()
    for ex in rmq.exchanges():
        print(ex)
    print(rmq.exchanges(vhost="zocalo", name=""))
