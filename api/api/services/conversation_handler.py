import asyncio
import random
from typing import Literal, Union

from bson import ObjectId
from faker.providers.person.en import Provider
from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.db import conversations
from api.schemas.conversation import (
    ApMessageLogEntry,
    BaseConversationInfo,
    BaseConversationUninitData,
    Conversation,
    ConversationDescriptor,
    ConversationInfo,
    ConversationInitData,
    ConversationLogEntry,
    ConversationNormalInternal,
    ConversationUninitData,
    ConversationWaitingInternal,
    FeedbackLogEntry,
    Message,
    MessageOption,
    Messages,
    NpMessageOptionsLogEntry,
    NpMessageSelectedLogEntry,
)
from api.schemas.persona import Persona

from .conversation_generation import (
    generate_conversation_scenario,
    generate_subject_persona,
)
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
    user_id: ObjectId, user_persona: Persona, level: int
) -> Conversation:
    subject_name = random.choice(Provider.first_names)
    scenario = await generate_conversation_scenario(user_id, user_persona, subject_name)

    data = BaseConversationUninitData(
        user_id=user_id,
        level=level,
        subject_name=subject_name,
        info=BaseConversationInfo(scenario=scenario),
        user_persona=user_persona,
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

    if isinstance(conversation.root, ConversationUninitData):
        subject_persona = await generate_subject_persona(
            conversation.root.info.scenario.subject_perspective,
            conversation.root.subject_name,
        )
        info = ConversationInfo(
            scenario=conversation.root.info.scenario,
            user=conversation.root.user_persona,
            subject=subject_persona,
        )

        level = conversation.root.level

        conversation.root = ConversationInitData(
            id=conversation.root.id,
            user_id=conversation.root.user_id,
            level=level,
            info=info,
            state=ConversationNormalInternal(
                state=(
                    LEVELS[level].initial_np_state
                    if info.scenario.is_user_initiated
                    else LEVELS[level].initial_ap_state
                )
            ),
            events=[],
            messages=Messages(root=[]),
            last_feedback_received=0,
        )

    if isinstance(conversation.root.state, ConversationWaitingInternal):
        assert option is not None
        response = conversation.root.state.options[option]

        conversation.root.events.append(
            ConversationLogEntry(
                root=NpMessageSelectedLogEntry(
                    message=response.response,
                )
            )
        )

        conversation.root.messages.root.append(
            Message(sender=conversation.root.info.user.name, message=response.response)
        )

        conversation.root.state = ConversationNormalInternal(state=response.next)

    assert isinstance(conversation.root.state, ConversationNormalInternal)

    state_data = (
        LEVELS[conversation.root.level]
        .get_flow_state(conversation.root.state.state)
        .root
    )

    if isinstance(state_data, NpFlowState):
        responses = await asyncio.gather(
            *[
                generate_message(
                    conversation.root.info.user,
                    conversation.root.info.subject,
                    conversation.root.info.scenario.user_perspective,
                    conversation.root.messages,
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

        conversation.root.events.append(
            ConversationLogEntry(
                root=NpMessageOptionsLogEntry(
                    state=conversation.root.state.state.root.id,
                    options=options,
                )
            )
        )

        conversation.root.state = ConversationWaitingInternal(options=options)

        result = NpMessageEvent(options=[o.response for o in options])
    elif isinstance(state_data, ApFlowState):
        opt = random.choice(state_data.options)

        response = await generate_message(
            conversation.root.info.subject,
            conversation.root.info.user,
            conversation.root.info.scenario.subject_perspective,
            conversation.root.messages,
            opt.prompt,
        )

        conversation.root.events.append(
            ConversationLogEntry(
                root=ApMessageLogEntry(
                    state=conversation.root.state.state.root.id,
                    message=response,
                )
            )
        )

        conversation.root.messages.root.append(
            Message(sender=conversation.root.info.subject.name, message=response)
        )

        conversation.root.state = ConversationNormalInternal(state=opt.next)

        result = ApMessageEvent(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(conversation.root, state_data)
        conversation.root.last_feedback_received = len(conversation.root.messages.root)

        conversation.root.events.append(
            ConversationLogEntry(
                root=FeedbackLogEntry(
                    state=conversation.root.state.state.root.id,
                    content=response,
                )
            )
        )

        if response.follow_up is not None:
            options = [
                MessageOption(
                    response=response.follow_up, next=state_data.next_needs_improvement
                )
            ]

            conversation.root.state = ConversationWaitingInternal(options=options)
        else:
            conversation.root.state = ConversationNormalInternal(
                state=state_data.next_ok
            )

        result = FeedbackEvent(content=response)
    else:
        raise RuntimeError(f"Invalid state: {state_data}")

    await conversations.update(conversation)

    return ConversationEvent(root=result)
