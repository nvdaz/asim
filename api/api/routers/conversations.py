import random

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from api.auth.deps import CurrentUser
from api.schemas.objectid import PyObjectId
from api.services import conversation_handler

router = APIRouter(prefix="/conversations", tags=["conversations"])

random.seed(0)


@router.post(
    "/", status_code=201, responses={400: {"description": "User not initialized"}}
)
async def create_conversation(
    current_user: CurrentUser,
    options: conversation_handler.CreateConversationOptions,
) -> conversation_handler.Conversation:
    if not current_user.root.init:
        raise HTTPException(status_code=400, detail="User not initialized")

    conversation = await conversation_handler.create_conversation(
        current_user.root.id, current_user.root.persona, options
    )

    return jsonable_encoder(conversation)


@router.get("/")
async def list_conversations(
    current_user: CurrentUser,
    level: int | None = None,
) -> list[conversation_handler.LevelConversationDescriptor]:
    return await conversation_handler.list_conversations(current_user.root.id, level)


@router.get("/{conversation_id}")
async def get_conversation(
    current_user: CurrentUser,
    conversation_id: PyObjectId,
) -> conversation_handler.Conversation:
    res = await conversation_handler.get_conversation(
        conversation_id, current_user.root.id
    )

    return res


@router.post("/{conversation_id}/next")
async def progress_conversation(
    current_user: CurrentUser, conversation_id: PyObjectId, option: int | None = None
) -> conversation_handler.ConversationEvent:
    return await conversation_handler.progress_conversation(
        conversation_id, current_user.root.id, option
    )
