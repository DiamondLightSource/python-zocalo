from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Annotated, Any

import pydantic
import workflows.recipe
from workflows.recipe.typed import NonEmpty, typed_handler
from workflows.services.common_service import CommonService


class JSONLinesParameters(pydantic.BaseModel):
    output_filename: Annotated[Path, NonEmpty]
    include: set[str] = set()
    exclude: set[str] = set()


class JSONLines(CommonService):
    """Write received messages into a JSONLines file on disk"""

    # Human readable service name
    _service_name = "JSON Lines"

    # Logger name
    _logger_name = "zocalo.service.jsonlines"

    _data: dict[Path, list[tuple[dict, dict]]]

    def initializing(self) -> None:
        self._register_idle(1, self.process_messages)
        self.subscribe(
            "jsonlines",
            self.receive_msg,
            exclusive=True,
            prefetch_count=100,
        )
        self._lock = threading.Lock()
        self._data = {}

    @typed_handler
    def receive_msg(
        self,
        rw: workflows.recipe.RecipeWrapper,
        header: dict,
        message: dict[str, Any],
        parameters: JSONLinesParameters,
    ) -> None:
        output_filename = parameters.output_filename
        filtered_message = message
        if parameters.include:
            filtered_message = {
                k: v for k, v in filtered_message.items() if k in parameters.include
            }
        if parameters.exclude:
            filtered_message = {
                k: v for k, v in filtered_message.items() if k not in parameters.exclude
            }

        with self._lock:
            self._data.setdefault(output_filename, [])
            self._data[output_filename].append((header, filtered_message))
            n_stored_messages = sum(len(v) for v in self._data.values())

        if n_stored_messages == 100:
            self.log.info("Triggering process messages")
            self.process_messages()

    def process_messages(self) -> None:
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
