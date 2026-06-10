# ── Global Exception Handler ──────────────────────────────────────────────────
# Single Responsibility: transforms domain exceptions into HTTP JSON responses.
# No business logic, no exception definitions — mapping only.

from fastapi import Request
from fastapi.responses import JSONResponse

from exceptions import AppBaseException


async def global_app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'success'   : False,
            'error_type': type(exc).__name__,
            'message'   : exc.message,
        },
    )
