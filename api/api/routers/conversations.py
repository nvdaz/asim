import csv
import random

from fastapi import APIRouter

from api.services import conversation_service, user_service

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


@router.post("/", status_code=201)
async def create_conversation() -> conversation_service.Conversation:
    user_name = "Kyle"
    messages = users["0053c352-d227-40b9-989c-78ec216d3a21"]
    user_info = await user_service.generate_user(messages, user_name)
    return await conversation_service.create_conversation(user_info)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
) -> conversation_service.Conversation:
    return conversation_service.get_conversation(conversation_id)


@router.post("/{conversation_id}/next")
async def progress_conversation(
    conversation_id: str, option: int | None = None
) -> conversation_service.ConversationEvent:
    return await conversation_service.progress_conversation(conversation_id, option)
