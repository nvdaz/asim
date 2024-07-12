import asyncio
import random
from typing import Literal, Union

from bson import ObjectId
from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.db import conversations
from api.schemas.conversation import (
    ApMessageLogEntry,
    BaseConversationData,
    Conversation,
    ConversationDescriptor,
    ConversationLogEntry,
    ConversationNormalInternal,
    ConversationWaitingInternal,
    FeedbackLogEntry,
    Message,
    MessageOption,
    NpMessageOptionsLogEntry,
    NpMessageSelectedLogEntry,
)
from api.schemas.persona import Persona

from .conversation_generation import generate_conversation_info
from .feedback_generation import Feedback, generate_feedback
from .flow_state.base import ApFlowState, FeedbackFlowState, NpFlowState
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL
from .message_generation import generate_message

LEVELS = [FIGURATIVE_LANGUAGE_LEVEL, BLUNT_LANGUAGE_LEVEL]


class NpMessageEvent(BaseModel):
    type: Literal["np"] = "np"
    options: list[str]


class ApMessageEvent(BaseModel):
    type: Literal["ap"] = "ap"
    content: str


class FeedbackEvent(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback


class ConversationEvent(RootModel):
    root: Annotated[
        Union[NpMessageEvent, ApMessageEvent, FeedbackEvent],
        Field(discriminator="type"),
    ]


async def create_conversation(
    user_id: ObjectId, user: Persona, level: int
) -> Conversation:
    conversation_info = await generate_conversation_info(user_id, user)

    data = BaseConversationData(
        user_id=user_id,
        level=level,
        info=conversation_info,
        state=ConversationNormalInternal(
            state=(
                LEVELS[level].initial_np_state
                if conversation_info.scenario.is_user_initiated
                else LEVELS[level].initial_ap_state
            )
        ),
        events=[],
        messages=[],
        last_feedback_received=0,
    )

    conversation = await conversations.insert(data)

    return Conversation.from_data(conversation)


async def list_conversations(
    user_id: ObjectId, level: int | None = None
) -> list[ConversationDescriptor]:
    convs = await conversations.list(user_id, level)
    return [ConversationDescriptor.from_data(c) for c in convs]


async def get_conversation(
    conversation_id: ObjectId, user_id: ObjectId
) -> Conversation:
    conversation = await conversations.get(conversation_id, user_id)
    return Conversation.from_data(conversation)


async def progress_conversation(
    conversation_id: ObjectId, user_id: ObjectId, option: int | None
) -> ConversationEvent:
    conversation = await conversations.get(conversation_id, user_id)

    if isinstance(conversation.state, ConversationWaitingInternal):
        assert option is not None
        response = conversation.state.options[option]

        conversation.events.append(
            ConversationLogEntry(
                root=NpMessageSelectedLogEntry(
                    message=response.response,
                )
            )
        )

        conversation.messages.root.append(
            Message(sender=conversation.info.user.name, message=response.response)
        )

        conversation.state = ConversationNormalInternal(state=response.next)

    assert isinstance(conversation.state, ConversationNormalInternal)

    state_data = (
        LEVELS[conversation.level].get_flow_state(conversation.state.state).root
    )

    if isinstance(state_data, NpFlowState):
        responses = await asyncio.gather(
            *[
                generate_message(
                    conversation.info.user,
                    conversation.info.scenario.user_scenario,
                    conversation.messages,
                    opt.prompt,
                )
                for opt in state_data.options
            ]
        )

        options = [
            MessageOption(
                response=response,
                next=opt.next,
            )
            for response, opt in zip(responses, state_data.options)
        ]

        random.shuffle(options)

        conversation.events.append(
            ConversationLogEntry(
                root=NpMessageOptionsLogEntry(
                    state=conversation.state.state.root.id,
                    options=options,
                )
            )
        )

        conversation.state = ConversationWaitingInternal(options=options)

        result = NpMessageEvent(options=[o.response for o in options])
    elif isinstance(state_data, ApFlowState):
        opt = random.choice(state_data.options)

        response = await generate_message(
            conversation.info.subject,
            conversation.info.scenario.subject_scenario,
            conversation.messages,
            opt.prompt,
        )

        conversation.events.append(
            ConversationLogEntry(
                root=ApMessageLogEntry(
                    state=conversation.state.state.root.id,
                    message=response,
                )
            )
        )

        conversation.messages.root.append(
            Message(sender=conversation.info.subject.name, message=response)
        )

        conversation.state = ConversationNormalInternal(state=opt.next)

        result = ApMessageEvent(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(conversation, state_data)
        conversation.last_feedback_received = len(conversation.messages.root)

        conversation.events.append(
            ConversationLogEntry(
                root=FeedbackLogEntry(
                    state=conversation.state.state.root.id,
                    content=response,
                )
            )
        )

        if response.follow_up is not None:
            conversation.messages.root.append(
                Message(
                    sender=conversation.info.user.name,
                    message=response.follow_up,
                )
            )
            conversation.state = ConversationNormalInternal(
                state=state_data.next_needs_improvement
            )
        else:
            conversation.state = ConversationNormalInternal(state=state_data.next_ok)

        result = FeedbackEvent(content=response)
    else:
        raise RuntimeError(f"Invalid state: {state_data}")

    await conversations.update(conversation)

    return ConversationEvent(root=result)
