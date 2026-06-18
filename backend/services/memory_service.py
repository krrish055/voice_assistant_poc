"""
services/memory_service.py

Single responsibility: store and query report slot state per session.

Design: interface + in-process dict implementation.
Swap to Redis by implementing the same interface.

Required slots: topic, page_count, output_format
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


_REQUIRED_SLOTS = ("topic", "page_count", "output_format")


class IMemoryService(ABC):
    @abstractmethod
    def get_slots(self, session_id: str) -> Dict:
        ...

    @abstractmethod
    def update_slot(self, session_id: str, key: str, value) -> None:
        ...

    @abstractmethod
    def is_complete(self, session_id: str) -> bool:
        ...

    @abstractmethod
    def missing_slots(self, session_id: str) -> list:
        ...

    @abstractmethod
    def clear(self, session_id: str) -> None:
        ...


class MemoryService(IMemoryService):
    """In-process slot store. Thread-safe for single-process deployments."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict] = {}

    def get_slots(self, session_id: str) -> Dict:
        return dict(self._store.get(session_id, {}))

    def update_slot(self, session_id: str, key: str, value) -> None:
        self._store.setdefault(session_id, {})[key] = value

    def is_complete(self, session_id: str) -> bool:
        slots = self._store.get(session_id, {})
        return all(slots.get(s) for s in _REQUIRED_SLOTS)

    def missing_slots(self, session_id: str) -> list:
        slots = self._store.get(session_id, {})
        return [s for s in _REQUIRED_SLOTS if not slots.get(s)]

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
