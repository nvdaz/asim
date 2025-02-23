from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from api.schemas.utc_datetime import UTCDatetime

from .objectid import PyObjectId


class Options(BaseModel):
    feedback_mode: Literal["on-suggestion", "on-submit"] = "on-submit"
    suggestion_generation: Literal["content-inspired", "random"] = "content-inspired"
    enabled_objectives: Annotated[
        list[
            Literal[
                "non-literal-emoji",
                "non-literal-figurative",
                "yes-no-question",
                "blunt",
            ]
        ],
        Field(min_length=1, max_length=4),
    ] = ["non-literal-emoji", "non-literal-figurative", "yes-no-question", "blunt"]
    gap: bool = False


default_options = Options(
    feedback_mode="on-suggestion", suggestion_generation="content-inspired"
)


class Feedback(BaseModel):
    title: str
    body: str


class ChatMessage(BaseModel):
    sender: str
    content: str
    created_at: UTCDatetime


class InChatFeedback(BaseModel):
    feedback: Feedback
    alternative: str | None = None
    alternative_feedback: str | None = None
    created_at: UTCDatetime
    rating: int | None = None


chat_message_list_adapter = TypeAdapter(list[ChatMessage | InChatFeedback])


class Suggestion(BaseModel):
    message: str
    problem: str | None = None
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
    options: Options = default_options
    messages: list[ChatMessage | InChatFeedback] = []
    agent: str
    last_updated: UTCDatetime
    agent_typing: bool = False
    loading_feedback: bool = False
    generating_suggestions: int = 0
    unread: bool = False
    objectives_used: list[str] = []
    state: str = "no-objective"
    suggestions: list[Suggestion] | None = None
    last_suggestions: list[Suggestion] | None = None
    events: list[ChatEvent] = []
    checkpoint_rate: bool = False
    introduction: str = "**NO INTRODUCTION GENERATED**"
    scenario: str = "**NO SCENARIO GENERATED**"
    introduction_seen: bool = False


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
    loading_feedback: bool
    generating_suggestions: int
    messages: list[ChatMessage | InChatFeedback]
    suggestions: list[Suggestion] | None
    checkpoint_rate: bool
    introduction: str
    introduction_seen: bool
    options: Options

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
