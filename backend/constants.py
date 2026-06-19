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

# ── Background Job Engine ─────────────────────────────────────────────────────
MSG_JOB_QUEUED              = "Your report is being generated in the background. You will be notified when it is ready."
MSG_JOB_COMPLETED           = "Your report is ready. You can download it now."
MSG_JOB_FAILED              = "Your report could not be generated. Please try again."
ERR_JOB_NOT_FOUND           = "Job not found."
ERR_JOB_INVALID_TRANSITION  = "Invalid job state transition."

# ── Approval Workflow ──────────────────────────────────────────────────────────
MSG_APPROVAL_PENDING        = "Your request requires administrator approval. You will be notified once it is reviewed."
MSG_APPROVAL_APPROVED       = "Your request has been approved and is now being processed."
MSG_APPROVAL_REJECTED       = "Your request was not approved by the administrator."
ERR_APPROVAL_NOT_FOUND      = "Approval request not found."
ERR_APPROVAL_INVALID_ACTION = "Invalid approval action."
ERR_APPROVAL_ALREADY_ACTED  = "This approval request has already been actioned."

# ── Notification Center ─────────────────────────────────────────────────────────
NOTIF_JOB_COMPLETED         = "Your background report job has completed successfully."
NOTIF_JOB_FAILED            = "Your background report job failed. Please retry."
NOTIF_APPROVAL_APPROVED     = "Your restricted request has been approved."
NOTIF_APPROVAL_REJECTED     = "Your restricted request was rejected by an administrator."
ERR_NOTIFICATION_NOT_FOUND  = "Notification not found."
