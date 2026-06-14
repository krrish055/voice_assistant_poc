"""AI Orchestrator - Dynamic Multi-Agent Control (Registry Pattern)"""
from typing import Dict, Optional, Any, List
from uuid import uuid4
from datetime import datetime
from string import Template
import asyncio

from admin.domain.models import Agent, AgentConfig, AgentStatus, AgentLog
from admin.constants import *

# ═══════════════════════════════════════════════════════════════════════════
# CORE ORCHESTRATION SERVICE (Manager's Control Panel)
# Pattern: Registry + Event-Driven State Management
# ═══════════════════════════════════════════════════════════════════════════

class AIOrchestrator:
    """
    Dynamic Multi-Agent Orchestrator with Real-Time Config Updates
    
    Key Features:
    - Hot-swap agent configs without restart
    - Runtime prompt variable injection
    - Real-time activity monitoring
    - Audit logging for all changes
    """
    
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._configs: Dict[str, AgentConfig] = {}
        self._logs: List[AgentLog] = []
        self._ws_connections: List[Any] = []
        self._agent_repo = None  # Will be set by container
    
    def set_repository(self, agent_repo):
        """Set agent repository for persistence"""
        self._agent_repo = agent_repo  # WebSocket clients
    
    # ═════════════════════════════════════════════════════════════════════
    # REGISTRY MANAGEMENT (Dynamic Agent Registration)
    # ═════════════════════════════════════════════════════════════════════
    
    def register_agent(
        self, name: str, model: str, 
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        system_prompt: str = "",
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register new agent with config"""
        agent_id = f"agent-{uuid4().hex[:8]}"
        
        config = AgentConfig(
            agent_id=agent_id,
            name=name,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            extra_params=extra_params or {}
        )
        
        agent = Agent(
            id=agent_id,
            name=name,
            config=config,
            status=AgentStatus.IDLE
        )
        
        self._agents[agent_id] = agent
        self._configs[agent_id] = config
        
        self._log_event(agent_id, "agent_created", {"name": name, "model": model})
        return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent instance"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        return [agent.to_dict() for agent in self._agents.values()]
    
    # ═════════════════════════════════════════════════════════════════════
    # DYNAMIC CONFIG UPDATES (Hot-Swap Without Restart)
    # ═════════════════════════════════════════════════════════════════════
    
    def update_agent_config(
        self, agent_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        MANAGER'S CONTROL ENDPOINT
        Update agent config in real-time without code changes
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        config = agent.config
        changes = {}
        
        if temperature is not None:
            changes["temperature"] = f"{config.temperature} → {temperature}"
            config.temperature = temperature
        
        if max_tokens is not None:
            changes["max_tokens"] = f"{config.max_tokens} → {max_tokens}"
            config.max_tokens = max_tokens
        
        if system_prompt is not None:
            changes["system_prompt"] = "updated"
            config.system_prompt = system_prompt
        
        if model is not None:
            changes["model"] = f"{config.model} → {model}"
            config.model = model
        
        if extra_params:
            config.extra_params.update(extra_params)
            changes["extra_params"] = list(extra_params.keys())
        
        agent.update_config(config)
        self._configs[agent_id] = config
        
        # 🔥 PERSIST TO REPOSITORY/DATABASE
        if self._agent_repo:
            self._agent_repo.update(agent)
        
        self._log_event(agent_id, "config_update", changes, user="manager")
        self._broadcast_update(agent_id, "config_changed", changes)
        
        return True
    
    def get_agent_config(self, agent_id: str) -> Optional[Dict]:
        """Get current agent configuration"""
        config = self._configs.get(agent_id)
        return config.to_dict() if config else None
    
    # ═════════════════════════════════════════════════════════════════════
    # RUNTIME PROMPT TEMPLATING (Dynamic Variable Injection)
    # ═════════════════════════════════════════════════════════════════════
    
    def render_prompt(
        self, agent_id: str,
        runtime_vars: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Render prompt with runtime variables
        Supports: "You are ${role} assistant for ${company}"
        """
        config = self._configs.get(agent_id)
        if not config or not config.system_prompt:
            return None
        
        template = Template(config.system_prompt)
        rendered = template.safe_substitute(**(runtime_vars or {}))
        
        return rendered
    
    # ═════════════════════════════════════════════════════════════════════
    # AGENT LIFECYCLE CONTROL
    # ═════════════════════════════════════════════════════════════════════
    
    def restart_agent(self, agent_id: str) -> bool:
        """Reset agent memory/state"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.reset_memory()
        self._log_event(agent_id, "agent_restarted", {})
        self._broadcast_update(agent_id, "agent_restarted", {})
        
        return True
    
    def pause_agent(self, agent_id: str) -> bool:
        """Pause agent execution"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.status = AgentStatus.PAUSED
        agent.is_active = False
        self._log_event(agent_id, "agent_paused", {})
        
        return True
    
    def resume_agent(self, agent_id: str) -> bool:
        """Resume paused agent"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.status = AgentStatus.IDLE
        agent.is_active = True
        self._log_event(agent_id, "agent_resumed", {})
        
        return True
    
    # ═════════════════════════════════════════════════════════════════════
    # REAL-TIME MONITORING (Live Activity Logs)
    # ═════════════════════════════════════════════════════════════════════
    
    def get_agent_logs(
        self, agent_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get agent activity logs"""
        logs = [
            log.to_dict() for log in self._logs
            if log.agent_id == agent_id
        ]
        return logs[-limit:]
    
    def get_all_logs(self, limit: int = 100) -> List[Dict]:
        """Get system-wide logs"""
        return [log.to_dict() for log in self._logs[-limit:]]
    
    # ═════════════════════════════════════════════════════════════════════
    # WEBSOCKET SUPPORT (Real-Time Dashboard Updates)
    # ═════════════════════════════════════════════════════════════════════
    
    def register_ws_client(self, websocket: Any) -> None:
        """Register WebSocket connection for live updates"""
        self._ws_connections.append(websocket)
    
    def unregister_ws_client(self, websocket: Any) -> None:
        """Remove WebSocket connection"""
        if websocket in self._ws_connections:
            self._ws_connections.remove(websocket)
    
    async def _broadcast_update(
        self, agent_id: str,
        event_type: str,
        data: Dict
    ) -> None:
        """Broadcast real-time updates to connected clients"""
        message = {
            "agent_id": agent_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected WebSocket clients
        for ws in self._ws_connections[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self._ws_connections.remove(ws)
    
    # ═════════════════════════════════════════════════════════════════════
    # AUDIT LOGGING
    # ═════════════════════════════════════════════════════════════════════
    
    def _log_event(
        self, agent_id: str,
        event_type: str,
        details: Dict,
        user: str = "system"
    ) -> None:
        """Log all state changes for audit trail"""
        log = AgentLog(
            id=f"log-{uuid4().hex[:8]}",
            agent_id=agent_id,
            event_type=event_type,
            details=details,
            user=user
        )
        self._logs.append(log)
        
        # Keep only last 1000 logs in memory
        if len(self._logs) > 1000:
            self._logs = self._logs[-1000:]


# Global orchestrator instance
orchestrator = AIOrchestrator()
