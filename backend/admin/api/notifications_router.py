"""
admin/api/notifications_router.py

Endpoints: query notifications for a user, mark a notification seen.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict

from admin.constants import SUCCESS_CODE
from constants import ERR_NOTIFICATION_NOT_FOUND
from services.container import notification_service
from exceptions import AppBaseException

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/{user_id}")
def get_notifications(user_id: str, unread_only: bool = True) -> Dict:
    notifications = notification_service.get_for_user(user_id, unread_only=unread_only)
    return {
        "status":        SUCCESS_CODE,
        "notifications": [n.to_dict() for n in notifications],
        "total":         len(notifications),
    }


@router.patch("/{notification_id}/seen")
def mark_seen(notification_id: str) -> Dict:
    try:
        notification_service.mark_seen(notification_id)
        return {"status": SUCCESS_CODE, "notification_id": notification_id}
    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
