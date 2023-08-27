from __future__ import annotations

import json
import threading
from pathlib import Path

import workflows.recipe
from workflows.services.common_service import CommonService


class JSONLines(CommonService):
    """Write received messages into a JSONLines file on disk"""

    # Human readable service name
    _service_name = "JSON Lines"

    # Logger name
    _logger_name = "zocalo.service.jsonlines"

    _data: dict[Path, list[tuple[dict, dict]]]

    def initializing(self):
        self._register_idle(1, self.process_messages)
        workflows.recipe.wrap_subscribe(
            self._transport,
            "jsonlines",
            self.receive_msg,
            acknowledgement=True,
            exclusive=True,
            log_extender=self.extend_log,
            prefetch_count=100,
        )
        self._lock = threading.Lock()
        self._data = {}

    def receive_msg(
        self, rw: workflows.recipe.RecipeWrapper, header: dict, message: dict
    ):
        output_filename = rw.recipe_step["parameters"]["output_filename"]
        if not output_filename:
            self.log.error("Received message contains no output_filename")
            rw.transport.nack(header)
            return
        output_filename = Path(output_filename)
        exclude = set(rw.recipe_step["parameters"].get("exclude", []))
        include = set(rw.recipe_step["parameters"].get("include", []))
        filtered_message = message
        if include:
            filtered_message = {
                k: v for k, v in filtered_message.items() if k in include
            }
        if exclude:
            filtered_message = {
                k: v for k, v in filtered_message.items() if k not in exclude
            }

        with self._lock:
            self._data.setdefault(output_filename, [])
            self._data[output_filename].append((header, filtered_message))
            n_stored_messages = sum(len(v) for v in self._data.values())

        if n_stored_messages == 100:
            self.log.info("Triggering process messages")
            self.process_messages()

    def process_messages(self):
        with self._lock:
            for output_filename in list(self._data):
                grouped_data = self._data[output_filename]
                self.log.info(
                    f"Writing {len(grouped_data)} messages to {output_filename}"
                )
                try:
                    output_filename = Path(output_filename)
                    output_filename.parent.mkdir(exist_ok=True, parents=True)
                    with output_filename.open(mode="a") as fh:
                        for _, message in grouped_data:
                            fh.write(json.dumps(message) + "\n")
                except Exception as e:
                    self.log.error(
                        f"Uncaught exception {e!r} writing messages to {output_filename}",
                        exc_info=True,
                    )
                    for header, _ in grouped_data:
                        self.transport.nack(header)
                    return
                else:
                    for header, _ in grouped_data:
                        self.transport.ack(header)

                # delete this data now we've processed it
                del self._data[output_filename]
