import os
import errno
import json
import subprocess
from datetime import datetime

import workflows.recipe
from workflows.services.common_service import CommonService


class Runner(CommonService):
    """Basic Runner service to execute recipes and wrapped recipes"""

    # Human readable service name
    _service_name = "Runner"

    # Logger name
    _logger_name = "zocalo.runner"

    @property
    def custom_queue(self):
        return os.environ.get("RUNNER_CUSTOM_QUEUE") or ""

    def initializing(self):
        self.log.info("Runner Service starting")

        custom_queue = f"{self.custom_queue}." if self.custom_queue else ""
        queue = f"runner.{custom_queue}submission"
        self.log.info("Subscribing to: %s", queue)

        workflows.recipe.wrap_subscribe(
            self._transport,
            queue,
            self.process,
            acknowledgement=True,
            log_extender=self.extend_log,
        )

    @staticmethod
    def _recursive_mkdir(path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def process(self, rw, header, message):
        """Process the incoming recipes"""
        self.log.info(
            f"Running Runner Service at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        parameters = rw.recipe_step["parameters"]

        try:
            workingdir = parameters["workingdir"]
            commands = parameters["commands"]
        except KeyError:
            self.log.error(
                "Recipe did not contain both workingdir and commands", exc_info=True
            )
            self._transport.nack(header)
            return

        if not len(commands):
            self.log.error("Did not receive any commands to execute")
            self._transport.nack(header)
            return

        try:
            self._recursive_mkdir(workingdir)
        except OSError as e:
            self.log.error(
                "Could not create working directory: %s", str(e), exc_info=True
            )
            self._transport.nack(header)
            return

        commands = [
            com.replace("$RECIPEPOINTER", str(rw.recipe_pointer)) for com in commands
        ]

        if "recipefile" in parameters:
            recipefile = parameters["recipefile"]
            try:
                self._recursive_mkdir(os.path.dirname(recipefile))
            except OSError as e:
                if e.errno == errno.ENOENT:
                    self.log.error(
                        "Error in underlying filesystem: %s", str(e), exc_info=True
                    )
                    self._transport.nack(header)
                    return
                raise
            self.log.debug("Writing recipe to %s", recipefile)
            commands = [com.replace("$RECIPEFILE", recipefile) for com in commands]

            with open(recipefile, "w") as fh:
                fh.write(rw.recipe.pretty())

        if "recipeenvironment" in parameters:
            recipeenvironment = parameters["recipeenvironment"]
            try:
                self._recursive_mkdir(os.path.dirname(recipeenvironment))
            except OSError as e:
                if e.errno == errno.ENOENT:
                    self.log.error(
                        "Error in underlying filesystem: %s", str(e), exc_info=True
                    )
                    self._transport.nack(header)
                    return
                raise
            self.log.debug("Writing recipe environment to %s", recipeenvironment)
            commands = [
                com.replace("$RECIPEENV", recipeenvironment) for com in commands
            ]
            with open(recipeenvironment, "w") as fh:
                json.dump(
                    rw.environment, fh, sort_keys=True, indent=2, separators=(",", ": ")
                )

        # Create a recipewrap file to pass to the wrapper script
        if "recipewrapper" in parameters:
            recipewrapper = parameters["recipewrapper"]
            self.log.debug(f"Storing serialized recipe wrapper in {recipewrapper}")

            try:
                self._recursive_mkdir(os.path.dirname(recipewrapper))
            except OSError as e:
                if e.errno == errno.ENOENT:
                    self.log.error(
                        "Error in underlying filesystem: %s", str(e), exc_info=True
                    )
                else:
                    self.log.error(
                        "Could not create recipe wrapper directory: %s",
                        str(e),
                        exc_info=True,
                    )
                self._transport.nack(header)
                return

            try:
                with open(recipewrapper, "w") as fh:
                    json.dump(
                        {
                            "recipe": rw.recipe.recipe,
                            "recipe-pointer": rw.recipe_pointer,
                            "environment": rw.environment,
                            "recipe-path": rw.recipe_path,
                            "payload": rw.payload,
                        },
                        fh,
                        indent=2,
                    )
            except OSError:
                self.log.error(f"Could not write recipewrap to file at {recipewrapper}")
                self._transport.nack(header)
                return

            # Replace the $RECIPEWRAP keyword in the command with the new recipewrapper file
            commands = [com.replace("$RECIPEWRAP", recipewrapper) for com in commands]

        # Conditionally acknowledge receipt of the message
        txn = self._transport.transaction_begin()
        self._transport.ack(header, transaction=txn)

        try:
            commands_list = [cmd.split(" ") for cmd in commands]
            for cmd in commands_list:
                output_file = parameters.get("output_file")
                result = subprocess.run(
                    cmd,
                    timeout=parameters.get("timeout", 30),
                    cwd=workingdir,
                    stdout=subprocess.PIPE if output_file else None,
                    stderr=subprocess.STDOUT if output_file else None
                )
                try:
                    result.check_returncode()
                finally:
                    if output_file:
                        output_file = os.path.join(workingdir, output_file)
                        with open(output_file, "a") as f:
                            f.write(result.stdout.decode("utf-8"))

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log.exception(f"Had error running command: {cmd} {str(e)}")
            rw.send_to("failure", "")

        except subprocess.TimeoutExpired:
            self.log.exception(f"Time ran out running command: {cmd}")
            rw.send_to("timeout", "")

        except Exception:
            self.log.exception("Could not execute commands")

        # Send results onwards
        rw.set_default_channel("job_processed")
        rw.send({"processed": True}, transaction=txn)

        # Stop processing message
        self._transport.transaction_commit(txn)
