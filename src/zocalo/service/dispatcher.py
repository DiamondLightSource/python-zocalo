from __future__ import annotations

import copy
import errno
import json
import os
import re
import time
import timeit
import uuid

import pkg_resources
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
    _logger_name = "zocalo.service.dispatcher"

    def filter_load_recipes_from_files(self, message, parameters):
        """Load named recipes from central location and merge them into the recipe object"""
        for recipefile in message.get("recipes", []):
            try:
                with open(
                    os.path.join(self.recipe_basepath, recipefile + ".json"), "r"
                ) as rcp:
                    named_recipe = workflows.recipe.Recipe(recipe=rcp.read())
            except ValueError:
                raise ValueError(f"Error reading recipe {recipefile}")
            except IOError as e:
                if e.errno == errno.ENOENT:
                    raise ValueError(
                        f"Message references non-existing recipe {recipefile}. Recipe path is {self.recipe_basepath}",
                    )
                raise
            try:
                named_recipe.validate()
            except workflows.Error as e:
                raise ValueError(f"Named recipe {recipefile} failed validation. {e}")
            message["recipe"] = message["recipe"].merge(named_recipe)
        return message, parameters

    def filter_load_custom_recipe(self, message, parameters):
        """Load a custom recipe from a message and merge them into the recipe object"""
        if message.get("custom_recipe"):
            try:
                custom_recipe = workflows.recipe.Recipe(
                    recipe=json.dumps(message["custom_recipe"])
                )
                self.log.info(
                    "Received message containing a custom recipe: %s",
                    message["custom_recipe"],
                )
            except Exception as e:
                raise ValueError(
                    f"Error reading custom recipe {message['custom_recipe']}"
                ) from e
            try:
                custom_recipe.validate()
            except workflows.Error as e:
                raise ValueError(
                    f"Custom recipe {custom_recipe} failed validation. {e}"
                )
            message["recipe"] = message["recipe"].merge(custom_recipe)
        return message, parameters

    def filter_apply_parameters(self, message, parameters):
        """Fill in any placeholders in the recipe of the form {name} using the
        parameters data structure"""
        message["recipe"].apply_parameters(parameters)
        return message, parameters

    def initializing(self):
        """Subscribe to the processing_recipe queue. Received messages must be acknowledged."""
        self.log.info("Dispatcher starting")
        self.recipe_basepath = self._environment["config"].storage.get(
            "zocalo.recipe_directory"
        )
        # Store a copy of all dispatch messages in this location
        self._logbook = self._environment["config"].storage.get(
            "zocalo.dispatcher.logbook_location"
        )
        if self._logbook:
            try:
                os.makedirs(self._logbook, 0o775)
            except OSError:
                pass  # Ignore if exists
            if os.access(self._logbook, os.R_OK | os.W_OK | os.X_OK):
                self.log.debug(f"Using logbook location {self._logbook}")
            else:
                self.log.error(f"Logbook disabled: Can not write to {self._logbook}")
                self._logbook = None
        else:
            self.log.info(
                "Logbook disabled: zocalo.dispatcher.logbook_location not defined"
            )
            self._logbook = None

        self.message_filters = {
            **{
                f.name: f.load()
                for f in pkg_resources.iter_entry_points(
                    "zocalo.services.dispatcher.filters"
                )
            },
            "load_custom_recipe": self.filter_load_custom_recipe,
            "load_recipes_from_files": self.filter_load_recipes_from_files,
            "apply_parameters": self.filter_apply_parameters,
        }

        self.ready_for_processing = {
            f.name: f.load()
            for f in pkg_resources.iter_entry_points(
                "zocalo.services.dispatcher.ready_for_processing"
            )
        }

        workflows.recipe.wrap_subscribe(
            self._transport,
            "processing_recipe",
            self.process,
            acknowledgement=True,
            log_extender=self.extend_log,
            allow_non_recipe_messages=True,
        )

    def record_to_logbook(self, guid, header, original_message, message, recipewrap):
        basepath = os.path.join(self._logbook, time.strftime("%Y-%m"))
        clean_guid = re.sub(r"[^a-z0-9A-Z\-]+", "", guid, re.UNICODE)
        if not clean_guid or len(clean_guid) < 3:
            self.log.warning(
                "Message with non-conforming guid %s not written to logbook", guid
            )
            return
        try:
            os.makedirs(os.path.join(basepath, clean_guid[:2]))
        except OSError:
            pass  # Ignore if exists

        def neat_json_to_file(obj, fh, **kwargs):
            def _fix(item):
                if isinstance(item, list):
                    return [_fix(i) for i in item]
                if isinstance(item, dict):
                    return {str(key): _fix(value) for key, value in item.items()}
                return item

            return json.dump(
                _fix(obj),
                fh,
                sort_keys=True,
                skipkeys=True,
                default=str,
                indent=2,
                separators=(",", ": "),
                **kwargs,
            )

        try:
            log_entry = os.path.join(basepath, clean_guid[:2], clean_guid[2:])
            with open(log_entry, "w") as fh:
                fh.write("Incoming message header:\n")
                neat_json_to_file(header, fh)
                fh.write("\n\nIncoming message body:\n")
                neat_json_to_file(original_message, fh)
                fh.write("\n\nParsed message body:\n")
                neat_json_to_file(message, fh)
                fh.write("\n\nRecipe object:\n")
                neat_json_to_file(
                    recipewrap.recipe.recipe,
                    fh,
                )
                fh.write("\n")
            self.log.debug("Message saved in logbook at %s", log_entry)
        except Exception:
            self.log.warning("Could not write message to logbook", exc_info=True)

    def process(self, rw, header, message):
        """Process an incoming processing request."""
        # Time execution
        start_time = timeit.default_timer()

        # Load processing parameters
        parameters = message.get("parameters", {})
        if not isinstance(parameters, dict):
            # malformed message
            self.log.error(
                "Dispatcher rejected malformed message: parameters not given as dictionary"
            )
            self._transport.nack(header)
            return

        # Unless 'guid' is already defined then generate a unique recipe IDs for
        # this request, which is attached to all downstream log records and can
        # be used to determine unique file paths.
        recipe_id = parameters.get("guid") or str(uuid.uuid4())
        parameters["guid"] = recipe_id

        if rw:
            # If we received a recipe wrapper then we already have a recipe_ID
            # attached to logs. Make a note of the downstream recipe ID so that
            # we can track execution beyond recipe boundaries.
            self.log.info(
                "Processing request with new recipe ID %s:\n%s", recipe_id, str(message)
            )

        # If we are fully logging requests then make a copy of the original message
        if self._logbook:
            original_message = copy.deepcopy(message)

        # From here on add the global ID to all log messages
        with self.extend_log("recipe_ID", recipe_id):
            self.log.debug("Received processing request:\n" + str(message))
            self.log.debug("Received processing parameters:\n" + str(parameters))

            # Step 1: Check that parsing the message can proceed
            for name, ready_for_processing in self.ready_for_processing.items():
                if not ready_for_processing(message, parameters):
                    # Message not yet cleared for processing
                    if "dispatcher_expiration" not in parameters:
                        parameters["dispatcher_expiration"] = time.time() + int(
                            parameters.get("dispatcher_timeout", 120)
                        )
                    if parameters["dispatcher_expiration"] > time.time():
                        # Wait for 2 seconds
                        txn = self._transport.transaction_begin(
                            subscription_id=header["subscription"]
                        )
                        self._transport.ack(header, transaction=txn)
                        self._transport.send(
                            "processing_recipe", message, transaction=txn, delay=2
                        )
                        self.log.info("Message not yet ready for processing")
                        self._transport.transaction_commit(txn)
                        return
                    elif parameters.get("dispatcher_error_queue"):
                        # Drop message into error queue
                        txn = self._transport.transaction_begin(
                            subscription_id=header["subscription"]
                        )
                        self._transport.ack(header, transaction=txn)
                        self._transport.send(
                            parameters["dispatcher_error_queue"],
                            message,
                            transaction=txn,
                        )
                        self.log.info(
                            "Message rejected to specified error queue as still not ready for processing"
                        )
                        self._transport.transaction_commit(txn)
                        return
                    else:
                        # Unhandled error, send message to DLQ
                        self.log.error(
                            "Message rejected as still not ready for processing",
                        )
                        self._transport.nack(header)
                        return

            filtered_message = copy.deepcopy(message)
            filtered_parameters = copy.deepcopy(parameters)

            # Create empty recipe
            filtered_message["recipe"] = workflows.recipe.Recipe()

            # Apply all specified filters in order to message and parameters
            for name, f in self.message_filters.items():
                try:
                    filtered_message, filtered_parameters = f(
                        filtered_message, filtered_parameters
                    )
                except Exception as e:
                    self.log.error(
                        "Rejected message due to filter (%s) error: %s",
                        name,
                        str(e),
                        exc_info=True,
                    )
                    self._transport.nack(header)
                    return

            self.log.debug("Mangled processing request:\n" + str(filtered_message))
            self.log.debug(
                "Mangled processing parameters:\n" + str(filtered_parameters)
            )

            # Conditionally acknowledge receipt of the message
            txn = self._transport.transaction_begin(
                subscription_id=header["subscription"]
            )
            self._transport.ack(header, transaction=txn)

            rw = workflows.recipe.RecipeWrapper(
                recipe=filtered_message["recipe"], transport=self._transport
            )
            rw.environment = {
                "ID": recipe_id
            }  # FIXME: This should go into the constructor, but workflows can't do that yet
            rw.start(transaction=txn)

            # Write information to logbook if applicable
            if self._logbook:
                self.record_to_logbook(
                    recipe_id, header, original_message, filtered_message, rw
                )

            # Commit transaction
            self._transport.transaction_commit(txn)
            self.log.info(
                "Processed incoming message in %.4f seconds",
                timeit.default_timer() - start_time,
            )
