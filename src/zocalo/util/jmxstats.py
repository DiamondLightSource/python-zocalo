#
# simple API to obtain JMX information
#
# Point to a Zocalo configuration object with a loaded jmx plugin instance to use it, eg:
#  zc = zocalo.configuration.from_string("...")
#  zc.activate_environment("environment-with-a-jmx-plugin-configuration")
#  jmx = JMXAPI(zc)
# Then you can access objects with eg.
#  jmx.java.lang(type="Memory")
#  jmx.org.apache.activemq(type="Broker", brokerName="localhost/TotalConsumerCount")


from __future__ import annotations

import base64
import json
import urllib.request
from collections.abc import Callable
from typing import Any

import zocalo.configuration


class JMXAPIPath:
    """A recursing helper object that encodes a JMX bean path."""

    def __init__(self, path: str, callback: Callable[..., Any]) -> None:
        self.path = path
        self.callback = callback

    def __repr__(self) -> str:
        return self.path

    def __getattribute__(self, attribute: str) -> Any:
        try:
            return object.__getattribute__(self, attribute)
        except AttributeError:
            return JMXAPIPath(self.path + "." + attribute, self.callback)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.callback(self.path, *args, **kwargs)


class JMXAPI:
    """Access to JMX via the Joloika/REST API to obtain monitoring information
    from a running JVM."""

    def __init__(self, zc: zocalo.configuration.Configuration):
        if not zc.jmx:
            raise zocalo.ConfigurationError(
                "There are no JMX credentials configured in your environment"
            )
        self.url = (
            f"http://{zc.jmx['host']}:{zc.jmx['port']}/{zc.jmx['base_url']}/read/"
        )
        self._authstring = (
            "Basic "
            + base64.b64encode(
                zc.jmx["username"].encode("utf-8")
                + b":"
                + zc.jmx["password"].encode("utf-8")
            ).decode()
        )

    def __getattribute__(self, attribute: str) -> Any:
        try:
            return object.__getattribute__(self, attribute)
        except AttributeError:
            return JMXAPIPath(attribute, self._call)

    def _call(
        self, path: str, attribute: str | None = None, *args: Any, **kwargs: str
    ) -> Any:
        params = ",".join(key + "=" + value for key, value in kwargs.items())
        url = path + ":" + params
        if attribute:
            url = url + "/" + attribute
        return self._get(url)

    def _get(self, url: str) -> Any:
        complete_url = self.url + url
        req = urllib.request.Request(
            complete_url, headers={"Accept": "application/json"}
        )
        req.add_header("Authorization", self._authstring)
        handler = urllib.request.urlopen(req)
        returncode = handler.getcode()
        if returncode != 200:
            raise RuntimeError("JMX lookup returned HTTP code %d" % returncode)
        return json.load(handler)


if __name__ == "__main__":
    zc = zocalo.configuration.from_file()
    if "live" in zc.environments:
        zc.activate_environment("live")
    jmx = JMXAPI(zc)
    from pprint import pprint

    mem = jmx.java.lang(type="Memory")
    pprint(mem)
    consumers = jmx.org.apache.activemq(
        type="Broker", brokerName="localhost", attribute="TotalConsumerCount"
    )
    pprint(consumers)
    health = jmx.org.apache.activemq(
        type="Broker", brokerName="localhost", service="Health"
    )
    pprint(health)
    queuestats = jmx.org.apache.activemq(
        type="Broker",
        brokerName="localhost",
        destinationType="Queue",
        destinationName="zocalo.transient.controller",
        attribute="QueueSize",
    )
    pprint(queuestats)
