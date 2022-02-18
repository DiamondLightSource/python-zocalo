from __future__ import annotations

from unittest import mock

import pytest
from workflows.recipe.wrapper import RecipeWrapper
from workflows.transport.offline_transport import OfflineTransport

from zocalo.service.mailer import Mailer


@pytest.fixture
def zocalo_configuration(mocker):
    mock_zc = mocker.patch("zocalo.configuration.from_file", autospec=True)
    mock_zc.return_value.smtp = {
        "host": "localhost",
        "port": 4242,
        "from": "zocalo@example.com",
    }
    return mock_zc


def test_mailer_receive_msg(mocker, zocalo_configuration):
    message = {
        "recipe": {
            "1": {
                "parameters": {
                    "recipients": {
                        "all": "foo@example.com",
                        "select": "bar",
                        "bar": ["bar@example.com"],
                    },
                    "subject": "This is a test email",
                    "content": [
                        "header\n",
                        "{pprint_payload}\n",
                        "footer",
                    ],
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
    mailer = Mailer()
    mailer.transport = t
    mailer.start()
    mock_smtp = mocker.patch("smtplib.SMTP")
    msg = {
        "foo": "bar",
        "ham": "spam",
    }
    mailer.receive_msg(rw, header, msg)
    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()
    email_msg = mock_smtp.return_value.__enter__.return_value.send_message.call_args[0][
        0
    ]
    assert email_msg["To"] == "bar@example.com, foo@example.com"
    assert email_msg["From"] == "zocalo@example.com"
    assert email_msg["Subject"] == "This is a test email"
    assert (
        email_msg.get_content()
        == """\
header
{'foo': 'bar', 'ham': 'spam'}
footer
"""
    )
