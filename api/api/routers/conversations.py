from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException

from api.auth.deps import CurrentUser
from api.schemas.conversation import (
    ConversationOptions,
    LevelConversationOptions,
    PlaygroundConversationOptions,
    SelectOption,
)
from api.schemas.objectid import PyObjectId
from api.services import conversation_handler

router = APIRouter(prefix="/conversations", tags=["conversations"])


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
    options: conversation_handler.ConversationOptions,
) -> conversation_handler.Conversation:
    if not current_user.init:
        raise HTTPException(status_code=400, detail="User not initialized")

    try:
        conversation = await conversation_handler.create_conversation(
            current_user, options
        )
    except conversation_handler.StageNotUnlocked as e:
        raise HTTPException(status_code=401, detail="Stage not unlocked") from e

    return conversation


async def get_conversation_options(
    type: Literal["level", "playground"], level: int | None = None
) -> ConversationOptions:
    if type == "level" and level is not None:
        return LevelConversationOptions(type="level", level=level)
    elif type == "playground":
        return PlaygroundConversationOptions(type="playground")
    else:
        raise HTTPException(status_code=400, detail="Invalid conversation query")


@router.get("/")
async def list_conversations(
    current_user: CurrentUser,
    options: Annotated[
        conversation_handler.ConversationOptions, Depends(get_conversation_options)
    ],
) -> list[conversation_handler.ConversationDescriptor]:
    return await conversation_handler.list_conversations(current_user.id, options)


@router.get("/{conversation_id}")
async def get_conversation(
    current_user: CurrentUser,
    conversation_id: PyObjectId,
) -> conversation_handler.Conversation:
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
