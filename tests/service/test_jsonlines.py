from __future__ import annotations

from unittest import mock

from workflows.recipe.wrapper import RecipeWrapper
from workflows.transport.offline_transport import OfflineTransport
from zocalo.service.jsonlines import JSONLines


def test_jsonlines(tmp_path):
    output_file = tmp_path / "foo.json"
    message = {
        "recipe": {
            "1": {
                "parameters": {
                    "output_filename": str(output_file),
                    "include": ["ham", "spam", "bar"],
                    "exclude": ["bar"],
                },
            },
        },
        "recipe-pointer": 1,
    }
    header = {
        "message-id": mock.sentinel,
        "subscription": mock.sentinel,
    }

    t = OfflineTransport()
    rw = RecipeWrapper(message=message, transport=t)
    jsonlines = JSONLines()
    jsonlines.transport = t
    jsonlines.start()
    messages = [
        {"foo": "bar", "ham": 1, "spam": 2, "bar": "foo"},
        {"foo": "bar", "ham": 2, "spam": 3, "bar": "foo"},
    ]
    for msg in messages:
        jsonlines.receive_msg(rw, header, msg)
    # This would normally be called internally by the service
    jsonlines.process_messages()

    content = output_file.read_text()
    assert (
        content
        == """\
{"ham": 1, "spam": 2}
{"ham": 2, "spam": 3}
"""
    )
