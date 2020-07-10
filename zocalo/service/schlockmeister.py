import collections
import uuid

from workflows.services.common_service import CommonService

TRACE_LOGLEVEL = 5
# a log level below debug if anyone is interested in the really-low-level spam


class Schlockmeister(CommonService):
    """
    Remove too-often-redelivered messages from the queues.

    When a message is redelivered this can have innocuous reasons, for example
    when it was processed by a service that got killed by the user, or there
    was a temporary network glitch, or anything along those lines.
    In other cases the message may cause services to die without them catching
    the error. Schlockmeister subscribes to all queues and picks out messages
    that get redelivered too often and tells the broker to quarantine them.
    Redelivered messages may not be the cause of the issue, because messages
    can be prefetched by a client, which then dies for an unrelated reason,
    causing the messages to be redelivered. For this reason the redelivery
    limit is set rather high.
    The implementation is ActiveMQ specific.

    schlockmeister, n.
    a person who deals in or sells inferior or worthless goods; junk dealer.
    """

    # Human readable service name
    _service_name = "Schlockmeister"

    # Logger name
    _logger_name = "zocalo.service.schlockmeister"

    known_queues = {}
    known_consumers = {}
    known_instances = set()

    def initializing(self):
        """
        Subscribe to all queues. Received messages must be acknowledged.
        Only receive messages that have been delivered 5 times in the past.
        Get messages without pre-processing, as this may have caused the crash.
        """

        self.log.info("Collecting broker information")

        # Generate a unique ID in order to identify myself and other instances of
        # myself in the list of active subscribers/consumers
        self.uuid = str(uuid.uuid4())

        # Listen to a specific queue in the namespace. There will be no messages
        # in that queue. It only acts as a marker to identify service instances.
        self._markerqueue = "transient.schlockmeister." + self.uuid
        self._transport.subscribe(self._markerqueue, self.ignore, disable_mangling=True)

        # Look through list of all subscriptions to identify the subscription that
        # was just set up. From this we can infer the relevant namespace.
        self._namespace = None
        self._subid_watch_global = self._transport.subscribe_broadcast(
            "ActiveMQ.Advisory.Consumer.Queue.>",
            self.watch_global,
            ignore_namespace=True,
        )

        # Add a fallback in case the namespace could not be determined.
        self._register_idle(90, self._namespace_determination_failure)

    @staticmethod
    def ignore(header, message):
        """Ignore any messages on this subscription."""

    def _namespace_determination_failure(self):
        """Report namespace determination failure."""
        self.log.error(
            "Could not determine namespace within allocated time. Shutting down."
        )
        self._shutdown()

    def watch_global(self, header, message):
        """
        Received information on one existing queue subscription.
        Try to identify the relevant transport namespace.
        """
        if self._namespace or not isinstance(message, dict):
            return
        if self._markerqueue in message.get("ConsumerInfo", {}).get(
            "destination", {}
        ).get("string", ""):
            self._namespace = message["ConsumerInfo"]["destination"]["string"][
                : -len(self._markerqueue)
            ]
            self.log.info("Identified namespace as '%s'", self._namespace)

            # With the namespace now identified, can drop the global subscription watch and look only at relevant queues
            self._transport.unsubscribe(self._subid_watch_global)

            # Disable fallback function. Enable garbage collection instead.
            self._register_idle(15, self.garbage_collect)

            self._transport.subscribe_broadcast(
                "ActiveMQ.Advisory.Consumer.Queue.%s>" % self._namespace,
                self.watch_local,
                ignore_namespace=True,
            )

    def watch_local(self, header, message):
        """Keep track of queue consumers to identify active queues and topics."""
        if not isinstance(message, dict):
            return

        if "ConsumerInfo" in message:
            destination = message["ConsumerInfo"]["destination"]["string"]
            if not destination.startswith(self._namespace):
                self.log.warning(
                    "Subscription to %s detected, which is not within namespace",
                    self._namespace,
                )
                return
            destination = destination.replace(self._namespace, "")

            subscriber = message["ConsumerInfo"]["consumerId"]["connectionId"]

            consumer_triple = (
                subscriber,
                message["ConsumerInfo"]["consumerId"]["sessionId"],
                message["ConsumerInfo"]["consumerId"]["value"],
            )
            if consumer_triple in self.known_consumers:
                self.log.error(
                    "Consumer triple %s has already been seen!", str(consumer_triple)
                )
            self.known_consumers[consumer_triple] = destination

            self.log.log(
                TRACE_LOGLEVEL, "Seen new subscriber %s to %s", subscriber, destination
            )
            if destination not in self.known_queues:
                self.known_queues[destination] = {"subscribers": collections.Counter()}
            self.known_queues[destination]["subscribers"].update({subscriber: 1})

            if destination.startswith("transient.schlockmeister."):
                self.log.info("Ignoring subscriptions by client %s", subscriber)
                self.known_instances.add(subscriber)
        elif "RemoveInfo" in message:
            subscriber = message["RemoveInfo"]["objectId"]["connectionId"]
            consumer_triple = (
                subscriber,
                message["RemoveInfo"]["objectId"]["sessionId"],
                message["RemoveInfo"]["objectId"]["value"],
            )
            if consumer_triple not in self.known_consumers:
                self.log.error(
                    "Consumer triple %s unknown for removal!", str(consumer_triple)
                )
                return
            destination = self.known_consumers[consumer_triple]
            del self.known_consumers[consumer_triple]

            if destination not in self.known_queues:
                self.log.error("Queue %s unknown for removal", destination)
            self.log.log(
                TRACE_LOGLEVEL, "Seen subscriber %s leaving %s", subscriber, destination
            )
            self.known_queues[destination]["subscribers"].update({subscriber: -1})
            if self.known_queues[destination]["subscribers"][subscriber] == 0:
                del self.known_queues[destination]["subscribers"][subscriber]
        else:
            self.log.warning("Received unknown message type\n%s", str(message))
        self.update_subscriptions()

    def update_subscriptions(self):
        """Subscribe to any new queues with real subscribers."""
        for destination in self.known_queues:
            if self.known_queues[destination].get("subscription"):
                continue
            real_subscriber_count = sum(
                map(
                    lambda k: k not in self.known_instances,
                    self.known_queues[destination]["subscribers"],
                )
            )
            if real_subscriber_count:
                self.log.debug("subscribing to %s", destination)
                self.known_queues[destination][
                    "subscription"
                ] = self._transport.subscribe(
                    destination,
                    self.quarantine,
                    acknowledgement=True,
                    selector="JMSXDeliveryCount>5",
                    disable_mangling=True,
                )

    def garbage_collect(self):
        """
        Delayed unsubscribe from lists that are without other subscribers.
        Clean up list of known queues.
        """
        queues = list(self.known_queues)
        for destination in queues:
            if self.known_queues[destination].get("subscription"):
                real_subscriber_count = sum(
                    map(
                        lambda k: k not in self.known_instances,
                        self.known_queues[destination]["subscribers"],
                    )
                )
                if not real_subscriber_count:
                    self.log.debug("unsubscribing from %s", destination)
                    self._transport.unsubscribe(
                        self.known_queues[destination]["subscription"]
                    )
                    del self.known_queues[destination]["subscription"]
            if len(self.known_queues[destination]) == 1 and not any(
                self.known_queues[destination]["subscribers"]
            ):
                del self.known_queues[destination]
                self.log.debug(
                    "collecting stale queue %s, leaving %d queues, %d consumers, %d peers",
                    destination,
                    len(self.known_queues),
                    len(self.known_consumers),
                    len(self.known_instances) - 1,
                )

    def quarantine(self, header, message):
        """Quarantine this message."""

        self.log.warning(
            "Schlockmeister has found a potentially bad message.\n"
            + "First 1000 characters of header:\n%s\n"
            + "First 1000 characters of message:\n%s",
            str(header)[:1000],
            str(message)[:1000],
        )

        # The actual quarantining magic happens on the broker
        self._transport.nack(header)
