"""
admin/api/approvals_router.py

Endpoints: query pending approvals, action an approval.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel

from approvals.models import ApprovalAction
from admin.constants import SUCCESS_CODE
from constants import ERR_APPROVAL_NOT_FOUND, ERR_APPROVAL_INVALID_ACTION
from services.container import approval_service
from exceptions import AppBaseException

router = APIRouter(prefix="/api/admin/approvals", tags=["Approvals"])


class ApprovalActionRequest(BaseModel):
    action:      ApprovalAction
    reviewed_by: str
    notes:       Optional[str] = None


@router.get("")
def list_pending(limit: int = 50) -> Dict:
    approvals = approval_service.get_pending(limit=limit)
    return {
        "status": SUCCESS_CODE,
        "approvals": [a.to_dict() for a in approvals],
        "total": len(approvals),
    }


@router.get("/{approval_id}")
def get_approval(approval_id: str) -> Dict:
    approval = approval_service.get_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=ERR_APPROVAL_NOT_FOUND)
    return {"status": SUCCESS_CODE, "approval": approval.to_dict()}


@router.post("/{approval_id}/action")
async def action_approval(approval_id: str, request: ApprovalActionRequest) -> Dict:
    try:
        approval = await approval_service.process_action(
            approval_id=approval_id,
            action=request.action,
            reviewed_by=request.reviewed_by,
            notes=request.notes,
        )
        return {"status": SUCCESS_CODE, "approval": approval.to_dict()}
    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
