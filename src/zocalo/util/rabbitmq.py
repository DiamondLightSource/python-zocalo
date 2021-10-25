import datetime
import enum
import logging
import pathlib
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


class ConnectionState(enum.Enum):
    starting = "starting"
    tuning = "tuning"
    opening = "opening"
    running = "running"
    flow = "flow"
    blocking = "blocking"
    blocked = "blocked"
    closing = "closing"
    closed = "closed"


class ConnectionInfo(BaseModel):
    """TCP/IP connection statistics."""

    pid: Optional[int] = Field(
        int, description="Id of the Erlang process associated with the connection."
    )
    name: str = Field(..., description="Readable name for the connection.")
    port: int = Field(..., description="Server port.")
    host: str = Field(
        ...,
        description="Server hostname obtained via reverse DNS, or its IP address if reverse DNS failed or was disabled.",
    )
    peer_port: int = Field(..., description="Peer port.")
    peer_host: str = Field(
        ...,
        description="Peer hostname obtained via reverse DNS, or its IP address if reverse DNS failed or was not enabled.",
    )
    ssl: bool = Field(
        ...,
        description="Boolean indicating whether the connection is secured with SSL.",
    )
    ssl_protocol: Optional[str] = Field(
        None, description='SSL protocol (e.g. "tlsv1").'
    )
    ssl_key_exchange: Optional[str] = Field(
        None, description='SSL key exchange algorithm (e.g. "rsa").'
    )
    ssl_cipher: Optional[str] = Field(
        None, description='SSL cipher algorithm (e.g. "aes_256_cbc").'
    )
    ssl_hash: Optional[str] = Field(None, description='SSL hash function (e.g. "sha").')
    peer_cert_subject: Optional[str] = Field(
        None, description="The subject of the peer's SSL certificate, in RFC4514 form."
    )
    peer_cert_issuer: Optional[str] = Field(
        None, description="The issuer of the peer's SSL certificate, in RFC4514 form."
    )
    peer_cert_validity: Optional[str] = Field(
        None, description="The period for which the peer's SSL certificate is valid."
    )
    state: ConnectionState
    channels: int = Field(..., description="Number of channels using the connection.")
    protocol: str = Field(
        ...,
        description="Version of the AMQP protocol in use; currently one of: {0,9,1} {0,8,0}",
    )
    auth_mechanism: str = Field(
        ..., description='SASL authentication mechanism used, such as "PLAIN".'
    )
    user: str = Field(..., description="Username associated with the connection.")
    vhost: str = Field(
        ..., description="Virtual host name with non-ASCII characters escaped as in C."
    )
    timeout: int = Field(
        ...,
        description="Connection timeout / negotiated heartbeat interval, in seconds.",
    )
    frame_max: int = Field(..., description="Maximum frame size (bytes).")
    channel_max: int = Field(
        ..., description="Maximum number of channels on this connection."
    )
    # client_properties
    # Informational properties transmitted by the client during connection establishment.
    # recv_oct:
    # Octets received.
    # recv_cnt
    # Packets received.
    # send_oct
    # Octets send.
    # send_cnt
    # Packets sent.
    # send_pend
    # Send queue size.
    connected_at: datetime.datetime = Field(
        ..., description="Date and time this connection was established, as timestamp."
    )


class NodeType(enum.Enum):
    disc = "disc"
    ram = "ram"


