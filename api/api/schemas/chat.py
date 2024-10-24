from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from api.schemas.utc_datetime import UTCDatetime

from .objectid import PyObjectId


class ChatMessage(BaseModel):
    sender: str
    content: str
    created_at: UTCDatetime


chat_message_list_adapter = TypeAdapter(list[ChatMessage])


class Feedback(BaseModel):
    title: str
    body: str


class Suggestion(BaseModel):
    message: str
    needs_improvement: bool
    objective: str | None
    feedback: Feedback | None = None


suggestion_list_adapter = TypeAdapter(list[Suggestion])


class ChatEvent(BaseModel):
    name: str
    data: Any
    created_at: datetime


chat_event_list_adapter = TypeAdapter(list[ChatEvent])


class BaseChat(BaseModel):
    user_id: PyObjectId
    messages: list[ChatMessage] = []
    agent: str
    last_updated: UTCDatetime
    agent_typing: bool = False
    unread: bool = False
    objectives_used: list[str] = []
    state: str = "no-objective"
    suggestions: list[Suggestion] | None = None
    events: list[ChatEvent] = []


class ChatData(BaseChat):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class Chat(BaseChat):
    id: Annotated[PyObjectId, Field(alias="id")]

    @classmethod
    def from_data(cls, data: ChatData) -> "Chat":
        return cls(**data.model_dump())


class ChatApi(BaseModel):
    id: PyObjectId
    agent: str
    last_updated: UTCDatetime
    unread: bool
    agent_typing: bool
    messages: list[ChatMessage]
    suggestions: list[Suggestion] | None

    @classmethod
    def from_data(cls, data: ChatData) -> "ChatApi":
        return cls(**data.model_dump())


class ChatInfoData(BaseModel):
    id: Annotated[PyObjectId, Field(alias="_id")]
    agent: str
    last_updated: UTCDatetime
    unread: bool

    model_config = ConfigDict(populate_by_name=True)


class ChatInfo(BaseModel):
    id: PyObjectId
    agent: str
    last_updated: UTCDatetime

    @classmethod
    def from_data(cls, data: ChatInfoData) -> "ChatInfo":
        return cls(**data.model_dump())


chat_info_list_adapter = TypeAdapter(list[ChatInfo])
