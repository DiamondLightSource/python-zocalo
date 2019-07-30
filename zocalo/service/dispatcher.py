from __future__ import absolute_import, division, print_function

import copy
import errno
import os
import timeit
import uuid

import workflows.recipe
from workflows.services.common_service import CommonService


class Dispatcher(CommonService):
    """Single point of contact service that takes in job meta-information
     (say, a data collection ID), a processing recipe, a list of recipes,
     or pointers to recipes stored elsewhere, and mangles these into something
     that can be processed by downstream services.
    """

    # Human readable service name
    _service_name = "Dispatcher"

    # Logger name
    _logger_name = "services.dispatcher"

    # Define a base path where your recipes are located (accessed with zocalo.go -r $recipename)
    _recipe_basepath = "/dls_sw/apps/zocalo/live/recipes"

    def filter_parse_recipe_object(self, message, parameters):
        """If a recipe is specified as either a string or data structure in the
        message then parse it into a recipe object. Otherwise create an empty
        recipe object."""
        if message.get("recipe"):
            try:
                message["recipe"] = workflows.recipe.Recipe(recipe=message["recipe"])
            except Exception as e:
                raise ValueError(
                    "Rejected message containing a custom recipe that caused parsing errors: %s"
                    % str(e)
                )
        else:
            message["recipe"] = workflows.recipe.Recipe()
        return message, parameters

    def filter_load_recipes_from_files(self, message, parameters):
        """Loads named recipes from central location and merges them into the recipe object"""
        for recipefile in message.get("load_named_recipes", []):
            try:
                with open(
                    os.path.join(self._recipe_basepath, recipefile + ".json"), "r"
                ) as rcp:
                    named_recipe = workflows.recipe.Recipe(recipe=rcp.read()).recipe
            except ValueError as e:
                raise ValueError("Error reading recipe '%s': %s", recipefile, str(e))
            except IOError as e:
                if e.errno == errno.ENOENT:
                    raise ValueError(
                        "Message references non-existing recipe '%s'", recipefile
                    )
                raise
            try:
                named_recipe.validate()
            except workflows.Error as e:
                raise ValueError(
                    "Named recipe %s failed validation. %s" % (recipefile, str(e))
                )
            message["recipe"].merge(named_recipe)
        return message, parameters

    def filter_apply_parameters(self, message, parameters):
        """Fill in any placeholders in the recipe of the form {name} using the
        parameters data structure"""
        message["recipe"].apply_parameters(parameters)
        return message, parameters

    # Put message filter functions in here and they will be run in order during filtering
    _message_filters = [
        filter_parse_recipe_object,
        filter_load_recipes_from_files,
        filter_apply_parameters,
    ]

    def hook_before_filtering(self, header, message, recipe_id):
        """Actions to be taken before message filtering"""
        pass

    def hook_before_dispatch(self, header, message, recipe_id, filtered_message, rw):
        """Actions to be taken just before dispatching message"""
        print(header)
        print(message)

    def initializing(self):
        """Subscribe to the processing_recipe queue. Received messages must be acknowledged."""
        # self._environment.get('live') can be used to distinguish live/test mode
        self.log.info("Dispatcher starting")

        if self._environment.get("live"):
            if self._logbook:
                try:
                    os.makedirs(self._logbook, 0o775)
                except OSError:
                    pass  # Ignore if exists
            # Reset _logbook to none if it is defined but directory was not made correctly
            if not os.access(self._logbook, os.R_OK | os.W_OK | os.X_OK):
                self.log.error("Logbook disabled: Can not write to location")
                self._logbook = None
        else:
            self.log.info("Logbook disabled: Not running in live mode")
            self._logbook = None

        self._transport.subscribe(
            "processing_recipe", self.process, acknowledgement=True
        )

    def process(self, header, message):
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
        # From here on add the global ID to all log messages
        with self.extend_log("recipe_ID", recipe_id):
            self.log.debug("Received processing request:\n" + str(message))
            self.log.debug("Received processing parameters:\n" + str(parameters))

            filtered_message = copy.deepcopy(message)
            filtered_parameters = copy.deepcopy(parameters)

            self.hook_before_filtering(header, message, recipe_id)

            # Apply all specified filters in order to message and parameters
            for f in self._message_filters:
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

            self.log.debug("Mangled processing request:\n" + str(filtered_message))
            self.log.debug(
                "Mangled processing parameters:\n" + str(filtered_parameters)
            )

            if not isinstance(message.get("recipe"), workflows.recipe.Recipe):
                self.log.error(
                    "Message contains no valid recipes or pointers to recipes"
                )
                self._transport.nack(header)
                return

            try:
                message["recipe"].validate()
            except workflows.Error as e:
                self.log.error(
                    "Recipe failed final validation step. %s", str(e), exc_info=True
                )
                self._transport.nack(header)
                return

            # Create the RecipeWrapper object
            rw = workflows.recipe.RecipeWrapper(
                environment={"ID": recipe_id},
                recipe=full_recipe,
                transport=self._transport,
            )

            # Conditionally acknowledge receipt of the message
            txn = self._transport.transaction_begin()
            self._transport.ack(header, transaction=txn)

            # Call another hook just before dispatching the message
            self.hook_before_dispatch(header, message, recipe_id, filtered_message, rw)

            rw.start(transaction=txn)

            # Commit transaction
            self._transport.transaction_commit(txn)
            self.log.info(
                "Processed incoming message in %.4f seconds",
                timeit.default_timer() - start_time,
            )
