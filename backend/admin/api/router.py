from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

from admin.api.agents_router import router as agents_router
from admin.api.chat_router import router as chat_router
from admin.api.prompt_router import router as prompt_router
from admin.api.approvals_router import router as approvals_router
from admin.api.jobs_router import router as jobs_router
from admin.api.notifications_router import router as notifications_router
from registry.agent_registry import registry
from admin.constants import SUCCESS_CODE

router = APIRouter()
router.include_router(agents_router)
router.include_router(chat_router)
router.include_router(prompt_router)
router.include_router(approvals_router)
router.include_router(jobs_router)
router.include_router(notifications_router)

_ws_clients: List[WebSocket] = []


async def broadcast(event: str, data: Dict) -> None:
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json({"event": event, "data": data})
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


@router.get("/api/admin/health")
def health() -> Dict:
    agents = registry.list_all()
    active = sum(1 for a in agents if a.get("is_active"))
    return {"status": SUCCESS_CODE, "total_agents": len(agents), "active_agents": active}


@router.websocket("/api/admin/ws/monitor")
async def ws_monitor(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        await websocket.send_json({"event": "initial_state", "data": {"agents": registry.list_all()}})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"event": "pong", "data": {}})
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
