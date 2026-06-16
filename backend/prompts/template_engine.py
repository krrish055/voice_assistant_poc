from dataclasses import dataclass, field
from typing import List, Dict, Any
from string import Template


@dataclass
class PromptContext:
    agent_name: str
    company: str
    agent_role: str
    session_history: List[Dict] = field(default_factory=list)
    compliance_rules: List[str] = field(default_factory=list)
    runtime_vars: Dict[str, Any] = field(default_factory=dict)


def render(template_str: str, variables: Dict[str, Any] = None) -> str:
    return Template(template_str).safe_substitute(**(variables or {}))


def build_prompt(base_template: str, ctx: PromptContext) -> str:
    history_str = "\n".join(
        f"User: {t.get('user_input', '')}\nAssistant: {t.get('ai_response_text', '')}"
        for t in ctx.session_history[-5:]
    )
    rules_str = "\n".join(f"- {r}" for r in ctx.compliance_rules)

    base_vars = {
        "agent_name": ctx.agent_name,
        "company": ctx.company,
        "agent_role": ctx.agent_role,
        **ctx.runtime_vars,
    }
    parts = [Template(base_template).safe_substitute(**base_vars)]

    if history_str:
        parts.append(f"\n\n[SESSION MEMORY]\n{history_str}")
    if rules_str:
        parts.append(f"\n\n[ACTIVE COMPLIANCE RULES]\n{rules_str}")

    return "".join(parts)
