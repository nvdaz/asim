from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .objectid import PyObjectId


class ChatMessage(BaseModel):
    sender: str
    content: str
    created_at: datetime


chat_message_list_adapter = TypeAdapter(list[ChatMessage])


class BaseChat(BaseModel):
    user_id: PyObjectId
    messages: list[ChatMessage] = []
    agent: str
    last_updated: datetime
    agent_typing: bool = False
    unread: bool = False


class ChatData(BaseChat):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class Chat(BaseChat):
    id: Annotated[PyObjectId, Field(alias="id")]

    @classmethod
    def from_data(cls, data: ChatData) -> "Chat":
        return cls(**data.model_dump())


class ChatInfoData(BaseModel):
    id: Annotated[PyObjectId, Field(alias="_id")]
    agent: str
    last_updated: datetime
    unread: bool

    model_config = ConfigDict(populate_by_name=True)


class ChatInfo(BaseModel):
    id: PyObjectId
    agent: str
    last_updated: datetime

    @classmethod
    def from_data(cls, data: ChatInfoData) -> "ChatInfo":
        return cls(**data.model_dump())


chat_info_list_adapter = TypeAdapter(list[ChatInfo])
