import collections
import logging
import string
import uuid
import json
import os.path

from unittest import mock
from workflows.recipe import Recipe


CollectedTest = collections.namedtuple(
    "CollectedTest", "send, expect, timers, errors, quiet"
)


class SafeDict(dict):
    """A dictionary that returns undefined keys as {keyname}.
    This can be used to selectively replace variables in datastructures."""

    def __missing__(self, key):
        return "{" + key + "}"


class CommonSystemTest:
    """
    Base class for system tests for Zocalo,
    the Diamond Light Source data analysis framework.
    """

    uuid = "T-12345678-1234-1234-1234-1234567890ab"
    """A random unique identifier for tests. A new one will be generated on class
     initialization and for each invocation of a test function."""

    parameters = SafeDict()
    """Set of known test parameters. Generally only a unique test identifier,
     parameters['uuid'], will be set."""

    validation = False
    """Set to true when test functions are only called for validation rather than
     testing. Think of this as 'dummy_mode'."""

    development_mode = False
    """A flag to distinguish between testing the live system and testing the
     development system. This should be used only sparingly, after all tests
     should be as realistic as possible, but may be required in some places,
     eg. to decide where to load external files from."""

    log = logging.getLogger("dlstbx.system_test")
    """Common logger object."""

    def __init__(self, zc, dev_mode=False):
        """Constructor via which the development mode can be set."""
        self.development_mode = dev_mode
        self.rotate_uuid()
        self._zc = zc

    def get_recipe(self, recipe, load=True):
        """Load a recipe from file

        Kwargs:
            load(bool): Whether to load the json into a Recipe
        """
        recipe_path = self._zc.storage["zocalo.recipe_directory"]
        with open(os.path.join(recipe_path, f"{recipe}.json")) as fh:
            recipe = json.load(fh)
            if load:
                return Recipe(recipe)
            else:
                return recipe

    def rotate_uuid(self):
        """Generate a new unique ID for the test. Prepend 'T-' to a UUID to
        distinguish between IDs used in system tests and IDs used for live
        processing. This helps for example when interpreting logs, as system test
        messages will show up in isolation rather than as part of a processing
        pipeline."""
        self.uuid = "T-" + str(uuid.uuid4())

    def enumerate_test_functions(self):
        """Returns a list of (name, function) tuples for all declared test
        functions in the class."""
        return [
            (function, getattr(self, function))
            for function in dir(self)
            if function.startswith("test_")
        ]

    def validate(self):
        """Checks that all test functions parse correctly to pick up syntax errors.
        Does run test functions with disabled messaging functions."""
        # Replace messaging functions by mock constructs
        patch_functions = ["_add_timer", "_messaging"]
        original_functions = {(x, getattr(self, x)) for x in patch_functions}
        for x in patch_functions:
            setattr(self, x, mock.create_autospec(getattr(self, x)))
        self.validation = True
        try:
            for name, function in self.enumerate_test_functions():
                self.log.info("validating %s" % name)
                function()
                self.rotate_uuid()  # rotate uuid for next function
                self.log.info("OK")
        finally:
            # Restore messaging functions
            for name, function in original_functions:
                setattr(self, name, function)
            self.validation = False

    def collect_tests(self):
        """Runs all test functions and collects messaging information.
        Returns a dictionary of
          { testname: CollectedTest }
        with the namedtuple CollectedTest parameters initialised with arrays.
        """
        self.config = self._zc.storage["system_tests"]
        messages = {}
        for name, function in self.enumerate_test_functions():
            self.rotate_uuid()
            self.parameters["uuid"] = self.uuid

            def messaging(direction, **kwargs):
                if direction not in messages[name]._fields:
                    raise RuntimeError("Invalid messaging call (%s)" % str(direction))
                getattr(messages[name], direction).append(kwargs)

            def timer(**kwargs):
                messages[name].timers.append(kwargs)

            self._messaging = messaging
            self._add_timer = timer
            messages[name] = CollectedTest(
                send=[], expect=[], timers=[], errors=[], quiet=[]
            )
            try:
                function()
            except Exception:
                import traceback

                messages[name].errors.append(traceback.format_exc())
        return messages

    #
    # -- Functions for use within tests ----------------------------------------
    #

    def send_message(self, queue=None, topic=None, headers={}, message=""):
        """Use this function within tests to send messages to queues and topics."""
        assert queue or topic, "Message queue or topic destination required"

        # Inject the custom uuid into the message if its a recipe
        if isinstance(message, dict):
            if not message.get("parameters"):
                message["parameters"] = {}
            message["parameters"]["uuid"] = self.uuid

        self._messaging(
            "send", queue=queue, topic=topic, headers=headers, message=message
        )

    def expect_message(
        self, queue=None, topic=None, headers=None, message=None, min_wait=0, timeout=10
    ):
        """Use this function within tests to wait for messages to queues and topics."""
        assert queue or topic, "Message queue or topic destination required"
        assert (
            not queue or not topic
        ), "Can only expect message on queue or topic, not both"
        self._messaging(
            "expect",
            queue=queue,
            topic=topic,
            headers=headers,
            message=message,
            min_wait=min_wait,
            timeout=timeout,
        )

    def expect_recipe_message(
        self,
        recipe,
        recipe_path,
        recipe_pointer,
        headers=None,
        payload=None,
        min_wait=0,
        timeout=10,
        queue=None,
        topic=None,
        environment=None,
    ):
        """Use this function within tests to wait for recipe-wrapped messages."""
        assert recipe, "Recipe required"
        if not (queue or topic):
            assert recipe_pointer > 0, "Recipe-pointer required"
            assert recipe_pointer in recipe, "Given recipe-pointer %s invalid" % str(
                recipe_pointer
            )
            queue = recipe[recipe_pointer].get("queue")
            topic = recipe[recipe_pointer].get("topic")
            assert queue or topic, "Message queue or topic destination required"
        assert (
            not queue or not topic
        ), "Can only expect message on queue or topic, not both"
        if headers is None:
            headers = {"workflows-recipe": "True"}
        else:
            headers = headers.copy()
            headers["workflows-recipe"] = "True"
        if environment:

            class dictionary_contains:
                def __init__(self, d):
                    self.containsdict = d

                def __eq__(self, other):
                    return self.containsdict.items() <= other.items()

            environment = dictionary_contains(environment)
        else:
            environment = mock.ANY
        expected_message = {
            "payload": payload,
            "recipe": recipe,
            "recipe-path": recipe_path,
            "recipe-pointer": recipe_pointer,
            "environment": environment,
        }
        self._messaging(
            "expect",
            queue=queue,
            topic=topic,
            headers=headers,
            message=expected_message,
            min_wait=min_wait,
            timeout=timeout,
        )

    def expect_unreached_recipe_step(
        self, recipe, recipe_pointer, min_wait=3, queue=None, topic=None,
    ):
        """Use this function within tests to mark recipe steps as unreachable."""
        assert recipe, "Recipe required"
        if not (queue or topic):
            assert recipe_pointer > 0, "Recipe-pointer required"
            assert recipe_pointer in recipe, "Given recipe-pointer %s invalid" % str(
                recipe_pointer
            )
            queue = recipe[recipe_pointer].get("queue")
            topic = recipe[recipe_pointer].get("topic")
            assert queue or topic, "Message queue or topic destination required"
        assert (
            not queue or not topic
        ), "Can only expect message on queue or topic, not both"

        self._messaging(
            "quiet", queue=queue, topic=topic,
        )
        self._add_timer(at_time=min_wait)

    def timer_event(
        self, at_time=None, callback=None, args=None, kwargs=None, expect_return=...
    ):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        assert at_time, "need to specify time for event"
        assert callback, "need to specify callback function"
        self._add_timer(
            at_time=at_time,
            callback=callback,
            args=args,
            kwargs=kwargs,
            expect_return=expect_return,
        )

    def apply_parameters(self, item):
        """Recursively apply formatting to {item}s in a data structure, leaving
        undefined {item}s as they are.

        Examples:
          parameters = { 'x':'5' }
          recursively_replace_parameters( { '{x}': '{y}' } )
             => { '5': '{y}' }

          parameters = { 'y':'5' }
          recursively_replace_parameters( { '{x}': '{y}' } )
             => { '{x}': '5' }

          parameters = { 'x':'3', 'y':'5' }
          recursively_replace_parameters( { '{x}': '{y}' } )
             => { '3': '5' }
        """
        if isinstance(item, str):
            return string.Formatter().vformat(item, (), self.parameters)
        if isinstance(item, dict):
            return {
                self.apply_parameters(key): self.apply_parameters(value)
                for key, value in item.items()
            }
        if isinstance(item, tuple):
            return tuple(self.apply_parameters(list(item)))
        if isinstance(item, list):
            return [self.apply_parameters(x) for x in item]
        return item

    #
    # -- Internal house-keeping functions --------------------------------------
    #

    def _add_timer(self, *args, **kwargs):
        raise NotImplementedError("Test functions can not be run directly")

    def _messaging(self, *args, **kwargs):
        raise NotImplementedError("Test functions can not be run directly")
