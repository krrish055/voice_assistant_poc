"""
services/container.py
Single responsibility: construct and wire the application-level singletons.

This is the ONLY file that imports both VoicePipeline and OrchestratorAgent.
Neither pipeline.py nor orchestrator_agent.py imports the other — the
circular-import risk is eliminated structurally, not by import ordering tricks.

Consumers import from services/__init__.py, not from here directly.
"""
from services.pipeline import VoicePipeline
from agents.orchestrator_agent import OrchestratorAgent

voice_pipeline: VoicePipeline = VoicePipeline()
orchestrator: OrchestratorAgent = OrchestratorAgent(pipeline=voice_pipeline)
