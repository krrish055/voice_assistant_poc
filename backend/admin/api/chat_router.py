from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel, Field

from admin.core.container import container
from registry.agent_registry import registry
from admin.constants import SUCCESS_CODE

router = APIRouter(prefix="/api/admin/agents", tags=["Chat"])


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    variables: Optional[Dict[str, str]] = None


@router.get("/{agent_id}/chat")
def get_chat_history(agent_id: str, limit: int = 50) -> Dict:
    messages = container.chat_service.get_chat_history(agent_id, limit)
    return {"status": SUCCESS_CODE, "agent_id": agent_id, "messages": messages}


@router.post("/{agent_id}/chat")
async def send_message(agent_id: str, request: SendMessageRequest) -> Dict:
    agent = registry.get(agent_id)
    if not agent or not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent not available")
    try:
        result = await container.chat_service.send_message_async(
            agent_id, request.content, request.variables
        )
        return {"status": SUCCESS_CODE, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}/chat")
def clear_chat(agent_id: str) -> Dict:
    container.chat_service.clear_history(agent_id)
    return {"status": SUCCESS_CODE, "message": f"Chat cleared for '{agent_id}'"}
