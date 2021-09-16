import collections
import argparse
import logging
import sys
import time
import pkg_resources
import operator

import junit_xml
from workflows.transport.stomp_transport import StompTransport

import zocalo.configuration

from zocalo.system_test.result import Result

logger = logging.getLogger(__name__)

stomp_logger = logging.getLogger("stomp.py")
stomp_logger.setLevel(logging.WARNING)

TimerEvent = collections.namedtuple(
    "TimerEvent", "time, callback, expected_result, result_object"
)


def run():
    if "--debug" in sys.argv:
        level = logging.DEBUG
        stomp_logger.setLevel(logging.DEBUG)
    else:
        level = logging.INFO
    logging.basicConfig(level=level)

    parser = argparse.ArgumentParser(description="Zocalo system tests")
    parser.add_argument(
        "-c", dest="classes", help="Filter tests to specific classes",
    )
    parser.add_argument(
        "-k", dest="functions", help="Filter tests to specific functions",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug output",
    )

    zc = zocalo.configuration.from_file()
    envs = zc.activate()
    zc.add_command_line_options(parser)

    try:
        zc.storage["system_tests"]
    except KeyError:
        raise AttributeError("Zocalo configuration `storage` plugin does not contain a `system_tests` key")

    args = parser.parse_args()

    test_mode = False
    if "test" in envs:
        logger.info("Running on test configuration")
        test_mode = True

    transport = StompTransport()
    transport.connect()
    if not transport.is_connected():
        logger.critical("Could not connect to ActiveMQ server")
        sys.exit(1)

    # Load system tests
    systest_classes = {}
    for entry in pkg_resources.iter_entry_points("zocalo.system_tests"):
        cls = entry.load()
        systest_classes[cls.__name__] = cls

    systest_count = len(systest_classes)
    logger.info("Found %d system test classes" % systest_count)

    if args.classes and systest_count:
        systest_classes = {
            n: cls
            for n, cls in systest_classes.items()
            if any(n.lower().startswith(v.lower()) for v in [args.classes])
        }
        logger.info(
            "Filtered %d classes via command line arguments"
            % (systest_count - len(systest_classes))
        )
        systest_count = len(systest_classes)

    tests = {}
    count = 0
    collection_errors = False
    for classname, cls in systest_classes.items():
        logger.debug("Collecting tests from %s" % classname)
        for testname, testsetting in cls(zc=zc, dev_mode=test_mode).collect_tests().items():
            count += 1
            if (args.functions and testname == args.functions) or not args.functions:
                testresult = Result()
                testresult.set_name(testname)
                testresult.set_classname(classname)
                testresult.early = 0
                if testsetting.errors:
                    testresult.log_trace("\n".join(testsetting.errors))
                    logger.error(
                        "Error reading test %s:\n%s",
                        testname,
                        "\n".join(testsetting.errors),
                    )
                    collection_errors = True
                tests[(classname, testname)] = (testsetting, testresult)
    logger.info("Found %d system tests" % count)
    logger.info(
        "Filtered %d system tests via command line arguments" % (count - len(tests))
    )
    if collection_errors:
        sys.exit("Errors during test collection")

    # Set up subscriptions
    start_time = time.time()  # This is updated after sending all messages

    channels = collections.defaultdict(list)
    for test, _ in tests.values():
        for expectation in test.expect:
            channels[(expectation["queue"], expectation["topic"])].append(expectation)
        for expectation in test.quiet:
            channels[(expectation["queue"], expectation["topic"])].extend([])

    channel_lookup = {}

    unexpected_messages = Result()
    unexpected_messages.set_name("received_no_unexpected_messages")
    unexpected_messages.set_classname(".")
    unexpected_messages.count = 0

    def handle_receipt(header, message):
        expected_messages = channels[channel_lookup[header["subscription"]]]
        for expected_message in expected_messages:
            if not expected_message.get("received"):
                if expected_message["message"] == message:
                    if expected_message.get("headers"):
                        headers_match = True
                        for parameter, value in expected_message["headers"].items():
                            if value != header.get(parameter):
                                headers_match = False
                        if not headers_match:
                            logger.warning(
                                "Received a message similar to an expected message:\n"
                                + str(message)
                                + "\n but its header\n"
                                + str(header)
                                + "\ndoes not match the expected header:\n"
                                + str(expected_message["headers"])
                            )
                            continue
                    if (
                        expected_message.get("min_wait")
                        and (time.time() - start_time) < expected_message["min_wait"]
                    ):
                        expected_message["early"] = (
                            "Received expected message:\n"
                            + str(header)
                            + "\n"
                            + str(message)
                            + "\n%.1f seconds too early."
                            % (expected_message["min_wait"] + start_time - time.time())
                        )
                        logger.warning(expected_message["early"])
                    expected_message["received"] = True
                    logger.debug(
                        "Received expected message:\n"
                        + str(header)
                        + "\n"
                        + str(message)
                        + "\n"
                    )
                    return
        logger.warning(
            "Received unexpected message:\n"
            + str(header)
            + "\n"
            + str(message)
            + "\n which is not in \n"
            + str(expected_messages)
            + "\n"
        )
        unexpected_messages.log_error(
            message="Received unexpected message",
            output=str(header) + "\n" + str(message) + "\n",
        )
        unexpected_messages.count += 1

    for n, (queue, topic) in enumerate(channels.keys()):
        logger.debug("%2d: Subscribing to %s" % (n + 1, queue))
        if queue:
            sub_id = transport.subscribe(queue, handle_receipt)
        if topic:
            sub_id = transport.subscribe_broadcast(topic, handle_receipt)
        channel_lookup[str(sub_id)] = (queue, topic)
        # subscriptions may be expensive on the server side, so apply some rate limiting
        # so that the server can catch up and replies on this connection are not unduly
        # delayed
        time.sleep(0.3)
    delay = 0.1 * len(channels) + 0.007 * len(channels) * len(channels)
    logger.debug(f"Waiting {delay:.1f} seconds...")
    time.sleep(delay)

    # Send out messages
    for test, _ in tests.values():
        for message in test.send:
            if message.get("queue"):
                logger.debug("Sending message to %s", message["queue"])
                transport.send(
                    message["queue"],
                    message["message"],
                    headers=message["headers"],
                    persistent=False,
                )
            if message.get("topic"):
                logger.debug("Broadcasting message to %s", message["topic"])
                transport.broadcast(
                    message["topic"], message["message"], headers=message["headers"]
                )

    # Prepare timer events
    start_time = time.time()

    timer_events = []
    for test, result in tests.values():
        for event in test.timers:
            event["at_time"] = event["at_time"] + start_time
            function = event.get("callback")
            if function:
                args = event.get("args", ())
                kwargs = event.get("kwargs", {})
                timer_events.append(
                    TimerEvent(
                        time=event["at_time"],
                        result_object=result,
                        callback=lambda function=function: function(*args, **kwargs),
                        expected_result=event.get("expect_return", Ellipsis),
                    )
                )
            else:
                timer_events.append(
                    TimerEvent(
                        time=event["at_time"],
                        result_object=result,
                        callback=lambda: None,
                        expected_result=Ellipsis,
                    )
                )
    timer_events = sorted(timer_events, key=operator.attrgetter("time"))

    # Wait for messages and timeouts, run events
    keep_waiting = True
    last_message = time.time()
    while keep_waiting:

        # Wait fixed time period or until next event
        wait_to = time.time() + 0.2
        keep_waiting = False
        while timer_events and time.time() > timer_events[0].time:
            event = timer_events.pop(0)
            event_result = event.callback()
            if event.expected_result is not Ellipsis:
                if event.expected_result != event_result:
                    logger.warning(
                        f"{event.result_object.classname} timer event failed for {event.result_object.name}: return value '{event_result}' does not match '{event.expected_result}'"
                    )
                    event.result_object.log_error(
                        message="Timer event failed with result '%s' instead of expected '%s'"
                        % (event_result, event.expected_result)
                    )
        if timer_events:
            wait_to = min(wait_to, timer_events[0][0])
            keep_waiting = True
        if time.time() > last_message + 5:
            logger.info("Waited %5.1fs." % (time.time() - start_time))
            last_message = time.time()
        time.sleep(max(0.01, wait_to - time.time()))

        for testname, test in tests.items():
            for expectation in test[0].expect:
                if not expectation.get("received") and not expectation.get(
                    "received_timeout"
                ):
                    if time.time() > start_time + expectation["timeout"]:
                        expectation["received_timeout"] = True
                        logger.warning(
                            "Test %s.%s timed out waiting for message\n%s"
                            % (testname[0], testname[1], str(expectation))
                        )
                        test[1].log_error(
                            message="No answer received within time limit.",
                            output=str(expectation),
                        )
                    else:
                        keep_waiting = True

    for testname, test in tests.items():
        for expectation in test[0].expect:
            if expectation.get("early"):
                test[1].log_error(
                    message="Answer received too early.", output=str(expectation)
                )
                test[1].early += 1

    # Export results
    ts = junit_xml.TestSuite(
        "zocalo.system_test", [r for _, r in tests.values()] + [unexpected_messages]
    )
    with open("output.xml", "w") as f:
        junit_xml.to_xml_report_file(f, [ts], prettyprint=True)

    successes = sum(r.is_success() for _, r in tests.values())
    logger.info(
        "System test run completed, %d of %d tests succeeded." % (successes, len(tests))
    )
    for a, b in tests.values():
        if not b.is_success():
            if b.is_failure() and b.failure_output:
                logger.error(
                    "  %s %s failed:\n    %s",
                    b.classname,
                    b.name,
                    b.failure_output.replace("\n", "\n    "),
                )
            else:
                logger.warning(
                    "  %s %s received %d out of %d expected replies %s"
                    % (
                        b.classname,
                        b.name,
                        len([x for x in a.expect if x.get("received")]),
                        len(a.expect),
                        "(%d early)" % b.early if b.early else "",
                    )
                )
    if unexpected_messages.count:
        logger.error(
            "  Received %d unexpected message%s."
            % (unexpected_messages.count, "" if unexpected_messages.count == 1 else "s")
        )
