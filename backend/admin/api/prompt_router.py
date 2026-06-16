from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Optional
from pydantic import BaseModel, Field

from admin.core.container import container
from admin.constants import SUCCESS_CODE, NOT_FOUND_CODE, MAX_SYSTEM_PROMPT_LENGTH

router = APIRouter(prefix="/api/admin/agents", tags=["Prompts"])


class SavePromptRequest(BaseModel):
    template: str = Field(..., max_length=MAX_SYSTEM_PROMPT_LENGTH)
    variables: Optional[Dict[str, str]] = None


class UpdateVariablesRequest(BaseModel):
    variables: Dict[str, str]


@router.get("/{agent_id}/prompt")
def get_prompt(agent_id: str) -> Dict:
    template = container.prompt_service.get_template(agent_id)
    if not template:
        return {"status": NOT_FOUND_CODE, "template": None}
    return {"status": SUCCESS_CODE, "template": template}


@router.post("/{agent_id}/prompt")
def save_prompt(agent_id: str, request: SavePromptRequest) -> Dict:
    template_id = container.prompt_service.save_template(
        agent_id=agent_id, template_str=request.template, variables=request.variables
    )
    return {"status": SUCCESS_CODE, "template_id": template_id}


@router.patch("/{agent_id}/prompt/variables")
def update_variables(agent_id: str, request: UpdateVariablesRequest) -> Dict:
    try:
        ok = container.prompt_service.update_variables(agent_id, request.variables)
        if not ok:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"status": SUCCESS_CODE, "message": "Variables updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/prompt/render")
def render_prompt(agent_id: str, runtime_vars: Optional[Dict[str, str]] = Body(None)) -> Dict:
    """Render dynamic prompt with ${variable} substitution."""
    rendered = container.prompt_service.render_template(agent_id, runtime_vars)
    if rendered is None:
        raise HTTPException(status_code=404, detail="No template found for agent")
    return {"status": SUCCESS_CODE, "rendered_prompt": rendered,
            "variables_injected": list(runtime_vars.keys()) if runtime_vars else []}
