#
# simple API to obtain JMX information
#
# Then can access objects with eg.
#  jmx.java.lang(type="Memory")
#  jmx.org.apache.activemq(type="Broker", brokerName="localhost/TotalConsumerCount")
import base64
import json
import urllib.request

from zocalo.configuration import config


class JMXAPIPath:
    """A recursing helper object that encodes a JMX bean path."""

    def __init__(self, path, callback):
        self.path = path
        self.callback = callback

    def __repr__(self):
        return self.path

    def __getattribute__(self, attribute):
        try:
            return object.__getattribute__(self, attribute)
        except AttributeError:
            return JMXAPIPath(self.path + "." + attribute, self.callback)

    def __call__(self, *args, **kwargs):
        return self.callback(self.path, *args, **kwargs)


class JMXAPI:
    """Access to JMX via the Joloika/REST API to obtain monitoring information
     from a running JVM."""

    def __init__(self):
        jmx_config = config.get_plugin("jmx", env=None)
        self.url = f"http://{jmx_config['host']}:{jmx_config['port']}/{jmx_config['base_url']}/read/"
        self.authstring = b"Basic " + base64.b64encode(
            jmx_config.get("username").encode("utf-8")
            + b":"
            + jmx_config.get("password").encode("utf-8")
        )

    def __getattribute__(self, attribute):
        try:
            return object.__getattribute__(self, attribute)
        except AttributeError:
            return JMXAPIPath(attribute, self._call)

    def _call(self, path, attribute=None, *args, **kwargs):
        params = ",".join(key + "=" + value for key, value in kwargs.items())
        url = path + ":" + params
        if attribute:
            url = url + "/" + attribute
        return self._get(url)

    def _get(self, url):
        complete_url = self.url + url
        req = urllib.request.Request(
            complete_url, headers={"Accept": "application/json"}
        )
        req.add_header("Authorization", self.authstring)
        handler = urllib.request.urlopen(req)
        returncode = handler.getcode()
        if returncode != 200:
            raise RuntimeError("JMX lookup returned HTTP code %d" % returncode)
        return json.load(handler)


if __name__ == "__main__":
    jmx = JMXAPI()
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
