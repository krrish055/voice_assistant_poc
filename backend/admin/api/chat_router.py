from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel, Field
import asyncio

from admin.core.container import container
from admin.domain.models import ChatMessage
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
def send_message(agent_id: str, request: SendMessageRequest) -> Dict:
    agent = registry.get(agent_id)
    if not agent or not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent not available")
    user_msg = ChatMessage.create_user_message(agent_id, request.content, request.variables)
    container.chat_service._chat_repo.add_message(user_msg)
    ai_content = asyncio.run(container.chat_service._generate_response(agent, request.content))
    ai_msg = ChatMessage.create_ai_message(agent_id, ai_content, request.variables)
    container.chat_service._chat_repo.add_message(ai_msg)
    agent.update_activity()
    return {"status": SUCCESS_CODE, "response": ai_content,
            "user_message": user_msg.to_dict(), "ai_message": ai_msg.to_dict()}


@router.delete("/{agent_id}/chat")
def clear_chat(agent_id: str) -> Dict:
    container.chat_service.clear_history(agent_id)
    return {"status": SUCCESS_CODE, "message": f"Chat cleared for '{agent_id}'"}
