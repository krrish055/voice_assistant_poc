"""
events/handler_registry.py

Single responsibility: map EventType → list of IEventHandler.
Open/Closed: add handlers via register() without modifying this file.
"""
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Type

from events.domain_events import DomainEvent, EventType


class IEventHandler(ABC):
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None: ...


class EventHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[IEventHandler]] = defaultdict(list)

    def register(self, event_type: EventType, handler: IEventHandler) -> None:
        self._handlers[event_type].append(handler)

    def get_handlers(self, event_type: EventType) -> List[IEventHandler]:
        return list(self._handlers.get(event_type, []))
