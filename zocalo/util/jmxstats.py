#
# simple API to obtain JMX information
#
# Point to a configuration file to use it, eg:
#  jmx = JMXAPI('/dls_sw/apps/zocalo/secrets/credentials-jmx-access.cfg')
# Then can access objects with eg.
#  jmx.java.lang(type="Memory")
#  jmx.org.apache.activemq(type="Broker", brokerName="localhost/TotalConsumerCount")


import base64
import json

from six.moves import configparser
from six.moves import urllib


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

    def __init__(
        self, configfile="/dls_sw/apps/zocalo/secrets/credentials-jmx-access.cfg"
    ):
        cfgparser = configparser.ConfigParser(allow_no_value=True)
        if not cfgparser.read(configfile):
            raise RuntimeError("Could not read from configuration file %s" % configfile)
        host = cfgparser.get("jmx", "host")
        port = cfgparser.get("jmx", "port")
        base = cfgparser.get("jmx", "baseurl")
        self.url = "http://{host}:{port}/{baseurl}/read/".format(
            host=host, port=port, baseurl=base
        )
        self.authstring = b"Basic " + base64.b64encode(
            cfgparser.get("jmx", "username").encode("utf-8")
            + b":"
            + cfgparser.get("jmx", "password").encode("utf-8")
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
