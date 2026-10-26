from __future__ import annotations

from unittest import mock

import pytest
from workflows.recipe.wrapper import RecipeWrapper
from workflows.transport.offline_transport import OfflineTransport

import zocalo.configuration
from zocalo.service.mailer import Mailer


@pytest.fixture
def zocalo_configuration():
    mock_zc = mock.MagicMock(zocalo.configuration.Configuration)
    mock_zc.smtp = {
        "host": "localhost",
        "port": 4242,
        "from": "zocalo@example.com",
    }
    return mock_zc


@pytest.fixture
def mock_smtp_send_message(mocker):
    mock_smtp = mocker.patch("smtplib.SMTP")
    return mock_smtp.return_value.__enter__.return_value.send_message


def test_mailer_receive_msg(zocalo_configuration, mock_smtp_send_message):
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
    mailer._environment = {"config": zocalo_configuration}
    mailer.transport = t
    mailer.start()
    msg = {
        "foo": "bar",
        "ham": "spam",
    }
    mailer.receive_msg(rw, header, msg)
    mock_smtp_send_message.assert_called_once()
    email_msg = mock_smtp_send_message.call_args[0][0]
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


@pytest.fixture
def mailer(zocalo_configuration):
    mailer = Mailer()
    mailer._environment = {"config": zocalo_configuration}
    mailer.transport = mock.Mock()
    mailer.start()
    return mailer


def recipe_wrapper(parameters, transport):
    return RecipeWrapper(
        message={"recipe": {"1": {"parameters": parameters}}, "recipe-pointer": 1},
        transport=transport,
    )


HEADER = {"message-id": 1, "subscription": 1}


def test_mailer_simple_message(mailer, mock_smtp_send_message):
    mailer.receive_msg(
        None,
        HEADER,
        {
            "parameters": {"recipient": ["a@example.com"], "from": "b@example.com"},
            "content": "Hello {payload[extra]}",
            "extra": "world",
        },
    )
    mailer.transport.ack.assert_called_once_with(HEADER)
    email_msg = mock_smtp_send_message.call_args[0][0]
    assert email_msg["To"] == "a@example.com"
    assert email_msg["From"] == "b@example.com"
    assert email_msg["Subject"] == "mail notification via zocalo"
    assert email_msg.get_content() == "Hello world\n"


def test_mailer_parameters_content_overrides_simple_content(
    mailer, mock_smtp_send_message
):
    mailer.receive_msg(
        None,
        HEADER,
        {
            "parameters": {"recipients": "a@example.com", "content": "from parameters"},
            "content": "from message",
        },
    )
    email_msg = mock_smtp_send_message.call_args[0][0]
    assert email_msg.get_content() == "from parameters\n"


@pytest.mark.parametrize(
    "message",
    [
        "not a dict",
        {"content": "no parameters"},
        {"parameters": {}, "content": "empty parameters"},
        {"parameters": {"recipients": "a@example.com"}},
        {"parameters": {"recipients": "a@example.com"}, "content": ""},
        {"parameters": {"subject": "no recipients"}, "content": "x"},
    ],
)
def test_mailer_rejects_invalid_simple_message(mailer, mock_smtp_send_message, message):
    mailer.receive_msg(None, HEADER, message)
    mailer.transport.nack.assert_called_once_with(HEADER, requeue=False)
    mock_smtp_send_message.assert_not_called()


@pytest.mark.parametrize(
    "parameters",
    [
        {"content": "no recipients"},
        {"recipients": "", "content": "x"},
        {"recipients": [], "content": "x"},
        {"recipients": {"bar": ["a@example.com"]}, "content": "no select"},
        {"recipients": {"select": "bar", "foo": "a@example.com"}, "content": "x"},
        {"recipients": "a@example.com"},
    ],
)
def test_mailer_rejects_invalid_recipe_parameters(
    mailer, mock_smtp_send_message, parameters
):
    rw = recipe_wrapper(parameters, mailer.transport)
    mailer.receive_msg(rw, HEADER, {})
    mailer.transport.nack.assert_called_once_with(HEADER, requeue=False)
    mock_smtp_send_message.assert_not_called()


def test_mailer_recipe_ignores_payload_parameters(mailer, mock_smtp_send_message):
    rw = recipe_wrapper({"content": "x"}, mailer.transport)
    mailer.receive_msg(rw, HEADER, {"parameters": {"recipients": "a@example.com"}})
    mailer.transport.nack.assert_called_once_with(HEADER, requeue=False)
    mock_smtp_send_message.assert_not_called()


def test_mailer_select_group_from_all(mailer, mock_smtp_send_message):
    rw = recipe_wrapper(
        {"recipients": {"select": "all", "all": "a@example.com"}, "content": "x"},
        mailer.transport,
    )
    mailer.receive_msg(rw, HEADER, {})
    email_msg = mock_smtp_send_message.call_args[0][0]
    assert email_msg["To"] == "a@example.com"
