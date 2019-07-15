from __future__ import absolute_import, division, print_function

import copy
import errno
import json
import os
import re
import time
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
    _recipe_basepath = None

    # Put message filter functions in here and they will be run in order during filtering
    _message_filters = []

    def before_filter(self):
        """Actions to be taken before message filtering"""
        pass

    def before_dispatch(self):
        """Actions to be taken just before dispatching message"""
        pass

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

    def record_to_logbook(self, uuid, header, original_message, message, recipewrap):
        basepath = os.path.join(self._logbook, time.strftime("%Y-%m"))
        clean_uuid = re.sub("[^a-z0-9A-Z\-]+", "", uuid, re.UNICODE)
        if not clean_uuid or len(clean_uuid) < 3:
            self.log.warning(
                "Message with non-conforming uuid %s not written to logbook", uuid
            )
            return
        try:
            os.makedirs(os.path.join(basepath, clean_uuid[:2]))
        except OSError:
            pass  # Ignore if exists
        try:
            log_entry = os.path.join(basepath, clean_uuid[:2], clean_uuid[2:])
            with open(log_entry, "w") as fh:
                fh.write("Incoming message header:\n")
                json.dump(
                    header,
                    fh,
                    sort_keys=True,
                    skipkeys=True,
                    default=str,
                    indent=2,
                    separators=(",", ": "),
                )
                fh.write("\n\nIncoming message body:\n")
                json.dump(
                    original_message,
                    fh,
                    sort_keys=True,
                    skipkeys=True,
                    default=str,
                    indent=2,
                    separators=(",", ": "),
                )
                fh.write("\n\nParsed message body:\n")
                json.dump(
                    message,
                    fh,
                    sort_keys=True,
                    skipkeys=True,
                    default=str,
                    indent=2,
                    separators=(",", ": "),
                )
                fh.write("\n\nRecipe object:\n")
                json.dump(
                    recipewrap.recipe.recipe,
                    fh,
                    sort_keys=True,
                    skipkeys=True,
                    default=str,
                    indent=2,
                    separators=(",", ": "),
                )
                fh.write("\n")
            self.log.debug("Message saved in logbook at %s", log_entry)
        except Exception:
            self.log.warning("Could not write message to logbook", exc_info=True)

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

        # If we are fully logging requests then make a copy of the original message
        if self._logbook:
            original_message = copy.deepcopy(message)

        # From here on add the global ID to all log messages
        with self.extend_log("recipe_ID", recipe_id):
            self.log.debug("Received processing request:\n" + str(message))
            self.log.debug("Received processing parameters:\n" + str(parameters))

            try:
                # Calls the defined filters
                for filter in self._message_filters:
                    message, parameters = filter(message, parameters)
            except Exception as e:
                self.log.error(
                    "Rejected message due to filter error: %s", str(e), exc_info=True
                )
                self._transport.nack(header)
                return
            self.log.debug("Mangled processing request:\n" + str(message))
            self.log.debug("Mangled processing parameters:\n" + str(parameters))

            # Process message
            recipes = []
            if message.get("custom_recipe"):
                try:
                    recipes.append(
                        workflows.recipe.Recipe(
                            recipe=json.dumps(message["custom_recipe"])
                        )
                    )
                except Exception as e:
                    self.log.error(
                        "Rejected message containing a custom recipe that caused parsing errors: %s",
                        str(e),
                        exc_info=True,
                    )
                    self._transport.nack(header)
                    return
            if message.get("recipes"):
                for recipefile in message["recipes"]:
                    try:
                        with open(
                            os.path.join(self._recipe_basepath, recipefile + ".json"),
                            "r",
                        ) as rcp:
                            recipes.append(workflows.recipe.Recipe(recipe=rcp.read()))
                    except ValueError as e:
                        self.log.error(
                            "Error reading recipe '%s': %s", recipefile, str(e)
                        )
                        self._transport.nack(header)
                        return
                    except IOError as e:
                        if e.errno == errno.ENOENT:
                            self.log.error(
                                "Message references non-existing recipe '%s'",
                                recipefile,
                            )
                            self._transport.nack(header)
                            return
                        raise

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
                recipe.apply_parameters(parameters)
                full_recipe = full_recipe.merge(recipe)

            # Conditionally acknowledge receipt of the message
            txn = self._transport.transaction_begin()
            self._transport.ack(header, transaction=txn)

            rw = workflows.recipe.RecipeWrapper(
                environment={"ID": recipe_id},
                recipe=full_recipe,
                transport=self._transport,
            )
            rw.start(transaction=txn)

            # Write information to logbook if applicable
            if self._logbook:
                self.record_to_logbook(recipe_id, header, original_message, message, rw)

            # Commit transaction
            self._transport.transaction_commit(txn)
            self.log.info(
                "Processed incoming message in %.4f seconds",
                timeit.default_timer() - start_time,
            )
