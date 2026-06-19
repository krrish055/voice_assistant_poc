"""
notifications/service.py

Single responsibility: create, query, and mutate Notification records.
"""
import logging
from typing import List, Optional

from config import NOTIFICATION_MAX_UNREAD
from constants import ERR_NOTIFICATION_NOT_FOUND
from events.dispatcher import EventDispatcher
from events.domain_events import DomainEvent, EventType
from exceptions import AppBaseException
from notifications.models import Notification
from notifications.repository import INotificationRepository

_log = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, repository: INotificationRepository, dispatcher: EventDispatcher) -> None:
        self._repo       = repository
        self._dispatcher = dispatcher

    async def create(self, user_id: str, message: str, ref_type: str, ref_id: str) -> Notification:
        notification = Notification.create(
            user_id=user_id, message=message, ref_type=ref_type, ref_id=ref_id,
        )
        self._repo.save(notification)
        _log.info(
            "[NotificationService] created id=%s user=%s ref_type=%s",
            notification.id, user_id, ref_type,
        )
        await self._dispatcher.emit(DomainEvent(
            event_type=EventType.NOTIFICATION_CREATED,
            payload={"notification_id": notification.id, "user_id": user_id},
        ))
        return notification

    def get_for_user(self, user_id: str, unread_only: bool = True) -> List[Notification]:
        return self._repo.get_by_user(user_id, unread_only=unread_only, limit=NOTIFICATION_MAX_UNREAD)

    def mark_seen(self, notification_id: str) -> None:
        notification = self._repo.get_by_id(notification_id)
        if not notification:
            raise AppBaseException(ERR_NOTIFICATION_NOT_FOUND, status_code=404)
        self._repo.mark_seen(notification_id)
        _log.info("[NotificationService] seen id=%s", notification_id)
