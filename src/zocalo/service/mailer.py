from __future__ import annotations

import email.message
import pprint
import smtplib
from collections.abc import Mapping
from typing import Annotated, Any

import pydantic
import workflows.recipe
from workflows.recipe.typed import typed_handler
from workflows.services.common_service import CommonService

import zocalo.configuration


class _SafeDict(dict):
    """A dictionary that returns undefined keys as {keyname}.
    This can be used to selectively replace variables in datastructures."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _listify(recipients: str | list[str]) -> list[str]:
    return recipients if isinstance(recipients, list) else [recipients]


class RecipientGroups(pydantic.BaseModel):
    """Recipients chosen from named groups of addresses, eg.

    {"select": "i03", "i03": ["a@example.com"], "all": "b@example.com"}

    sends to the addresses of the group named by 'select', plus those in 'all'.
    """

    model_config = pydantic.ConfigDict(extra="allow")
    # Typing the extra fields validates the group addresses, as documented by pydantic
    __pydantic_extra__: dict[str, str | list[str]]  # pyright: ignore[reportIncompatibleVariableOverride]

    select: str
    all: str | list[str] | None = None

    def addresses(self) -> list[str]:
        groups = self.model_dump(exclude_unset=True)
        selected = set(_listify(groups.get(self.select, [])))
        if self.all:
            selected |= set(_listify(self.all))
        return sorted(selected)


class MailParameters(pydantic.BaseModel):
    recipients: (
        Annotated[str, pydantic.Field(min_length=1)]
        | Annotated[list[str], pydantic.Field(min_length=1)]
        | RecipientGroups
    )
    from_: str | None = pydantic.Field(None, alias="from")
    subject: str = "mail notification via zocalo"
    content: str | list[str] | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def _accept_recipient(cls, data: Any) -> Any:
        """Accept 'recipient' as an alternative spelling of 'recipients'"""
        if isinstance(data, Mapping) and "recipients" not in data:
            if "recipient" in data:
                return {**data, "recipients": data["recipient"]}
        return data

    def addresses(self) -> list[str]:
        if isinstance(self.recipients, RecipientGroups):
            return self.recipients.addresses()
        return _listify(self.recipients)


class SimpleMailMessage(pydantic.BaseModel):
    """A mail notification sent directly to the queue, outside of a recipe"""

    model_config = pydantic.ConfigDict(extra="allow")

    parameters: Annotated[dict[str, Any], pydantic.Field(min_length=1)]
    content: (
        Annotated[str, pydantic.Field(min_length=1)]
        | Annotated[list[str], pydantic.Field(min_length=1)]
    )


class Mailer(CommonService):
    """A service that generates emails from messages."""

    # Human readable service name
    _service_name = "Mail Notifications"

    # Logger name
    _logger_name = "zocalo.services.mailer"

    def initializing(self) -> None:
        """Subscribe to the Mail notification queue.
        Received messages must be acknowledged."""
        self.log.debug("Mail notifications starting")

        if not self.config:
            raise zocalo.ConfigurationError("No Zocalo configuration loaded")
        if not self.config.smtp:
            raise zocalo.ConfigurationError(
                "There are no SMTP settings configured in your environment"
            )

        self.subscribe(
            "mailnotification",
            self.receive_msg,
            allow_non_recipe_messages=True,
        )

    def receive_msg(
        self, rw: workflows.recipe.RecipeWrapper | None, header: dict, message: Any
    ) -> None:
        """Do some mail notification."""

        self.log.info(f"{message=}")

        if rw:
            self.receive_recipe_msg(rw, header, message)
        else:
            # Incoming message is not a recipe message. Simple messages can be valid
            self.receive_simple_msg(rw, header, message)

    @typed_handler
    def receive_recipe_msg(
        self,
        rw: workflows.recipe.RecipeWrapper,
        header: dict,
        message: Any,
        parameters: MailParameters,
    ) -> None:
        self.send_mail(header, parameters, content=None, payload=message)

    @typed_handler(parameters_from=("message.parameters",))
    def receive_simple_msg(
        self,
        rw: None,
        header: dict,
        message: SimpleMailMessage,
        parameters: MailParameters,
    ) -> None:
        self.send_mail(
            header, parameters, content=message.content, payload=message.model_dump()
        )

    def send_mail(
        self,
        header: dict,
        parameters: MailParameters,
        *,
        content: str | list[str] | None,
        payload: Any,
    ) -> None:
        recipients = parameters.addresses()
        if not recipients:
            self.log.warning("No selected recipients for message")
            self.transport.nack(header, requeue=False)
            return

        sender = parameters.from_ or self.config.smtp["from"]

        subject = parameters.subject

        if parameters.content is not None:
            content = parameters.content

        if not content:
            self.log.warning("Message has no content")
            self.transport.nack(header, requeue=False)
            return
        if isinstance(content, list):
            content = "".join(content)
        if isinstance(payload, list):
            pprint_message = "\n".join(payload)
        else:
            pprint_message = pprint.pformat(payload)

        content = content.format_map(
            _SafeDict(payload=payload, pprint_payload=pprint_message)
        )
        self.log.info("Sending mail notification %r to %r", subject, recipients)

        # Accept message before sending mail. While this means we do not guarantee
        # message delivery it also means if the service crashes after delivery we
        # will not re-deliver the message inifinitely many times.
        self.transport.ack(header)

        try:
            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["To"] = recipients
            msg["From"] = sender
            msg.set_content(content)
            with smtplib.SMTP(
                host=self.config.smtp["host"], port=self.config.smtp["port"], timeout=60
            ) as s:
                s.send_message(msg)
        except TimeoutError as e:
            self.log.error(
                f"Message delivery failed with timeout: {e}",
            )
        except Exception as e:
            self.log.error(
                f"Message delivery failed with error {e}",
            )
        else:
            self.log.debug("Message sent successfully")