class NodeInfo(BaseModel):
    # applications	List of all Erlang applications running on the node.
    # auth_mechanisms	List of all SASL authentication mechanisms installed on the node.
    # cluster_links	A list of the other nodes in the cluster. For each node, there are details of the TCP connection used to connect to it and statistics on data that has been transferred.
    config_files: List[pathlib.Path] = Field(
        ..., description="List of config files read by the node."
    )
    # contexts	List of all HTTP listeners on the node.
    db_dir: pathlib.Path = Field(
        ..., description="Location of the persistent storage used by the node."
    )
    disk_free: int = Field(..., description="Disk free space in bytes.")
    disk_free_alarm: bool = Field(
        ..., description="Whether the disk alarm has gone off."
    )
    disk_free_limit: int = Field(
        ..., description="Point at which the disk alarm will go off."
    )
    enabled_plugins: List[str] = Field(
        ...,
        description="List of plugins which are both explicitly enabled and running.",
    )
    # exchange_types	Exchange types available on the node.
    fd_total: int = Field(..., description="File descriptors available.")
    fd_used: int = Field(..., description="Used file descriptors.")
    io_read_avg_time: float = Field(
        ...,
        ge=0,
        description="Average wall time (milliseconds) for each disk read operation in the last statistics interval.",
    )
    io_read_bytes: int = Field(
        ..., description="Total number of bytes read from disk by the persister."
    )
    io_read_count: int = Field(
        ..., description="Total number of read operations by the persister."
    )
    io_reopen_count: int = Field(
        ...,
        description="Total number of times the persister has needed to recycle file handles between queues. In an ideal world this number will be zero; if the number is large, performance might be improved by increasing the number of file handles available to RabbitMQ.",
    )
    io_seek_avg_time: int = Field(
        ...,
        description="Average wall time (milliseconds) for each seek operation in the last statistics interval.",
    )
    io_seek_count: int = Field(
        ..., description="Total number of seek operations by the persister."
    )
    io_sync_avg_time: int = Field(
        ...,
        description="Average wall time (milliseconds) for each fsync() operation in the last statistics interval.",
    )
    io_sync_count: int = Field(
        ..., description="Total number of fsync() operations by the persister."
    )
    io_write_avg_time: int = Field(
        ...,
        description="Average wall time (milliseconds) for each disk write operation in the last statistics interval.",
    )
    io_write_bytes: int = Field(
        ..., description="Total number of bytes written to disk by the persister."
    )
    io_write_count: int = Field(
        ..., description="Total number of write operations by the persister."
    )
    log_files: List[pathlib.Path] = Field(
        ...,
        description='List of log files used by the node. If the node also sends messages to stdout, "<stdout>" is also reported in the list.',
    )
    mem_used: int = Field(..., description="Memory used in bytes.")
    mem_alarm: bool = Field(..., description="Whether the memory alarm has gone off.")
    mem_limit: int = Field(
        ..., description="Point at which the memory alarm will go off."
    )
    mnesia_disk_tx_count: int = Field(
        ...,
        description="Number of Mnesia transactions which have been performed that required writes to disk. (e.g. creating a durable queue). Only transactions which originated on this node are included.",
    )
    mnesia_ram_tx_count: int = Field(
        ...,
        description="Number of Mnesia transactions which have been performed that did not require writes to disk. (e.g. creating a transient queue). Only transactions which originated on this node are included.",
    )
    msg_store_read_count: int = Field(
        ...,
        description="Number of messages which have been read from the message store.",
    )
    msg_store_write_count: int = Field(
        ...,
        description="Number of messages which have been written to the message store.",
    )
    name: str = Field(..., description="Node name.")
    net_ticktime: int = Field(
        ..., description="Current kernel net_ticktime setting for the node."
    )
    os_pid: int = Field(
        ...,
        description="Process identifier for the Operating System under which this node is running.",
    )
    # partitions	List of network partitions this node is seeing.
    proc_total: int = Field(..., description="Maximum number of Erlang processes.")
    proc_used: int = Field(..., description="Number of Erlang processes in use.")
    processors: int = Field(
        ..., description="Number of cores detected and usable by Erlang."
    )
    queue_index_journal_write_count: int = Field(
        ...,
        description="Number of records written to the queue index journal. Each record represents a message being published to a queue, being delivered from a queue, and being acknowledged in a queue.",
    )
    queue_index_read_count: int = Field(
        ..., description="Number of records read from the queue index."
    )
    queue_index_write_count: int = Field(
        ..., description="Number of records written to the queue index."
    )
    # rates_mode: 'none', 'basic' or 'detailed'.
    run_queue: float = Field(
        ..., description="Average number of Erlang processes waiting to run."
    )
    running: bool = Field(
        ...,
        description="Boolean for whether this node is up. Obviously if this is false, most other stats will be missing.",
    )
    # sasl_log_file	Location of sasl log file.
    sockets_total: int = Field(
        ..., description="File descriptors available for use as sockets."
    )
    sockets_used: int = Field(..., description="File descriptors used as sockets.")
    type: NodeType
    uptime: int = Field(
        ..., description="Time since the Erlang VM started, in milliseconds."
    )
    # memory	Detailed memory use statistics. Only appears if ?memory=true is appended to the URL.
    # binary	Detailed breakdown of the owners of binary memory. Only appears if ?binary=true is appended to the URL. Note that this can be an expensive query if there are many small binaries in the system.


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
            response = self.get(health_check)
            if response.status_code == requests.codes.ok:
                success[health_check] = response.json()
            else:
                failure[health_check] = response.text
        return success, failure

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> requests.Response:
        return requests.get(f"{self._url}/{endpoint}", auth=self._auth, params=params)

    def put(
        self, endpoint: str, params: Dict[str, Any] = None, json: Dict[str, Any] = None
    ) -> requests.Response:
        return requests.put(
            f"{self._url}/{endpoint}", auth=self._auth, params=params, json=json
        )

    def delete(self, endpoint: str, params: Dict[str, Any] = None) -> requests.Response:
        return requests.delete(
            f"{self._url}/{endpoint}", auth=self._auth, params=params
        )

    def connections(
        self, name: Optional[str] = None
    ) -> Union[List[ConnectionInfo], ConnectionInfo]:
        endpoint = "connections"
        if name is not None:
            endpoint = f"{endpoint}/{name}/"
            response = self.get(endpoint)
            return ConnectionInfo(**response.json())
        response = self.get(endpoint)
        logger.debug(response)
        return [ConnectionInfo(**qi) for qi in response.json()]

    def nodes(self, name: Optional[str] = None) -> Union[List[NodeInfo], NodeInfo]:
        # https://www.rabbitmq.com/monitoring.html#node-metrics
        endpoint = "nodes"
        if name is not None:
            endpoint = f"{endpoint}/{name}/"
            response = self.get(endpoint)
            return NodeInfo(**response.json())
        response = self.get(endpoint)
        logger.debug(response)
        return [NodeInfo(**qi) for qi in response.json()]

    def exchanges(
        self, vhost: Optional[str] = None, name: Optional[str] = None
    ) -> Union[List[ExchangeInfo], ExchangeInfo]:
        endpoint = "exchanges"
        if vhost is not None and name is not None:
            endpoint = f"{endpoint}/{vhost}/{name}/"
            response = self.get(endpoint)
            return ExchangeInfo(**response.json())
        elif vhost is not None:
            endpoint = f"{endpoint}/{vhost}/"
        elif name is not None:
            raise ValueError("name can not be set without vhost")
        response = self.get(endpoint)
        logger.debug(response)
        return [ExchangeInfo(**qi) for qi in response.json()]

    def exchange_declare(self, vhost: str, exchange: ExchangeSpec):
        endpoint = f"exchanges/{vhost}/{exchange.name}"
        response = self.put(
            endpoint, json=exchange.dict(exclude_defaults=True, exclude={"name"})
        )
        logger.debug(response)

    def exchange_delete(self, vhost: str, name: str, if_unused: bool = False):
        endpoint = f"exchanges/{vhost}/{name}"
        response = self.delete(endpoint)
        logger.debug(response)

    def queues(
        self, vhost: Optional[str] = None, name: Optional[str] = None
    ) -> Union[List[QueueInfo], QueueInfo]:
        endpoint = "queues"
        if vhost is not None and name is not None:
            endpoint = f"{endpoint}/{vhost}/{name}/"
            response = self.get(endpoint)
            return QueueInfo(**response.json())
        elif vhost is not None:
            endpoint = f"{endpoint}/{vhost}/"
        elif name is not None:
            raise ValueError("name can not be set without vhost")
        response = self.get(endpoint)
        # print(response.url)
        logger.debug(response)
        return [QueueInfo(**qi) for qi in response.json()]

    def queue_declare(self, vhost: str, queue: QueueSpec):
        endpoint = f"queues/{vhost}/{queue.name}"
        response = self.put(
            endpoint, json=queue.dict(exclude_defaults=True, exclude={"name"})
        )
        logger.debug(response)

    def queue_delete(
        self, vhost: str, name: str, if_unused: bool = False, if_empty: bool = False
    ):
        endpoint = f"queues/{vhost}/{name}"
        response = self.delete(endpoint)
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

    nodes = rmq.nodes()
    print(rmq.nodes(name=nodes[0].name))

    connections = rmq.connections()
    print(rmq.connections(name=connections[0].name))
