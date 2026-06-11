# config/runtime_state.py

class RuntimeState:
    def __init__(self):
        # Default state - Admin portal endpoints isko dynamically runtime par change kar sakte hain
        self.temperature: float = 0.7
        self.max_tokens: int = 1000
        self.custom_system_instruction: str = (
            "You are an expert AI Voice Assistant for InTimeTec Compliance. "
            "Keep your responses crisp, direct, and under 3 sentences for fluid voice delivery."
        )

    def update_config(self, temperature: float = None, custom_instruction: str = None):
        if temperature is not None:
            self.temperature = max(0.0, min(2.0, temperature))  # Bounds checking
        if custom_instruction is not None:
            self.custom_system_instruction = custom_instruction.strip()

# Global state instance jise pipeline aur endpoints access karenge
runtime_config = RuntimeState()