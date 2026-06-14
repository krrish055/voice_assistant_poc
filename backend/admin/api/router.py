"""Admin API Router - Dynamic Multi-Agent Control Endpoints"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from admin.core import container
from admin.services.orchestrator import orchestrator
from admin.constants import *
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

# ═══════════════════════════════════════════════════════════════════════════
# C4 Level 3: API Layer
# SOLID: Single Responsibility - Each endpoint handles one operation
# ═══════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════

class CreateAgentRequest(BaseModel):
    name: str = Field(..., max_length=MAX_AGENT_NAME_LENGTH)
    model: str = Field(DEFAULT_MODEL)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    max_tokens: int = Field(DEFAULT_MAX_TOKENS, ge=MIN_MAX_TOKENS, le=MAX_MAX_TOKENS)
    system_prompt: str = Field("", max_length=MAX_SYSTEM_PROMPT_LENGTH)

class UpdateAgentRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=MAX_AGENT_NAME_LENGTH)
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    max_tokens: Optional[int] = Field(None, ge=MIN_MAX_TOKENS, le=MAX_MAX_TOKENS)
    system_prompt: Optional[str] = Field(None, max_length=MAX_SYSTEM_PROMPT_LENGTH)
    is_active: Optional[bool] = None

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    variables: Optional[Dict[str, str]] = None

class SavePromptRequest(BaseModel):
    template: str = Field(..., max_length=MAX_SYSTEM_PROMPT_LENGTH)
    variables: Optional[Dict[str, str]] = None

class UpdateVariablesRequest(BaseModel):
    variables: Dict[str, str]

class AgentStatusRequest(BaseModel):
    active: bool

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

# ═══════════════════════════════════════════════════════════════════════════
# Agent Management Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/agents")
def list_agents() -> Dict:
    """Get all agents with live config"""
    agents = orchestrator.list_agents()
    return {
        "status": SUCCESS_CODE,
        "agents": agents,
        "total": len(agents)
    }

@router.get("/agents/{agent_id}")
def get_agent(agent_id: str) -> Dict:
    """Get agent with current config"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"status": SUCCESS_CODE, "agent": agent.to_dict()}

