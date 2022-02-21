from __future__ import annotations

import email.message
import pprint
import smtplib

import workflows.recipe
from workflows.services.common_service import CommonService

import zocalo.configuration


class _SafeDict(dict):
    """A dictionary that returns undefined keys as {keyname}.
    This can be used to selectively replace variables in datastructures."""

    def __missing__(self, key):
        return "{" + key + "}"


class Mailer(CommonService):
    """A service that generates emails from messages."""

    # Human readable service name
    _service_name = "Mail Notifications"

    # Logger name
    _logger_name = "zocalo.services.mailer"

    def initializing(self):
        """Subscribe to the Mail notification queue.
        Received messages must be acknowledged."""
        self.log.debug("Mail notifications starting")

        if not self.config:
            raise zocalo.ConfigurationError("No Zocalo configuration loaded")
        if not self.config.smtp:
            raise zocalo.ConfigurationError(
                "There are no SMTP settings configured in your environment"
            )

        workflows.recipe.wrap_subscribe(
            self._transport,
            "mailnotification",
            self.receive_msg,
            acknowledgement=True,
            log_extender=self.extend_log,
            allow_non_recipe_messages=True,
        )

    @staticmethod
    def listify(recipients):
        if isinstance(recipients, list):
            return recipients
        elif isinstance(recipients, tuple):
            return list(recipients)
        else:
            return [recipients]

    def receive_msg(self, rw, header, message):
        """Do some mail notification."""

        self.log.info(f"{message=}")

        if rw:
            parameters = rw.recipe_step["parameters"]
            content = None
        else:
            # Incoming message is not a recipe message. Simple messages can be valid
            if (
                not isinstance(message, dict)
                or not message.get("parameters")
                or not message.get("content")
            ):
                self.log.warning("Rejected invalid simple message")
                self._transport.nack(header)
                return

            parameters = message["parameters"]
            content = message["content"]

        recipients = parameters.get("recipients", parameters.get("recipient"))
        if not recipients:
            self.log.warning("No recipients set for message")
            self._transport.nack(header)
            return
        if isinstance(recipients, dict):
            if "select" not in recipients:
                self.log.warning(
                    "Recipients dictionary must have key 'select' to select relevant group"
                )
                self._transport.nack(header)
                return
            selected_recipients = self.listify(recipients.get(recipients["select"], []))
            if recipients.get("all"):
                all_recipients = self.listify(recipients["all"])
            recipients = sorted(set(selected_recipients) | set(all_recipients))
            if not recipients:
                self.log.warning("No selected recipients for message")
                self._transport.nack(header)
                return
        else:
            recipients = self.listify(recipients)

        sender = parameters.get("from", self.config.smtp["from"])

        subject = parameters.get("subject", "mail notification via zocalo")

        content = parameters.get("content", content)

        if not content:
            self.log.warning("Message has no content")
            self._transport.nack(header)
            return
        if isinstance(content, list):
            content = "".join(content)
        if isinstance(message, list):
            pprint_message = "\n".join(message)
        else:
            pprint_message = pprint.pformat(message)

        content = content.format_map(
            _SafeDict(payload=message, pprint_payload=pprint_message)
        )

        self.log.info("Sending mail notification %r to %r", subject, recipients)

        # Accept message before sending mail. While this means we do not guarantee
        # message delivery it also means if the service crashes after delivery we
        # will not re-deliver the message inifinitely many times.
        self._transport.ack(header)

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
