from dataclasses import dataclass, field
from typing import List, Dict, Any
from string import Template

from config import REPORT_HISTORY_WINDOW


@dataclass
class PromptContext:
    agent_name: str
    company: str
    agent_role: str
    session_history: List[Dict] = field(default_factory=list)
    compliance_rules: List[str] = field(default_factory=list)
    runtime_vars: Dict[str, Any] = field(default_factory=dict)
    memory_context: str = ""


def render(template_str: str, variables: Dict[str, Any] = None) -> str:
    return Template(template_str).safe_substitute(**(variables or {}))


def build_prompt(base_template: str, ctx: PromptContext) -> str:
    rules_str = "\n".join(f"- {r}" for r in ctx.compliance_rules)

    base_vars = {
        "agent_name":     ctx.agent_name,
        "company":        ctx.company,
        "agent_role":     ctx.agent_role,
        "memory_context": ctx.memory_context,
        **ctx.runtime_vars,
    }
    parts = [Template(base_template).safe_substitute(**base_vars)]

    # Inject recent turns only for agents that need raw history (compliance, report slot collection)
    # For voice/chat agents the memory_context block in the system prompt is sufficient.
    # Exception: if memory is empty (session start), inject last 6 turns as fallback context.
    memory_present = bool(ctx.memory_context and ctx.memory_context.strip())
    needs_history = ctx.agent_role in ("compliance", "report") or not memory_present
    if ctx.session_history and needs_history:
        turns_to_use = ctx.session_history[-REPORT_HISTORY_WINDOW:] if ctx.agent_role in ("compliance", "report") else ctx.session_history[-6:]
        history_str = "\n".join(
            f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
            for t in turns_to_use
        )
        parts.append(f"\n\n[RECENT CONVERSATION]\n{history_str}")

    if rules_str:
        parts.append(f"\n\n[ACTIVE COMPLIANCE RULES]\n{rules_str}")

    return "".join(parts)
