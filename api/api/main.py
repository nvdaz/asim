from fastapi import FastAPI

from .routers import auth, conversations

app = FastAPI(title="Autism Simulator API", version="0.0.1")

app.include_router(conversations.router)
app.include_router(auth.router)
