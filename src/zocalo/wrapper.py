from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Mapping, NotRequired, TypedDict, cast

import workflows.services.common_service
import workflows.util

import zocalo

if TYPE_CHECKING:
    import workflows.recipe.wrapper

    import zocalo.configuration


class BaseWrapper:
    _logger_name = "zocalo.wrapper"  # The logger can be accessed via self.log

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._environment = kwargs.get("environment", {})
        self.__log_extra: dict[str, Any] = {}
        logger = logging.getLogger(self._logger_name)
        self.log = logging.LoggerAdapter(logger, extra=self.__log_extra)

    def set_recipe_wrapper(
        self, recwrap: workflows.recipe.wrapper.RecipeWrapper
    ) -> None:
        self.recwrap = recwrap
        self.__log_extra["recipe_ID"] = recwrap.environment["ID"]

    def prepare(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("starting", payload)

    def update(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("updates", payload)

    def done(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("completed", payload)

    def success(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("success", payload)

    def failure(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("failure", str(payload))

    def run(self) -> bool:
        raise NotImplementedError()

    def record_result_individual_file(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-individual-file", payload)

    def record_result_all_files(self, payload: Any = "") -> None:
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-all-files", payload)

    @property
    def config(self) -> zocalo.configuration.Configuration | None:
        return self._environment.get("config")


class DummyWrapper(BaseWrapper):
    _logger_name = "zocalo.wrapper.DummyWrapper"

    status_thread: StatusNotifications

    def run(self) -> bool:
        self.log.info("This is a dummy wrapper that simply waits for twenty seconds.")
        import time

        time.sleep(10)
        self.status_thread.taskname += " (still running)"
        time.sleep(10)
        return True


class StatusDict(TypedDict):
    host: str
    task: str
    workflows: str
    zocalo: str
    status: NotRequired[int]
    statustext: NotRequired[str]


class StatusNotifications(threading.Thread):
    def __init__(self, send_function: Callable[[Mapping], None], taskname: str):
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
        self._status_dict: StatusDict = {
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
            cast(dict[str, Any], self._status_dict)[field] = value

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

    def send_status(self, dictionary: Mapping) -> None:
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
