import asyncio
import random
from typing import Literal, Union

from bson import ObjectId
from faker.providers.job import Provider as JobProvider
from faker.providers.person.en import Provider as PersonProvider
from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.db import conversations
from api.schemas.conversation import (
    ApMessageLogEntry,
    BaseLevelConversationUninitData,
    BasePlaygroundConversationUninitData,
    Conversation,
    ConversationLogEntry,
    ConversationNormalInternal,
    ConversationWaitingInternal,
    FeedbackLogEntry,
    LevelConversation,
    LevelConversationDescriptor,
    LevelConversationInfo,
    LevelConversationInfoUninit,
    LevelConversationInitData,
    LevelConversationUninitData,
    Message,
    MessageOption,
    NpMessageOptionsLogEntry,
    NpMessageSelectedLogEntry,
    PlaygroundConversationInfo,
    PlaygroundConversationInitData,
    PlaygroundConversationUninitData,
    conversation_from_data,
)
from api.schemas.persona import Persona

from .conversation_generation import (
    generate_conversation_scenario,
    generate_subject_persona,
)
from .feedback_generation import Feedback, generate_feedback
from .flow_state.base import (
    ApFlowState,
    FeedbackFlowState,
    NormalApFlowStateRef,
    NormalNpFlowStateRef,
    NpFlowState,
)
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL
from .flow_state.playground import PLAYGROUND_MAPPINGS
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


class CreateLevelConversationOptions(BaseModel):
    type: Literal["level"] = "level"
    level: int


class CreatePlaygroundConversationOptions(BaseModel):
    type: Literal["playground"] = "playground"


CreateConversationOptions = Annotated[
    CreateLevelConversationOptions | CreatePlaygroundConversationOptions,
    Field(discriminator="type"),
]


async def create_conversation(
    user_id: ObjectId,
    user_persona: Persona,
    options: CreateConversationOptions,
) -> LevelConversation:
    subject_name = random.choice(PersonProvider.first_names)

    match options:
        case CreateLevelConversationOptions(level=level):
            scenario = await generate_conversation_scenario(
                user_id, user_persona, subject_name
            )

            data = BaseLevelConversationUninitData(
                user_id=user_id,
                level=level,
                subject_name=subject_name,
                info=LevelConversationInfoUninit(scenario=scenario),
                user_persona=user_persona,
            )

        case CreatePlaygroundConversationOptions():
            topic = random.choice(user_persona.interests)
            data = BasePlaygroundConversationUninitData(
                user_id=user_id,
                subject_name=subject_name,
                user_persona=user_persona,
                info=PlaygroundConversationInfo(
                    topic=topic,
                    user=user_persona,
                    subject=Persona(
                        name=subject_name,
                        age=str(random.randint(18, 65)),
                        occupation=random.choice(JobProvider.jobs),
                        interests=[topic],
                        description=(
                            f"You are {subject_name}, an autistic individual who is "
                            f"extremely passionate about {topic}. You are very "
                            "knowledgeable about the subject and enjoy discussing it "
                            "with others."
                        ),
                    ),
                ),
            )

    conversation = await conversations.insert(data)

    return conversation_from_data(conversation)


async def list_conversations(
    user_id: ObjectId, level: int | None = None
) -> list[LevelConversationDescriptor]:
    convs = await conversations.list(user_id, level)
    return [LevelConversationDescriptor.from_data(c) for c in convs]


async def get_conversation(
    conversation_id: ObjectId, user_id: ObjectId
) -> Conversation:
    conversation = await conversations.get(conversation_id, user_id)
    return conversation_from_data(conversation)


async def progress_conversation(
    conversation_id: ObjectId, user_id: ObjectId, option: int | None
) -> ConversationEvent:
    conversation = await conversations.get(conversation_id, user_id)

    if isinstance(conversation, LevelConversationUninitData):
        subject_persona = await generate_subject_persona(
            conversation.info.scenario.subject_perspective,
            conversation.subject_name,
        )
        info = LevelConversationInfo(
            scenario=conversation.info.scenario,
            user=conversation.user_persona,
            subject=subject_persona,
        )

        level = conversation.level

        conversation = LevelConversationInitData(
            id=conversation.id,
            user_id=conversation.user_id,
            level=level,
            info=info,
            state=ConversationNormalInternal(
                state=(
                    NormalNpFlowStateRef
                    if info.scenario.is_user_initiated
                    else NormalApFlowStateRef
                )
            ),
            events=[],
            messages=[],
            last_feedback_received=0,
        )

    if isinstance(conversation, PlaygroundConversationUninitData):
        level = 0

        conversation = PlaygroundConversationInitData(
            id=conversation.id,
            user_id=conversation.user_id,
            subject_name=conversation.subject_name,
            info=conversation.info,
            user_persona=conversation.user_persona,
            state=ConversationNormalInternal(state=NormalNpFlowStateRef),
            events=[],
            messages=[],
            last_feedback_received=0,
        )

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

        conversation.messages.append(
            Message(sender=conversation.info.user.name, message=response.response)
        )

        conversation.state = ConversationNormalInternal(state=response.next)

    assert isinstance(conversation.state, ConversationNormalInternal)

    state_data = (
        LEVELS[conversation.level].get_flow_state(conversation.state.state)
        if conversation.type == "level"
        else PLAYGROUND_MAPPINGS[conversation.state.state]
    )

    if isinstance(state_data, NpFlowState):
        print(state_data.options)
        state_options = (
            random.sample(state_data.options, 3)
            if len(state_data.options) > 3
            else state_data.options
        )

        responses = await asyncio.gather(
            *[
                generate_message(
                    conversation.info.user,
                    conversation.info.subject,
                    (
                        conversation.info.scenario.user_perspective
                        if conversation.type == "level"
                        else (
                            f"You are discussing {conversation.info.topic} with "
                            f"{conversation.info.subject.name}, who is an expert."
                        )
                    ),
                    conversation.messages,
                    opt.prompt,
                )
                for opt in state_options
            ]
        )

        options = [
            MessageOption(
                response=response,
                next=opt.next,
            )
            for response, opt in zip(responses, state_options)
        ]

        random.shuffle(options)

        conversation.events.append(
            ConversationLogEntry(
                root=NpMessageOptionsLogEntry(
                    state=conversation.state.state.id,
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
            conversation.info.user,
            (
                conversation.info.scenario.subject_perspective
                if conversation.type == "level"
                else (
                    f"You are discussing {conversation.info.topic} with "
                    f"{conversation.info.user.name}."
                )
            ),
            opt.prompt,
        )

        conversation.events.append(
            ConversationLogEntry(
                root=ApMessageLogEntry(
                    state=conversation.state.state.id,
                    message=response,
                )
            )
        )

        conversation.messages.append(
            Message(sender=conversation.info.subject.name, message=response)
        )

        conversation.state = ConversationNormalInternal(state=opt.next)

        result = ApMessageEvent(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(conversation, state_data)
        conversation.last_feedback_received = len(conversation.messages)

        conversation.events.append(
            ConversationLogEntry(
                root=FeedbackLogEntry(
                    state=conversation.state.state.id,
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

            conversation.state = ConversationWaitingInternal(options=options)
        else:
            conversation.state = ConversationNormalInternal(state=state_data.next_ok)

        result = FeedbackEvent(content=response)
    else:
        raise RuntimeError(f"Invalid state: {state_data}")

    await conversations.update(conversation)

    return ConversationEvent(root=result)
