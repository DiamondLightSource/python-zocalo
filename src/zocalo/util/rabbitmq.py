from __future__ import annotations

import base64
import datetime
import enum
import hashlib
import logging
import pathlib
import secrets
import urllib
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from pydantic import BaseModel, Field
from workflows.transport import pika_transport

import zocalo.configuration

logger = logging.getLogger("zocalo.util.rabbitmq")


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
    timeout: Optional[int] = Field(
        None,
        description="Connection timeout / negotiated heartbeat interval, in seconds.",
    )
    frame_max: int = Field(..., description="Maximum frame size (bytes).")
    channel_max: Optional[int] = Field(
        None, description="Maximum number of channels on this connection."
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
    config_files: Optional[List[pathlib.Path]] = Field(
        None, description="List of config files read by the node."
    )
    # contexts	List of all HTTP listeners on the node.
    db_dir: Optional[pathlib.Path] = Field(
        None, description="Location of the persistent storage used by the node."
    )
    disk_free: int = Field(..., description="Disk free space in bytes.")
    disk_free_alarm: bool = Field(
        ..., description="Whether the disk alarm has gone off."
    )
    disk_free_limit: Optional[int] = Field(
        None, description="Point at which the disk alarm will go off."
    )
    enabled_plugins: Optional[List[str]] = Field(
        None,
        description="List of plugins which are both explicitly enabled and running.",
    )
    # exchange_types	Exchange types available on the node.
    fd_total: int = Field(..., description="File descriptors available.")
    fd_used: int = Field(..., description="Used file descriptors.")
    io_read_avg_time: Optional[int] = Field(
        None,
        ge=0,
        description="Average wall time (milliseconds) for each disk read operation in the last statistics interval.",
    )
    io_read_bytes: Optional[int] = Field(
        None, description="Total number of bytes read from disk by the persister."
    )
    io_read_count: Optional[int] = Field(
        None, description="Total number of read operations by the persister."
    )
    io_reopen_count: Optional[int] = Field(
        None,
        description="Total number of times the persister has needed to recycle file handles between queues. In an ideal world this number will be zero; if the number is large, performance might be improved by increasing the number of file handles available to RabbitMQ.",
    )
    io_seek_avg_time: Optional[int] = Field(
        None,
        description="Average wall time (milliseconds) for each seek operation in the last statistics interval.",
    )
    io_seek_count: Optional[int] = Field(
        None, description="Total number of seek operations by the persister."
    )
    io_sync_avg_time: Optional[int] = Field(
        None,
        description="Average wall time (milliseconds) for each fsync() operation in the last statistics interval.",
    )
    io_sync_count: Optional[int] = Field(
        None, description="Total number of fsync() operations by the persister."
    )
    io_write_avg_time: Optional[int] = Field(
        None,
        description="Average wall time (milliseconds) for each disk write operation in the last statistics interval.",
    )
    io_write_bytes: Optional[int] = Field(
        None, description="Total number of bytes written to disk by the persister."
    )
    io_write_count: Optional[int] = Field(
        None, description="Total number of write operations by the persister."
    )
    log_files: Optional[List[pathlib.Path]] = Field(
        None,
        description='List of log files used by the node. If the node also sends messages to stdout, "<stdout>" is also reported in the list.',
    )
    mem_used: int = Field(..., description="Memory used in bytes.")
    mem_alarm: bool = Field(..., description="Whether the memory alarm has gone off.")
    mem_limit: Optional[int] = Field(
        None, description="Point at which the memory alarm will go off."
    )
    mnesia_disk_tx_count: Optional[int] = Field(
        None,
        description="Number of Mnesia transactions which have been performed that required writes to disk. (e.g. creating a durable queue). Only transactions which originated on this node are included.",
    )
    mnesia_ram_tx_count: Optional[int] = Field(
        None,
        description="Number of Mnesia transactions which have been performed that did not require writes to disk. (e.g. creating a transient queue). Only transactions which originated on this node are included.",
    )
    msg_store_read_count: Optional[int] = Field(
        None,
        description="Number of messages which have been read from the message store.",
    )
    msg_store_write_count: Optional[int] = Field(
        None,
        description="Number of messages which have been written to the message store.",
    )
    name: str = Field(..., description="Node name.")
    net_ticktime: Optional[int] = Field(
        None, description="Current kernel net_ticktime setting for the node."
    )
    os_pid: Optional[int] = Field(
        None,
        description="Process identifier for the Operating System under which this node is running.",
    )
    # partitions	List of network partitions this node is seeing.
    proc_total: int = Field(..., description="Maximum number of Erlang processes.")
    proc_used: int = Field(..., description="Number of Erlang processes in use.")
    processors: Optional[int] = Field(
        None, description="Number of cores detected and usable by Erlang."
    )
    queue_index_journal_write_count: Optional[int] = Field(
        None,
        description="Number of records written to the queue index journal. Each record represents a message being published to a queue, being delivered from a queue, and being acknowledged in a queue.",
    )
    queue_index_read_count: Optional[int] = Field(
        None, description="Number of records read from the queue index."
    )
    queue_index_write_count: Optional[int] = Field(
        None, description="Number of records written to the queue index."
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
    sockets_total: Optional[int] = Field(
        None, description="File descriptors available for use as sockets."
    )
    sockets_used: int = Field(..., description="File descriptors used as sockets.")
    type: Optional[NodeType] = None
    uptime: Optional[int] = Field(
        None, description="Time since the Erlang VM started, in milliseconds."
    )
    # memory	Detailed memory use statistics. Only appears if ?memory=true is appended to the URL.
    # binary	Detailed breakdown of the owners of binary memory. Only appears if ?binary=true is appended to the URL. Note that this can be an expensive query if there are many small binaries in the system.


class DestinationType(enum.Enum):
    QUEUE = "q"
    EXCHANGE = "e"


class BindingSpec(BaseModel):
    source: str = Field(
        ..., description="The name of the source exchange of the binding"
    )
    destination: str = Field(
        ...,
        description="The name of the end point of the binding (either an exchange or a queue)",
    )
    destination_type: DestinationType = Field(
        ..., description="The type of the binding end point"
    )
    vhost: str = Field(
        ..., description="Virtual host name with non-ASCII characters escaped as in C."
    )
    routing_key: str = Field("", description="Routing key attached to binding")
    arguments: Optional[dict] = Field(
        default_factory=dict, description="Binding arguments"
    )


class BindingInfo(BindingSpec):
    properties_key: str = Field(
        "",
        description="Unique identifier composed of the bindings routing key and a hash of its arguments",
    )


class ExchangeType(enum.Enum):
    direct = "direct"
    topic = "topic"
    headers = "headers"
    fanout = "fanout"
    x_delayed_message = "x-delayed-message"


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
    arguments: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Exchange arguments."
    )
    vhost: str = Field(
        ..., description="Virtual host name with non-ASCII characters escaped as in C."
    )

    class Config:
        use_enum_values = True


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


class PolicyApplyTo(enum.Enum):
    """Which types of object this policy should apply to."""

    queues = "queues"
    exchanges = "exchanges"
    all = "all"


class PolicySpec(BaseModel):
    """Sets a policy."""

    vhost: str = Field(
        ..., description="Virtual host name with non-ASCII characters escaped as in C."
    )
    name: str = Field(..., description="The name of the policy.")
    pattern: str = Field(
        ...,
        description="The regular expression, which when matches on a given resources causes the policy to apply.",
    )
    definition: Dict[str, Any] = Field(
        ...,
        description="A set of key/value pairs (think a JSON document) that will be injected into the map of optional arguments of the matching queues and exchanges.",
    )
    priority: int = Field(
        0,
        description="The priority of the policy as an integer. Higher numbers indicate greater precedence. The default is 0.",
    )
    apply_to: PolicyApplyTo = Field(
        default=PolicyApplyTo.all,
        alias="apply-to",
        description="Which types of object this policy should apply to.",
    )

    class Config:
        use_enum_values = True
        validate_all = True
        allow_population_by_field_name = True


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
    arguments: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Queue arguments."
    )
    vhost: str = Field(
        ..., description="Virtual host name with non-ASCII characters escaped as in C."
    )


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


