import csv
import random

from fastapi import APIRouter
from pydantic import BaseModel

from api.auth.deps import CurrentUser
from api.services import conversation_handler
from api.services.user_info import generate_user_info

router = APIRouter(prefix="/conversations", tags=["conversations"])

random.seed(0)

users = {}

with open("./userConversations.csv") as csv_file:
    csv_reader = csv.DictReader(csv_file)

    for row in csv_reader:
        user = row["user_id"]
        if user not in users:
            users[user] = []
        users[user].append((row["message"], row["response"]))


class CreateConversationOptions(BaseModel):
    level: int


@router.post("/", status_code=201)
async def create_conversation(
    current_user: CurrentUser,
    options: CreateConversationOptions,
) -> conversation_handler.Conversation:
    messages = users[str(current_user.user_id)]
    user_info = await generate_user_info(messages, current_user.name)
    return await conversation_handler.create_conversation(
        current_user.user_id, user_info, options.level
    )


@router.get("/{conversation_id}")
async def get_conversation(
    current_user: CurrentUser,
    conversation_id: str,
) -> conversation_handler.Conversation:
    return await conversation_handler.get_conversation(
        conversation_id, current_user.user_id
    )


@router.post("/{conversation_id}/next")
async def progress_conversation(
    current_user: CurrentUser, conversation_id: str, option: int | None = None
) -> conversation_handler.ConversationEvent:
    return await conversation_handler.progress_conversation(
        conversation_id, current_user.user_id, option
    )
