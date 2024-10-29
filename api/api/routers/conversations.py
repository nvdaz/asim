import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from api.db import auth_tokens, users
from api.schemas.conversation import (
    ConversationStage,
    ConversationStageStr,
    conversation_stage_from_str,
)
from api.services import websocket_handler
from api.services.connection_manager import Connections

router = APIRouter(prefix="/conversations", tags=["conversations"])

router_chats = APIRouter(prefix="/chats", tags=["chats"])


def _get_conversation_stage(stage: ConversationStageStr) -> ConversationStage:
    return conversation_stage_from_str(stage)


ConversationStageFromQuery = Annotated[
    ConversationStage, Depends(_get_conversation_stage)
]

connections = Connections()


@router.websocket("/ws")
async def ws_endpoint(
    ws: WebSocket,
):
    connection_id = secrets.token_urlsafe(32)
    connection_manager = None
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

        await ws.send_json({"type": "connected", "connection_id": connection_id})

        connection_manager = connections.get(user_id)

        await websocket_handler.handle_connection(
            ws, connection_manager, connection_id, user
        )
    except WebSocketDisconnect:
        if connection_manager:
            connection_manager.close(connection_id)
