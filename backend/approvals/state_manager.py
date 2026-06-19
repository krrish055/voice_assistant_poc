"""
approvals/state_manager.py

FSM for ApprovalRequest lifecycle.
Mapping-based — no if/else chains.
"""
from approvals.models import ApprovalStatus
from exceptions import AppBaseException
from constants import ERR_APPROVAL_INVALID_ACTION, ERR_APPROVAL_ALREADY_ACTED


_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING:    {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED},
    ApprovalStatus.APPROVED:   {ApprovalStatus.PROCESSING},
    ApprovalStatus.PROCESSING: {ApprovalStatus.COMPLETED, ApprovalStatus.FAILED},
    ApprovalStatus.COMPLETED:  {ApprovalStatus.SEEN},
    ApprovalStatus.FAILED:     {ApprovalStatus.PENDING},
    ApprovalStatus.REJECTED:   {ApprovalStatus.SEEN},
    ApprovalStatus.SEEN:       set(),
}

_TERMINAL: frozenset[ApprovalStatus] = frozenset({
    ApprovalStatus.APPROVED,
    ApprovalStatus.REJECTED,
    ApprovalStatus.COMPLETED,
    ApprovalStatus.FAILED,
    ApprovalStatus.SEEN,
})


class ApprovalStateManager:

    @staticmethod
    def transition(current: ApprovalStatus, target: ApprovalStatus) -> ApprovalStatus:
        if current in _TERMINAL and current != ApprovalStatus.FAILED:
            raise AppBaseException(ERR_APPROVAL_ALREADY_ACTED, status_code=409)
        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            raise AppBaseException(
                f"{ERR_APPROVAL_INVALID_ACTION}: {current} → {target}", status_code=409
            )
        return target
