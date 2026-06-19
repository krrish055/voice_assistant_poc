"""
constants.py

All user-facing response strings in one place.
Change copy here without touching business logic.
"""

# ── Report generation errors ──────────────────────────────────────────────────
ERR_REPORT_LLM_FAILED       = "I ran into an issue generating your report content. Please try again."
ERR_REPORT_BAD_FORMAT       = "The report could not be generated because the AI response was not in the expected format. Please try again."
ERR_REPORT_NO_SECTIONS      = "The report content could not be generated. Please try again."
ERR_REPORT_FILE_SAVE_FAILED = "Your report was generated but the file could not be saved. Please try again."
MSG_REPORT_READY            = "Your report is ready. You can download it now."

# ── General ───────────────────────────────────────────────────────────────────
MSG_PLEASE_SAY_SOMETHING    = "Please say something."
MSG_HOW_CAN_I_HELP          = "How can I help you?"
