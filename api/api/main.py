import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .routers import auth, conversations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "http://localhost:5173",
    "https://autsim.pages.dev",
    "https://dev.autsim.pages.dev",
]

app = FastAPI(title="Autism Simulator API", version="0.0.1", debug=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.debug(f"Allowed origins: {origins}")

app.include_router(conversations.router)
app.include_router(conversations.router_chats)
app.include_router(auth.router)
