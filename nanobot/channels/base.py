"""Base channel interface for chat platforms."""

import time
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


class BaseChannel(ABC):
    """
    Abstract base class for chat channel implementations.

    Each channel (Telegram, Discord, etc.) should implement this interface
    to integrate with the nanobot message bus.
    """

    name: str = "base"

    def __init__(self, config: Any, bus: MessageBus):
        """
        Initialize the channel.

        Args:
            config: Channel-specific configuration.
            bus: The message bus for communication.
        """
        self.config = config
        self.bus = bus
        self._running = False
        self._rate_limit_timestamps: dict[str, list[float]] = {}

    @abstractmethod
    async def start(self) -> None:
        """
        Start the channel and begin listening for messages.

        This should be a long-running async task that:
        1. Connects to the chat platform
        2. Listens for incoming messages
        3. Forwards messages to the bus via _handle_message()
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """
        Send a message through this channel.

        Args:
            msg: The message to send.
        """
        pass

    def is_allowed(self, sender_id: str) -> bool:
        """Check if *sender_id* is permitted.  Empty list → deny all; ``"*"`` → allow all."""
        allow_list = getattr(self.config, "allow_from", [])
        if not allow_list:
            logger.warning("{}: allow_from is empty — all access denied", self.name)
            return False
        if "*" in allow_list:
            return True
        return str(sender_id) in allow_list

    def is_rate_limited(self, sender_id: str) -> bool:
        """Return True if sender has exceeded the rate limit window."""
        rl = getattr(self.config, "rate_limit", None)
        if rl is None or not rl.enabled:
            return False

        now = time.time()
        cutoff = now - rl.window_seconds
        history = self._rate_limit_timestamps.setdefault(sender_id, [])
        self._rate_limit_timestamps[sender_id] = [t for t in history if t > cutoff]

        if len(self._rate_limit_timestamps[sender_id]) >= rl.max_messages:
            return True

        self._rate_limit_timestamps[sender_id].append(now)
        return False

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_key: str | None = None,
    ) -> None:
        """
        Handle an incoming message from the chat platform.

        This method checks permissions and forwards to the bus.

        Args:
            sender_id: The sender's identifier.
            chat_id: The chat/channel identifier.
            content: Message text content.
            media: Optional list of media URLs.
            metadata: Optional channel-specific metadata.
            session_key: Optional session key override (e.g. thread-scoped sessions).
        """
        if not self.is_allowed(sender_id):
            logger.warning(
                "Access denied for sender {} on channel {}. "
                "Add them to allowFrom list in config to grant access.",
                sender_id, self.name,
            )
            return

        if self.is_rate_limited(sender_id):
            rl = getattr(self.config, "rate_limit", None)
            reply_text = rl.reply_text if rl else ""
            if reply_text:
                logger.info("Rate limit hit for sender {} on channel {}", sender_id, self.name)
                out = OutboundMessage(
                    channel=self.name,
                    chat_id=str(chat_id),
                    content=reply_text,
                    metadata=metadata or {},
                )
                await self.bus.publish_outbound(out)
            else:
                logger.debug("Rate limit hit for sender {} on channel {} (silent drop)", sender_id, self.name)
            return

        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {},
            session_key_override=session_key,
        )

        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        """Check if the channel is running."""
        return self._running
