import random
from dataclasses import dataclass
from typing import Literal, Union

from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.schemas.conversation import (
    ConversationData,
    ConversationNormal,
    ConversationScenario,
    ConversationWaiting,
    Message,
    MessageOption,
)
from api.schemas.persona import Persona

from .conversation_generation import generate_conversation_info
from .feedback_generation import Feedback, generate_feedback
from .flow_state.base import ApFlowState, FeedbackFlowState, NpFlowState
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL
from .message_handling import generate_message

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


_CONVERSATIONS: list[ConversationData] = []


@dataclass
class Conversation:
    id: str
    level: int
    scenario: ConversationScenario
    subject_name: str
    messages: list[Message]

    @staticmethod
    def from_data(data: ConversationData):
        return Conversation(
            id=data.id,
            level=data.level,
            scenario=data.info.scenario,
            subject_name=data.info.subject.name,
            messages=data.messages,
        )


async def create_conversation(user: Persona, level: int) -> Conversation:
    conversation_info = await generate_conversation_info(user)

    id = len(_CONVERSATIONS)

    _CONVERSATIONS.append(
        ConversationData(
            id=str(id),
            level=level,
            info=conversation_info,
            state=ConversationNormal(
                state=(
                    LEVELS[level].initial_np_state
                    if conversation_info.scenario.is_user_initiated
                    else LEVELS[level].initial_ap_state
                )
            ),
            messages=[],
            last_feedback_received=0,
        )
    )

    return Conversation.from_data(_CONVERSATIONS[-1])


def get_conversation(conversation_id: str) -> Conversation:
    return Conversation.from_data(_CONVERSATIONS[int(conversation_id)])


async def progress_conversation(
    conversation_id: str, option: int | None
) -> ConversationEvent:
    conversation = _CONVERSATIONS[int(conversation_id)]

    if isinstance(conversation.state, ConversationWaiting):
        assert option is not None
        response = conversation.state.options[option]

        conversation.messages.root.append(
            Message(sender=conversation.info.user.name, message=response.response)
        )

        conversation.state = ConversationNormal(state=response.next)

    assert isinstance(conversation.state, ConversationNormal)

    state_data = (
        LEVELS[conversation.level].get_flow_state(conversation.state.state).root
    )

    if isinstance(state_data, NpFlowState):
        options: list[MessageOption] = []
        for opt in state_data.options:
            response = await generate_message(
                conversation.info.user,
                conversation.info.scenario.user_scenario,
                conversation.messages,
                opt.prompt,
            )

            options.append(MessageOption(response=response, next=opt.next))

        random.shuffle(options)
        conversation.state = ConversationWaiting(options=options)

        return NpMessageEvent(options=[o.response for o in options])
    elif isinstance(state_data, ApFlowState):
        opt = random.choice(state_data.options)

        response = await generate_message(
            conversation.info.subject,
            conversation.info.scenario.subject_scenario,
            conversation.messages,
            opt.prompt,
        )

        conversation.messages.root.append(
            Message(sender=conversation.info.subject.name, message=response)
        )
        conversation.state = ConversationNormal(state=opt.next)

        return ApMessageEvent(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(conversation, state_data)
        conversation.last_feedback_received = len(conversation.messages.root)

        if response.follow_up is not None:
            conversation.messages.root.append(
                Message(
                    sender=conversation.info.user.name,
                    message=response.follow_up,
                )
            )
            conversation.state = ConversationNormal(
                state=state_data.next_needs_improvement
            )
        else:
            conversation.state = ConversationNormal(state=state_data.next_ok)

        return FeedbackEvent(content=response)
