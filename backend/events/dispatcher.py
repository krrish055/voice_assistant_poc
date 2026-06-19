"""
events/dispatcher.py

Single responsibility: fan-out a DomainEvent to all registered handlers concurrently.
Pure asyncio — no external broker required.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

from events.domain_events import DomainEvent
from events.handler_registry import EventHandlerRegistry

if TYPE_CHECKING:
    pass

_log = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self, registry: EventHandlerRegistry) -> None:
        self._registry = registry

    async def emit(self, event: DomainEvent) -> None:
        handlers = self._registry.get_handlers(event.event_type)
        if not handlers:
            _log.debug("[EventDispatcher] no_handlers event=%s", event.event_type)
            return
        _log.info(
            "[EventDispatcher] emit event=%s id=%s handlers=%d",
            event.event_type, event.event_id, len(handlers),
        )
        results = await asyncio.gather(
            *[h.handle(event) for h in handlers],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _log.error(
                    "[EventDispatcher] handler_error event=%s handler=%s error=%s",
                    event.event_type, type(handlers[i]).__name__, result,
                )
