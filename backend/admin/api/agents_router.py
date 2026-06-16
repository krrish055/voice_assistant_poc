from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel, Field

from registry.agent_registry import registry
from admin.constants import (
    MAX_AGENT_NAME_LENGTH, MAX_SYSTEM_PROMPT_LENGTH,
    MIN_TEMPERATURE, MAX_TEMPERATURE, MIN_MAX_TOKENS, MAX_MAX_TOKENS, SUCCESS_CODE,
)

router = APIRouter(prefix="/api/admin/agents", tags=["Agents"])


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=MAX_AGENT_NAME_LENGTH)
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    max_tokens: Optional[int] = Field(None, ge=MIN_MAX_TOKENS, le=MAX_MAX_TOKENS)
    system_prompt: Optional[str] = Field(None, max_length=MAX_SYSTEM_PROMPT_LENGTH)
    is_active: Optional[bool] = None


@router.get("")
def list_agents() -> Dict:
    agents = registry.list_all()
    return {"status": SUCCESS_CODE, "agents": agents, "total": len(agents)}


@router.get("/{agent_id}")
def get_agent(agent_id: str) -> Dict:
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"status": SUCCESS_CODE, "agent": agent.to_dict()}


@router.patch("/{agent_id}")
def update_agent(agent_id: str, request: UpdateAgentRequest) -> Dict:
    updates = request.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    ok = registry.update_config(agent_id, **updates)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"status": SUCCESS_CODE, "message": f"Agent '{agent_id}' updated"}


@router.post("/{agent_id}/activate")
def set_active(agent_id: str, active: bool) -> Dict:
    ok = registry.set_active(agent_id, active)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    state = "activated" if active else "deactivated"
    return {"status": SUCCESS_CODE, "message": f"Agent '{agent_id}' {state}"}
