"""
approvals/service.py

Single responsibility: create and action approval requests.
Emits domain events. Delegates persistence to repository.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from approvals.models import ApprovalAction, ApprovalRequest, ApprovalStatus
from approvals.repository import IApprovalRepository
from approvals.state_manager import ApprovalStateManager
from constants import ERR_APPROVAL_NOT_FOUND
from events.dispatcher import EventDispatcher
from events.domain_events import DomainEvent, EventType
from exceptions import AppBaseException

_log = logging.getLogger(__name__)

_ACTION_TARGET_MAP: dict[ApprovalAction, ApprovalStatus] = {
    ApprovalAction.APPROVE: ApprovalStatus.APPROVED,
    ApprovalAction.REJECT:  ApprovalStatus.REJECTED,
}

_ACTION_EVENT_MAP: dict[ApprovalAction, EventType] = {
    ApprovalAction.APPROVE: EventType.APPROVAL_APPROVED,
    ApprovalAction.REJECT:  EventType.APPROVAL_REJECTED,
}


class ApprovalService:
    def __init__(self, repository: IApprovalRepository, dispatcher: EventDispatcher) -> None:
        self._repo       = repository
        self._dispatcher = dispatcher

    async def create(
        self,
        session_id: str,
        user_id: str,
        request_type: str,
        payload: Dict,
    ) -> ApprovalRequest:
        approval = ApprovalRequest.create(
            session_id=session_id,
            user_id=user_id,
            request_type=request_type,
            payload=payload,
        )
        self._repo.save(approval)
        _log.info(
            "[ApprovalService] created id=%s type=%s user=%s",
            approval.id, request_type, user_id,
        )
        await self._dispatcher.emit(DomainEvent(
            event_type=EventType.APPROVAL_REQUESTED,
            payload={
                "approval_id": approval.id,
                "session_id":  session_id,
                "user_id":     user_id,
                "request_type": request_type,
            },
        ))
        return approval

    async def process_action(
        self,
        approval_id: str,
        action: ApprovalAction,
        reviewed_by: str,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        approval = self._repo.get_by_id(approval_id)
        if not approval:
            raise AppBaseException(ERR_APPROVAL_NOT_FOUND, status_code=404)

        target         = _ACTION_TARGET_MAP[action]
        approval.status = ApprovalStateManager.transition(approval.status, target)
        approval.reviewed_by = reviewed_by
        approval.notes       = notes
        approval.updated_at  = datetime.now(timezone.utc)
        self._repo.update(approval)

        event_type = _ACTION_EVENT_MAP[action]
        await self._dispatcher.emit(DomainEvent(
            event_type=event_type,
            payload={
                "approval_id":       approval.id,
                "session_id":        approval.session_id,
                "user_id":           approval.user_id,
                "original_payload":  approval.payload,
                "reviewed_by":       reviewed_by,
            },
        ))
        _log.info(
            "[ApprovalService] actioned id=%s action=%s by=%s",
            approval_id, action, reviewed_by,
        )
        return approval

    def get_pending(self, limit: int = 50) -> List[ApprovalRequest]:
        return self._repo.get_by_status(ApprovalStatus.PENDING, limit=limit)

    def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._repo.get_by_id(approval_id)
