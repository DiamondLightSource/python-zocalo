from __future__ import annotations

import logging
import threading
from typing import Any, Callable

import workflows.services.common_service
import workflows.util

import zocalo


class BaseWrapper:
    _logger_name = "zocalo.wrapper"  # The logger can be accessed via self.log

    def __init__(self, *args, **kwargs):
        self._environment = kwargs.get("environment", {})
        self.__log_extra = {}
        logger = logging.getLogger(self._logger_name)
        self.log = logging.LoggerAdapter(logger, extra=self.__log_extra)

    def set_recipe_wrapper(self, recwrap):
        self.recwrap = recwrap
        self.__log_extra["recipe_ID"] = recwrap.environment["ID"]

    def prepare(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("starting", payload)

    def update(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("updates", payload)

    def done(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("completed", payload)

    def success(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("success", payload)

    def failure(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("failure", str(payload))

    def run(self):
        raise NotImplementedError()

    def record_result_individual_file(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-individual-file", payload)

    def record_result_all_files(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-all-files", payload)

    @property
    def config(self):
        return self._environment.get("config")


class DummyWrapper(BaseWrapper):
    _logger_name = "zocalo.wrapper.DummyWrapper"

    def run(self):
        self.log.info("This is a dummy wrapper that simply waits for twenty seconds.")
        import time

        time.sleep(10)
        self.status_thread.taskname += " (still running)"
        time.sleep(10)
        return True


class StatusNotifications(threading.Thread):
    def __init__(self, send_function: Callable[[dict], None], taskname: str):
        """Construct and start a StatusNotifications thread object.

        Once started, this will repeatedly re-broadcast the cached
        current status, every few seconds.

        Args:
            send_function: The transport function that broadcasts the actual message.
            taskname: The name of this task, which will be appended to the message.
        """
        super().__init__(name="zocalo status notification")
        self.daemon = True
        self._send_status = send_function
        self._lock = threading.Condition(threading.Lock())
        self._status_dict = {
            "host": workflows.util.generate_unique_host_id(),
            "task": taskname,
            "workflows": workflows.version(),
            "zocalo": zocalo.__version__,
        }
        self.set_status(workflows.services.common_service.Status.STARTING)
        self._keep_running = True
        self.start()

    def set_static_status_field(self, field: str, value: Any) -> None:
        """
        Add an additional static field to status notifications.
        """
        with self._lock:
            self._status_dict[field] = value

    def set_status(self, status: workflows.services.common_service.Status) -> None:
        with self._lock:
            self._status_dict["status"], self._status_dict["statustext"] = (
                status.intval,
                status.description,
            )
            self._lock.notify()

    @property
    def taskname(self) -> str:
        """Return the name displayed on service monitors for this task."""
        return self._status_dict["task"]

    @taskname.setter
    def taskname(self, value: str) -> None:
        """Set/update the name displayed on service monitors for this task."""
        with self._lock:
            self._status_dict["task"] = value
            self._lock.notify()

    def shutdown(self) -> None:
        """Stop the status notification thread."""
        self._keep_running = False

    def send_status(self, dictionary: dict) -> None:
        try:
            self._send_status(dictionary)
        except workflows.Disconnected:
            pass

    def run(self) -> None:
        """Status notification thread main loop."""
        with self._lock:
            self.send_status(self._status_dict)
            while self._keep_running:
                self._lock.wait(3)
                self.send_status(self._status_dict)
