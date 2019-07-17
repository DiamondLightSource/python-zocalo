from __future__ import absolute_import, division, print_function

import copy
import errno
import json
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

    def recipe_lookup_filter(message, parameters):
        """Takes defined recipes, reads them and appends to the raw_recipes list"""
        # Define a base path where your recipes are located (accessed with zocalo.go -r $recipename)
        recipe_basepath = "/dls_sw/apps/zocalo/live/recipes"
        for recipefile in message["recipes"]:
            try:
                with open(
                    os.path.join(recipe_basepath, recipefile + ".json"), "r"
                ) as rcp:
                    message["raw_recipes"].append(
                        workflows.recipe.Recipe(recipe=rcp.read()).recipe
                    )
            except ValueError as e:
                raise ValueError("Error reading recipe '%s': %s", recipefile, str(e))
            except IOError as e:
                if e.errno == errno.ENOENT:
                    raise Exception(
                        "Message references non-existing recipe '%s'", recipefile
                    )
                raise e

        return message, parameters

    # Put message filter functions in here and they will be run in order during filtering
    _message_filters = [recipe_lookup_filter]

    def before_filter(self, header, message, recipe_id):
        """Actions to be taken before message filtering"""
        pass

    def before_dispatch(self, header, message, recipe_id, filtered_message, rw):
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

        # Unless 'guid' is already defined then generate a unique recipe IDs for
        # this request, which is attached to all downstream log records and can
        # be used to determine unique file paths.
        recipe_id = parameters.get("uuid") or str(uuid.uuid4())
        parameters["uuid"] = recipe_id

        self.before_filter(header, message, recipe_id)

        # From here on add the global ID to all log messages
        with self.extend_log("recipe_ID", recipe_id):
            self.log.debug("Received processing request:\n" + str(message))
            self.log.debug("Received processing parameters:\n" + str(parameters))

            try:
                # Set up new variables to filter on
                filtered_message = copy.deepcopy(message)
                filtered_parameters = copy.deepcopy(parameters)
                # Calls the defined filters
                for filter in self._message_filters:
                    try:
                        filtered_message, filtered_parameters = filter(
                            filtered_message, filtered_parameters
                        )
                    except Exception as e:
                        self._transport.nack(header)
                        self.log.exception(e)
                        return
            except Exception as e:
                self.log.error(
                    "Rejected message due to filter error: %s", str(e), exc_info=True
                )
                self._transport.nack(header)
                return
            self.log.debug("Mangled processing request:\n" + str(filtered_message))
            self.log.debug(
                "Mangled processing parameters:\n" + str(filtered_parameters)
            )

            # Extract recipes
            recipes = []
            for recipe in filtered_message.get("raw_recipes"):
                try:
                    recipes.append(workflows.recipe.Recipe(recipe=json.dumps(recipe)))
                except Exception as e:
                    self.log.error(
                        "Rejected message containing a custom recipe that caused parsing errors: %s",
                        str(e),
                        exc_info=True,
                    )
                    self._transport.nack(header)
                    return

            print(recipes)

            if not recipes:
                self.log.error(
                    "Message contains no valid recipes or pointers to recipes"
                )
                self._transport.nack(header)
                return

            full_recipe = workflows.recipe.Recipe()
            for recipe in recipes:
                try:
                    recipe.validate()
                except workflows.Error as e:
                    self.log.error(
                        "Recipe failed validation. %s", str(e), exc_info=True
                    )
                    self._transport.nack(header)
                    return
                recipe.apply_parameters(filtered_parameters)
                full_recipe = full_recipe.merge(recipe)

            # Conditionally acknowledge receipt of the message
            txn = self._transport.transaction_begin()
            self._transport.ack(header, transaction=txn)

            rw = workflows.recipe.RecipeWrapper(
                environment={"ID": recipe_id},
                recipe=full_recipe,
                transport=self._transport,
            )

            self.before_dispatch(header, message, recipe_id, filtered_message, rw)

            rw.start(transaction=txn)

            # Commit transaction
            self._transport.transaction_commit(txn)
            self.log.info(
                "Processed incoming message in %.4f seconds",
                timeit.default_timer() - start_time,
            )
