import csv
import random

from fastapi import APIRouter
from pydantic import BaseModel

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
    options: CreateConversationOptions,
) -> conversation_handler.Conversation:
    user_name = "Kyle"
    messages = users["0053c352-d227-40b9-989c-78ec216d3a21"]
    user_info = await generate_user_info(messages, user_name)
    return await conversation_handler.create_conversation(user_info, options.level)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
) -> conversation_handler.Conversation:
    return conversation_handler.get_conversation(conversation_id)


@router.post("/{conversation_id}/next")
async def progress_conversation(
    conversation_id: str, option: int | None = None
) -> conversation_handler.ConversationEvent:
    return await conversation_handler.progress_conversation(conversation_id, option)
