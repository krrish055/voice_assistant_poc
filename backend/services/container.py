"""
services/container.py

Single responsibility: construct and wire application-level singletons.

Dependency order:
  1. MemoryService created
  2. Registry seeded with MemoryService (ReportAgent receives it)
  3. VoicePipeline created
  4. OrchestratorAgent wired with pipeline + memory
"""
from services.memory_service import MemoryService
from services.pipeline import VoicePipeline
from agents.orchestrator_agent import OrchestratorAgent
from registry.agent_registry import registry

memory:         MemoryService     = MemoryService()
registry.seed_defaults(memory=memory)

voice_pipeline: VoicePipeline     = VoicePipeline()
orchestrator:   OrchestratorAgent = OrchestratorAgent(pipeline=voice_pipeline, memory=memory)