class HashingAlgorithm(enum.Enum):
    rabbit_password_hashing_sha256 = "rabbit_password_hashing_sha256"
    rabbit_password_hashing_sha512 = "rabbit_password_hashing_sha512"
    rabbit_password_hashing_md5 = "rabbit_password_hashing_md5"


class UserSpec(BaseModel):
    """
    Either password or password_hash can be set. If neither are set the user will not be
    able to log in with a password, but other mechanisms like client certificates may
    be used. Setting password_hash to "" will ensure the user cannot use a password to
    log in. tags is a list of tags for the user. Currently recognised tags are
    administrator, monitoring, and management.
    """

    name: str = Field(..., description="Username")
    password_hash: str = Field(..., description="Hash of the user password.")
    hashing_algorithm: HashingAlgorithm
    tags: List[str]

    class Config:
        use_enum_values = True


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
        self._url = url
        self._session = requests.Session()
        self._session.auth = (user, password)

    @classmethod
    def from_zocalo_configuration(cls, zc: zocalo.configuration.Configuration):
        instance = None
        base_url = zc.rabbitmqapi["base_url"]
        for url in base_url.split(","):
            instance = cls(
                url=url,
                user=zc.rabbitmqapi["username"],
                password=zc.rabbitmqapi["password"],
            )
            try:
                instance.get("health/checks/alarms")
                break
            except requests.ConnectionError as e:
                logger.warning(f"Could not connect to {url}: {e}")
                instance = None
        if not instance:
            raise RuntimeError(f"Could not connect to RabbitMQ API: {base_url}")
        return instance

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
                failure[health_check] = response.json()
        return success, failure

    def get(
        self, endpoint: str, params: Dict[str, Any] = None, timeout: float | None = None
    ) -> requests.Response:
        return self._session.get(
            f"{self._url}/{endpoint}", params=params, timeout=timeout
        )

    def put(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
        timeout: float | None = None,
    ) -> requests.Response:
        return self._session.put(
            f"{self._url}/{endpoint}", params=params, json=json, timeout=timeout
        )

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float | None = None,
    ) -> requests.Response:
        return self._session.post(
            f"{self._url}/{endpoint}", data=data, json=json, timeout=timeout
        )

    def delete(
        self, endpoint: str, params: Dict[str, Any] = None, timeout: float | None = None
    ) -> requests.Response:
        return self._session.delete(
            f"{self._url}/{endpoint}", params=params, timeout=timeout
        )

    def bindings(
        self,
        vhost: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        destination_type: Optional[str] = None,
    ) -> List[BindingInfo]:
        endpoint = "bindings"
        if vhost is not None:
            endpoint = f"{endpoint}/{vhost}"
        _check = {source, destination, destination_type}
        if None in _check and len(_check) > 1:
            raise ValueError(
                "Either all of source, destination and destination_type must be specified, or none of them"
            )
        if destination_type is not None:
            endpoint = f"{endpoint}/e/{source}/{destination_type}/{destination}"
        dest_map = {"queue": "q", "exchange": "e"}
        conv = (
            lambda key, value: dest_map[value] if key == "destination_type" else value
        )
        return [
            BindingInfo(**{_r[0]: conv(_r[0], _r[1]) for _r in r.items()})
            for r in self.get(endpoint).json()
        ]

    def binding_declare(self, binding: BindingSpec):
        endpoint = f"bindings/{binding.vhost}/e/{binding.source}/{binding.destination_type.value}/{binding.destination}"
        resp = self.post(
            endpoint,
            json=binding.dict(
                exclude_defaults=True,
                exclude={"vhost", "source", "destination", "destination_type"},
            ),
        )
        if resp.status_code == 404:
            logger.error(f"404 not found when declaring {endpoint}")
        elif resp.status_code == 405:
            logger.error(f"405 not allowed to declare {endpoint}")

    def bindings_delete(
        self,
        vhost: str,
        source: str,
        destination: str,
        destination_type: str,
        properties_key: Optional[str] = None,
    ):
        # If properties_key is not specified then all bindings between the specified
        # source and destination are deleted
        endpoint = f"bindings/{vhost}/e/{source}/{destination_type}/{destination}"
        if properties_key is None:
            dest_map = {"queue": "q", "exchange": "e"}
            conv = (
                lambda key, value: dest_map[value]
                if key == "destination_type"
                else value
            )
            props = [
                BindingInfo(
                    **{_r[0]: conv(_r[0], _r[1]) for _r in r.items()}
                ).properties_key
                for r in self.get(endpoint).json()
            ]
        else:
            props = [properties_key]
        for prop in props:
            resp = self.delete(f"{endpoint}/{prop}")
            if resp.status_code == 404:
                logger.error(f"404 not found when deleting {endpoint}/{prop}")
            elif resp.status_code == 405:
                logger.error(f"405 not allowed to delete {endpoint}/{prop}")

    def connections(
        self, name: Optional[str] = None
    ) -> Union[List[ConnectionInfo], ConnectionInfo]:
        endpoint = "connections"
        if name is not None:
            endpoint = f"{endpoint}/{name}/"
            response = self.get(endpoint)
            return ConnectionInfo(**response.json())
        response = self.get(endpoint)
        return [ConnectionInfo(**qi) for qi in response.json()]

    def nodes(self, name: Optional[str] = None) -> Union[List[NodeInfo], NodeInfo]:
        # https://www.rabbitmq.com/monitoring.html#node-metrics
        endpoint = "nodes"
        if name is not None:
            endpoint = f"{endpoint}/{name}"
            response = self.get(endpoint)
            return NodeInfo(**response.json())
        response = self.get(endpoint)
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
        return [ExchangeInfo(**qi) for qi in response.json()]

    def exchange_declare(self, exchange: ExchangeSpec):
        endpoint = f"exchanges/{exchange.vhost}/{exchange.name}/"
        self.put(
            endpoint,
            json=exchange.dict(exclude_defaults=True, exclude={"name", "vhost"}),
        )

    def exchange_delete(self, vhost: str, name: str, if_unused: bool = False):
        endpoint = f"exchanges/{vhost}/{name}"
        resp = self.delete(endpoint, params={"if-unused": if_unused})
        if resp.status_code == 404:
            logger.error(f"404 not found when deleting {endpoint}")
        elif resp.status_code == 405:
            logger.error(f"405 not allowed to delete {endpoint}")

    def policies(self, vhost: Optional[str] = None) -> List[PolicySpec]:
        endpoint = "policies"
        if vhost is not None:
            endpoint = f"{endpoint}/{vhost}/"
        response = self.get(endpoint)
        return [PolicySpec(**p) for p in response.json()]

    def policy(self, vhost: str, name: str) -> PolicySpec:
        endpoint = f"policies/{vhost}/{name}/"
        response = self.get(endpoint)
        return PolicySpec(**response.json())

    def set_policy(self, policy: PolicySpec):
        endpoint = f"policies/{policy.vhost}/{policy.name}/"
        self.put(
            endpoint,
            json=policy.dict(
                exclude_defaults=True, exclude={"name", "vhost"}, by_alias=True
            ),
        )

    def clear_policy(self, vhost: str, name: str):
        endpoint = f"policies/{vhost}/{name}/"
        self.delete(endpoint)

    def queues(
        self, vhost: Optional[str] = None, name: Optional[str] = None
    ) -> Union[List[QueueInfo], QueueInfo]:
        endpoint = "queues"
        if vhost is not None and name is not None:
            endpoint = f"{endpoint}/{vhost}/{name}"
            response = self.get(endpoint)
            return QueueInfo(**response.json())
        elif vhost is not None:
            endpoint = f"{endpoint}/{vhost}"
        elif name is not None:
            raise ValueError("name can not be set without vhost")
        response = self.get(endpoint)
        return [QueueInfo(**qi) for qi in response.json()]

    def queue_declare(self, queue: QueueSpec):
        endpoint = f"queues/{queue.vhost}/{queue.name}"
        self.put(
            endpoint, json=queue.dict(exclude_defaults=True, exclude={"name", "vhost"})
        )

    def queue_delete(
        self, vhost: str, name: str, if_unused: bool = False, if_empty: bool = False
    ):
        endpoint = f"queues/{vhost}/{name}"
        self.delete(endpoint, params={"if-unused": if_unused, "if-empty": if_empty})

    def users(self) -> List[UserSpec]:
        endpoint = "users"
        response = self.get(endpoint)
        return [UserSpec(**user) for user in response.json()]

    def user(self, name: str) -> UserSpec:
        endpoint = f"users/{name}/"
        response = self.get(endpoint).json()
        return UserSpec(**response)

    def user_put(self, user: UserSpec):
        endpoint = f"users/{user.name}/"
        submission = user.dict(exclude_defaults=True, exclude={"name"})
        submission["tags"] = ",".join(submission["tags"])
        self.put(endpoint, json=submission)

    def user_delete(self, name: str):
        endpoint = f"users/{name}/"
        self.delete(endpoint)


def hash_password(passwd: str, salt: Optional[str] = None) -> str:
    if salt:
        # extract salt from an existing password hash
        salt_bytes = base64.b64decode(salt)[:4]
    else:
        salt_bytes = secrets.token_bytes(4)
    utf8 = passwd.encode("utf-8")
    temp1 = salt_bytes + utf8
    temp2 = hashlib.sha256(temp1).digest()  # lgtm
    salted_hash = salt_bytes + temp2
    pass_hash = base64.b64encode(salted_hash)
    return pass_hash.decode()
