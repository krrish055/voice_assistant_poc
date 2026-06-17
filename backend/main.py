import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from exceptions import AppBaseException
from handlers import global_app_exception_handler
from config import get_allowed_origins
from graph.graph_client import graph_client
from admin.api import router as admin_router
from api.voice_router import router as voice_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)

app = FastAPI(title="InTimeTec AI Voice Node Gateway")


@app.on_event("startup")
async def startup():
    graph_client.verify()


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(voice_router)
app.add_exception_handler(AppBaseException, global_app_exception_handler)


@app.get("/api/conversations/{user_id}")
def get_conversations(user_id: str) -> list:
    from graph.graph_repository import graph_repo
    return graph_repo.get_conversations_by_user(user_id)