@router.post("/agents")
def create_agent(request: CreateAgentRequest) -> ApiResponse:
    """Register new agent in orchestrator"""
    try:
        agent_id = orchestrator.register_agent(
            name=request.name,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt
        )
        return ApiResponse(
            status=SUCCESS_CODE,
            message=f"Agent '{request.name}' registered successfully",
            data={"agent_id": agent_id}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/agents/{agent_id}")
def update_agent(agent_id: str, request: UpdateAgentRequest) -> ApiResponse:
    """🔥 MANAGER'S ENDPOINT: Hot-swap config without restart"""
    updates = request.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = orchestrator.update_agent_config(
        agent_id=agent_id,
        temperature=updates.get("temperature"),
        max_tokens=updates.get("max_tokens"),
        system_prompt=updates.get("system_prompt"),
        model=updates.get("model")
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return ApiResponse(
        status=SUCCESS_CODE,
        message=f"Agent '{agent_id}' config updated in real-time"
    )

@router.post("/agents/{agent_id}/restart")
def restart_agent(agent_id: str) -> ApiResponse:
    """Restart agent (reset memory/state)"""
    success = orchestrator.restart_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return ApiResponse(
        status=SUCCESS_CODE,
        message=f"Agent '{agent_id}' restarted successfully"
    )

@router.post("/agents/{agent_id}/pause")
def pause_agent(agent_id: str) -> ApiResponse:
    """Pause agent execution"""
    success = orchestrator.pause_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return ApiResponse(
        status=SUCCESS_CODE,
        message=f"Agent '{agent_id}' paused"
    )

@router.post("/agents/{agent_id}/resume")
def resume_agent(agent_id: str) -> ApiResponse:
    """Resume paused agent"""
    success = orchestrator.resume_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return ApiResponse(
        status=SUCCESS_CODE,
        message=f"Agent '{agent_id}' resumed"
    )

@router.get("/agents/{agent_id}/logs")
def get_agent_logs(agent_id: str, limit: int = 50) -> Dict:
    """📊 Real-time agent activity logs"""
    logs = orchestrator.get_agent_logs(agent_id, limit)
    return {
        "status": SUCCESS_CODE,
        "agent_id": agent_id,
        "logs": logs,
        "count": len(logs)
    }

@router.get("/logs")
def get_all_logs(limit: int = 100) -> Dict:
    """System-wide audit logs"""
    logs = orchestrator.get_all_logs(limit)
    return {
        "status": SUCCESS_CODE,
        "logs": logs,
        "count": len(logs)
    }

# ═══════════════════════════════════════════════════════════════════════════
# Chat Monitoring Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/chat")
def get_chat_history(agent_id: str, limit: int = 50) -> Dict:
    """Get chat history for agent"""
    try:
        messages = container.chat_service.get_chat_history(agent_id, limit)
        return {
            "status": SUCCESS_CODE,
            "agent_id": agent_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/chat")
def send_message(agent_id: str, request: SendMessageRequest) -> Dict:
    """Send message to agent using orchestrator's live config"""
    try:
        # Get agent from orchestrator (has live config updates)
        agent = orchestrator.get_agent(agent_id)
        if not agent or not agent.is_active:
            raise ValueError("Agent not available")
        
        # Add user message to chat history
        from admin.domain import ChatMessage
        user_msg = ChatMessage.create_user_message(agent_id, request.content, request.variables)
        container.chat_service._chat_repo.add_message(user_msg)
        
        # Generate AI response using orchestrator's agent (with live temperature)
        ai_content = asyncio.run(container.chat_service._generate_response(agent, request.content))
        ai_msg = ChatMessage.create_ai_message(agent_id, ai_content, request.variables)
        container.chat_service._chat_repo.add_message(ai_msg)
        
        agent.update_activity()
        
        return {
            "status": SUCCESS_CODE,
            "user_message": user_msg.to_dict(),
            "ai_message": ai_msg.to_dict(),
            "response": ai_content
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/agents/{agent_id}/chat")
def clear_chat_history(agent_id: str) -> ApiResponse:
    """Clear chat history"""
    container.chat_service.clear_history(agent_id)
    return ApiResponse(
        status=SUCCESS_CODE,
        message=f"Chat history cleared for agent '{agent_id}'"
    )

# ═══════════════════════════════════════════════════════════════════════════
# Prompt Management Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/prompt")
def get_prompt_template(agent_id: str) -> Dict:
    """Get prompt template"""
    template = container.prompt_service.get_template(agent_id)
    if not template:
        return {
            "status": NOT_FOUND_CODE,
            "message": "No template found",
            "template": None
        }
    return {"status": SUCCESS_CODE, "template": template}

@router.post("/agents/{agent_id}/prompt")
def save_prompt_template(agent_id: str, request: SavePromptRequest) -> ApiResponse:
    """Save/update prompt template"""
    try:
        template_id = container.prompt_service.save_template(
            agent_id=agent_id,
            template_str=request.template,
            variables=request.variables
        )
        return ApiResponse(
            status=SUCCESS_CODE,
            message="Prompt template saved successfully",
            data={"template_id": template_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/agents/{agent_id}/prompt/variables")
def update_prompt_variables(agent_id: str, request: UpdateVariablesRequest) -> ApiResponse:
    """Update prompt variables"""
    try:
        success = container.prompt_service.update_variables(agent_id, request.variables)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return ApiResponse(
            status=SUCCESS_CODE,
            message="Variables updated successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/agents/{agent_id}/prompt/render")
def render_prompt(agent_id: str, runtime_vars: Optional[Dict[str, str]] = Body(None)) -> Dict:
    """🎯 Render prompt with runtime variables (supports ${variable})"""
    rendered = orchestrator.render_prompt(agent_id, runtime_vars)
    if rendered is None:
        raise HTTPException(status_code=404, detail="Agent not found or no prompt set")
    
    return {
        "status": SUCCESS_CODE,
        "rendered_prompt": rendered,
        "variables_injected": list(runtime_vars.keys()) if runtime_vars else []
    }

# ═══════════════════════════════════════════════════════════════════════════
# WebSocket Endpoint - Real-Time Monitoring
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """🔴 LIVE: Real-time agent monitoring dashboard"""
    await websocket.accept()
    orchestrator.register_ws_client(websocket)
    
    try:
        # Send initial state
        agents = orchestrator.list_agents()
        await websocket.send_json({
            "type": "initial_state",
            "agents": agents
        })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client can send requests like {"action": "ping"}
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        orchestrator.unregister_ws_client(websocket)
    except Exception as e:
        orchestrator.unregister_ws_client(websocket)
        print(f"WebSocket error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# System Health & Analytics
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/health")
def health_check() -> Dict:
    """Health check with orchestrator stats"""
    agents = orchestrator.list_agents()
    active_count = sum(1 for a in agents if a.get("is_active"))
    
    return {
        "status": SUCCESS_CODE,
        "service": "Dynamic Multi-Agent Admin",
        "version": "2.0.0",
        "orchestrator": {
            "total_agents": len(agents),
            "active_agents": active_count,
            "paused_agents": len(agents) - active_count
        }
    }
