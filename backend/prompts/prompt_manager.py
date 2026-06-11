# prompts/prompt_manager.py

from config.runtime_state import runtime_config
from prompts.system_prompts import COMPLIANCE_AGENT_BASE

def get_active_system_prompt() -> str:
    """
    Combines the production base compliance guide with any hot-swapped custom instructions 
    pushed from the Admin Portal at runtime.
    """
    # Agar admin ne dynamic screen se alag instructions bheje hain toh use merge karo
    custom_layer = runtime_config.custom_system_instruction
    
    final_prompt = f"{COMPLIANCE_AGENT_BASE}\n\n[ADMIN OVERRIDE CONSTRAINTS]:\n{custom_layer}"
    return final_prompt