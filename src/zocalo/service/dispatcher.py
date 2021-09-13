import copy
import errno
import os
import timeit
import uuid
import pkg_resources

from pprint import pformat

import workflows.recipe
from workflows.services.common_service import CommonService


class Dispatcher(CommonService):
    """
    Single point of contact service that takes in job meta-information
    (say, a data collection ID), a processing recipe, a list of recipes,
    or pointers to recipes stored elsewhere, and mangles these into something
    that can be processed by downstream services.
    """

    # Human readable service name
    _service_name = "Dispatcher"

    # Logger name
    _logger_name = "services.dispatcher"

    # Define a base path where your recipes are located (accessed with zocalo.go -r $recipename)
    recipe_basepath = None

    def filter_load_recipes_from_files(self, message, parameters):
        """Loads named recipes from central location and merges them into the recipe object"""
        for recipefile in message.get("recipes", []):
            try:
                with open(
                    os.path.join(self.recipe_basepath, recipefile + ".json"), "r"
                ) as rcp:
                    named_recipe = workflows.recipe.Recipe(recipe=rcp.read())
            except ValueError as e:
                raise ValueError("Error reading recipe '%s': %s", recipefile, str(e))
            except IOError as e:
                if e.errno == errno.ENOENT:
                    raise ValueError(
                        f"Message references non-existing recipe {recipefile}. Recipe path is {self.recipe_basepath}",
                    )
                raise
            try:
                named_recipe.validate()
            except workflows.Error as e:
                raise ValueError(
                    "Named recipe %s failed validation. %s" % (recipefile, str(e))
                )
            named_recipe.apply_parameters(parameters)
            message["recipe"] = message["recipe"].merge(named_recipe)
        return message, parameters

    def filter_apply_parameters(self, message, parameters):
        """Fill in any placeholders in the recipe of the form {name} using the
        parameters data structure"""
        message["recipe"].apply_parameters(parameters)
        return message, parameters

    def hook_before_filtering(self, header, message, parameters, recipe_id):
        """Actions to be taken before message filtering

        If this function returns false then processing of this message
        will stop
        """
        return_code = True
        for entry in pkg_resources.iter_entry_points(
            "zocalo.dispatcher.hooks_before_filtering"
        ):
            fn = entry.load()
            val = fn(header, message, parameters, recipe_id, self.transport, self.log)
            if not val:
                return_code = False

        return return_code

    def hook_before_dispatch(
        self, header, message, parameters, recipe_id, filtered_message, rw,
    ):
        """Actions to be taken just before dispatching message

        If this function returns false then processing of this message
        will stop
        """
        return_code = True
        for entry in pkg_resources.iter_entry_points(
            "zocalo.dispatcher.hooks_before_dispatch"
        ):
            fn = entry.load()
            val = fn(
                header,
                message,
                parameters,
                recipe_id,
                filtered_message,
                rw,
                self.transport,
                self.log,
            )
            if not val:
                return_code = False

        return return_code

    def initializing(self):
        """Subscribe to the processing_recipe queue. Received messages must be acknowledged."""
        # self._environment.get('live') can be used to distinguish live/test modes
        self.recipe_basepath = self.config.storage["recipe_path"]

        self.log.info("Dispatcher starting")

        workflows.recipe.wrap_subscribe(
            self._transport,
            "processing_recipe",
            self.process,
            acknowledgement=True,
            log_extender=self.extend_log,
            allow_non_recipe_messages=True,
        )

    def process(self, rw, header, message):
        """Process an incoming processing request."""
        # Time execution
        start_time = timeit.default_timer()

        # Load processing parameters
        parameters = message.get("parameters", {})
        if not isinstance(parameters, dict):
            # malformed message
            self.log.warning(
                "Dispatcher rejected malformed message: parameters not given as dictionary"
            )
            self._transport.nack(header)
            return

        # Unless 'uuid' is already defined then generate a unique recipe IDs for
        # this request, which is attached to all downstream log records and can
        # be used to determine unique file paths.
        recipe_id = parameters.get("uuid") or str(uuid.uuid4())
        parameters["uuid"] = recipe_id

        if rw:
            # If we received a recipe wrapper then we already have a recipe_ID
            # attached to logs. Make a note of the downstream recipe ID so that
            # we can track execution beyond recipe boundaries.
            self.log.info(
                "Processing request with new recipe ID %s:\n%s", recipe_id, str(message)
            )

        # From here on add the global ID to all log messages
        with self.extend_log("recipe_ID", recipe_id):
            self.log.debug("Received processing request:\n" + str(message))
            self.log.debug("Received processing parameters:\n" + str(parameters))

            filtered_message = copy.deepcopy(message)
            filtered_parameters = copy.deepcopy(parameters)

            # Call a hook before processing the message
            if not self.hook_before_filtering(header, message, parameters, recipe_id):
                return

            # Create empty recipe
            filtered_message["recipe"] = workflows.recipe.Recipe()

            # Apply all specified filters in order to message and parameters
            message_filters = [
                f.load()
                for f in pkg_resources.iter_entry_points("zocalo.dispatcher.filters")
            ] + [self.filter_load_recipes_from_files, self.filter_apply_parameters]

            for f in message_filters:
                try:
                    filtered_message, filtered_parameters = f(
                        filtered_message, filtered_parameters
                    )
                except Exception as e:
                    self.log.error(
                        "Rejected message due to filter error: %s",
                        str(e),
                        exc_info=True,
                    )
                    self._transport.nack(header)
                    return

            self.log.debug("Mangled processing request:\n" + pformat(filtered_message))
            self.log.debug(
                "Mangled processing parameters:\n" + pformat(filtered_parameters)
            )

            # Create the RecipeWrapper object
            rw = workflows.recipe.RecipeWrapper(
                environment={"ID": recipe_id},
                recipe=filtered_message["recipe"],
                transport=self._transport,
            )

            # Conditionally acknowledge receipt of the message
            txn = self._transport.transaction_begin()
            self._transport.ack(header, transaction=txn)

            # Call another hook just before dispatching the message
            if not self.hook_before_dispatch(
                header, message, parameters, recipe_id, filtered_message, rw,
            ):
                return

            rw.start(transaction=txn)

            # Commit transaction
            self._transport.transaction_commit(txn)
            self.log.info(
                "Processed incoming message in %.4f seconds",
                timeit.default_timer() - start_time,
            )
