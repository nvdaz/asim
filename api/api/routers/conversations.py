import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel

from api.auth.deps import CurrentInternalAuth, CurrentUser
from api.db import auth_tokens, users
from api.schemas.chat import ChatInfo
from api.schemas.conversation import (
    ConversationStage,
    ConversationStageStr,
    PregenerateOptions,
    SelectOption,
    conversation_stage_from_str,
)
from api.schemas.objectid import PyObjectId
from api.services import chat_handler, conversation_handler

router = APIRouter(prefix="/conversations", tags=["conversations"])

router_chats = APIRouter(prefix="/chats", tags=["chats"])


def _get_conversation_stage(stage: ConversationStageStr) -> ConversationStage:
    return conversation_stage_from_str(stage)


ConversationStageFromQuery = Annotated[
    ConversationStage, Depends(_get_conversation_stage)
]


@router.post(
    "/",
    status_code=201,
    responses={
        400: {"description": "User not initialized"},
        401: {"description": "Stage not unlocked"},
    },
)
async def create_conversation(
    current_user: CurrentUser,
    stage: ConversationStageFromQuery,
) -> conversation_handler.Conversation:
    if not current_user.init:
        raise HTTPException(status_code=400, detail="User not initialized")

    try:
        conversation = await conversation_handler.create_conversation(
            current_user,
            stage,
        )
    except conversation_handler.StageNotUnlocked as e:
        raise HTTPException(status_code=401, detail="Stage not unlocked") from e

    return conversation


class ListConversationOptions(BaseModel):
    stage: ConversationStage


@router.get("/")
async def list_conversations(
    current_user: CurrentUser,
    stage: ConversationStageFromQuery,
) -> list[conversation_handler.ConversationDescriptor]:
    return await conversation_handler.list_conversations(current_user.id, stage)


@router.get("/{conversation_id}")
async def get_conversation(
    current_user: CurrentUser,
    conversation_id: PyObjectId,
) -> conversation_handler.Conversation | None:
    res = await conversation_handler.get_conversation(conversation_id, current_user.id)

    return res


@router.post("/{conversation_id}/next")
async def progress_conversation(
    current_user: CurrentUser,
    conversation_id: PyObjectId,
    option: SelectOption,
) -> conversation_handler.ConversationStep:
    try:
        return await conversation_handler.progress_conversation(
            conversation_id, current_user, option
        )
    except conversation_handler.InvalidSelection as e:
        raise HTTPException(status_code=400, detail="Invalid selection") from e


@router.post("/pregenerate", status_code=204)
async def pregenerate_conversation(
    _: CurrentInternalAuth,
    options: PregenerateOptions,
):
    await conversation_handler.pregenerate_conversation(options.user_id, options.stage)


@router.websocket("/ws")
async def ws_endpoint(
    ws: WebSocket,
):
    await asyncio.sleep(1)
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


@router_chats.post("/")
async def list_chats(
    current_user: CurrentUser,
) -> list[ChatInfo]:
    return await chat_handler.get_chats(current_user)
