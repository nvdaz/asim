from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from api.auth.deps import CurrentUser
from api.db import auth_tokens, users
from api.schemas.chat import ChatInfo
from api.schemas.conversation import (
    ConversationStage,
    ConversationStageStr,
    conversation_stage_from_str,
)
from api.services import chat_handler

router = APIRouter(prefix="/conversations", tags=["conversations"])

router_chats = APIRouter(prefix="/chats", tags=["chats"])


def _get_conversation_stage(stage: ConversationStageStr) -> ConversationStage:
    return conversation_stage_from_str(stage)


ConversationStageFromQuery = Annotated[
    ConversationStage, Depends(_get_conversation_stage)
]


@router.websocket("/ws")
async def ws_endpoint(
    ws: WebSocket,
):
    try:
        await ws.accept()

        credentials = await ws.receive_json()

        token = await auth_tokens.get(credentials["token"])

        if not token:
            await ws.send_json({"error": "Invalid token"})
            await ws.close()
            return

        user_id = token.user_id

        user = await users.get(user_id)

        if not user:
            await ws.send_json({"error": "User not found"})
            await ws.close()
            return

        await chat_handler.handle_connection(ws, user)
    except WebSocketDisconnect:
        pass


@router_chats.post("/")
async def list_chats(
    current_user: CurrentUser,
) -> list[ChatInfo]:
    return await chat_handler.get_chats(current_user)
