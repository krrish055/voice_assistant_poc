"""
services/container.py

Single responsibility: construct and wire application-level singletons.

Dependency order:
  1. SessionMemoryService created
  2. Registry seeded (ReportAgent receives memory)
  3. VoicePipeline created
  4. OrchestratorAgent wired with pipeline + memory
"""
from services.session_memory import SessionMemoryService
from services.pipeline import VoicePipeline
from agents.orchestrator_agent import OrchestratorAgent
from registry.agent_registry import registry

memory:         SessionMemoryService = SessionMemoryService()
registry.seed_defaults(memory=memory)

voice_pipeline: VoicePipeline        = VoicePipeline()
orchestrator:   OrchestratorAgent    = OrchestratorAgent(pipeline=voice_pipeline, memory=memory)
