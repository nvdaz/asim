import asyncio
import random

from bson import ObjectId
from faker.providers.job import Provider as JobProvider
from faker.providers.person.en import Provider as PersonProvider

from api.db import conversations
from api.schemas.conversation import (
    ApMessageLogEntry,
    ApMessageStep,
    BaseConversationUninit,
    Conversation,
    ConversationDataInit,
    ConversationDataUninit,
    ConversationDescriptor,
    ConversationOptions,
    ConversationStep,
    FeedbackLogEntry,
    FeedbackStep,
    LevelConversationInfo,
    LevelConversationOptions,
    Message,
    MessageOption,
    NpMessageOptionsLogEntry,
    NpMessageSelectedLogEntry,
    NpMessageStep,
    PlaygroundConversationInfo,
    PlaygroundConversationOptions,
    SelectOption,
    SelectOptionCustom,
    SelectOptionIndex,
    SelectOptionNone,
    StateActiveData,
    StateAwaitingUserChoiceData,
)
from api.schemas.persona import Persona, PersonaName

from .conversation_generation import (
    generate_agent_persona,
    generate_conversation_scenario,
)
from .feedback_generation import generate_feedback
from .flow_state.base import (
    ApFlowState,
    FeedbackFlowState,
    NormalApFlowStateRef,
    NormalNpFlowStateRef,
    NpFlowState,
)
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL_MAPPINGS
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL_MAPPINGS
from .flow_state.playground import PLAYGROUND_MAPPINGS
from .message_generation import generate_message

random.seed(0)

LEVEL_MAPPINGS = [FIGURATIVE_LANGUAGE_LEVEL_MAPPINGS, BLUNT_LANGUAGE_LEVEL_MAPPINGS]


async def create_conversation(
    user_id: ObjectId,
    user_persona: Persona,
    options: ConversationOptions,
) -> Conversation:
    agent_name = random.choice(PersonProvider.first_names)

    match options:
        case LevelConversationOptions(level=level):
            scenario = await generate_conversation_scenario(
                user_id, user_persona, agent_name
            )

            info = LevelConversationInfo(scenario=scenario, level=level)

        case PlaygroundConversationOptions():
            topic = random.choice(user_persona.interests)

            info = PlaygroundConversationInfo(
                topic=topic,
            )

    data = BaseConversationUninit(
        user_id=user_id, info=info, agent=PersonaName(name=agent_name), messages=[]
    )

    conversation = await conversations.insert(data)

    return Conversation.from_data(conversation)


async def list_conversations(user_id: ObjectId, options: ConversationOptions):
    convs = await conversations.query(user_id, options)
    return [ConversationDescriptor.from_data(c) for c in convs]


async def get_conversation(
    conversation_id: ObjectId, user_id: ObjectId
) -> Conversation:
    conversation = await conversations.get(conversation_id, user_id)
    return Conversation.from_data(conversation)


class InvalidSelection(Exception):
    pass


async def progress_conversation(
    conversation_id: ObjectId,
    user_id: ObjectId,
    user: Persona,
    option: SelectOption,
) -> ConversationStep:
    conversation = await conversations.get(conversation_id, user_id)

    if not conversation:
        raise RuntimeError("Conversation not found")

    if isinstance(conversation, ConversationDataUninit):
        match conversation.info:
            case LevelConversationInfo(scenario=scenario):
                agent = await generate_agent_persona(
                    conversation.info.scenario.agent_perspective,
                    conversation.agent.name,
                )
                state = StateActiveData(
                    id=(
                        NormalNpFlowStateRef
                        if scenario.is_user_initiated
                        else NormalApFlowStateRef
                    )
                )

            case PlaygroundConversationInfo(topic=topic):
                agent = Persona(
                    name=conversation.agent.name,
                    age=str(random.randint(18, 65)),
                    occupation=random.choice(JobProvider.jobs),
                    interests=[topic],
                    description=(f"You are discussing {topic} with {user.name}."),
                )

                state = StateActiveData(id=NormalNpFlowStateRef)

        conversation = ConversationDataInit(
            id=conversation.id,
            user_id=conversation.user_id,
            info=conversation.info,
            agent=agent,
            state=state,
            events=[],
            messages=[],
            last_feedback_received=0,
        )

    if isinstance(conversation.state, StateAwaitingUserChoiceData):
        match option:
            case SelectOptionIndex(index=index) if index < len(
                conversation.state.options
            ):

                response = conversation.state.options[index]
            case SelectOptionCustom(message=message) if conversation.state.allow_custom:
                response = MessageOption(response=message, next=NormalApFlowStateRef)
            case _:
                raise InvalidSelection()

        conversation.events.append(
            NpMessageSelectedLogEntry(
                message=response.response,
            )
        )

        conversation.messages.append(
            Message(sender=user.name, message=response.response)
        )

        conversation.state = StateActiveData(id=response.next)
    else:
        if not isinstance(option, SelectOptionNone):
            raise InvalidSelection()

    assert isinstance(conversation.state, StateActiveData)

    if isinstance(conversation.info, LevelConversationInfo):
        mappings = LEVEL_MAPPINGS[conversation.info.level]
    elif isinstance(conversation.info, PlaygroundConversationInfo):
        mappings = PLAYGROUND_MAPPINGS
    else:
        raise RuntimeError(f"Invalid conversation info: {conversation.info}")

    state_data = mappings[conversation.state.id]

    if isinstance(state_data, NpFlowState):
        state_options = (
            random.sample(state_data.options, 3)
            if len(state_data.options) > 3
            else state_data.options
        )

        responses = await asyncio.gather(
            *[
                generate_message(
                    user,
                    conversation.agent,
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
            NpMessageOptionsLogEntry(
                state=conversation.state.id.id,
                options=options,
            )
        )

        conversation.state = StateAwaitingUserChoiceData(
            options=options, allow_custom=state_data.allow_custom
        )

        result = NpMessageStep(
            options=[o.response for o in options], allow_custom=state_data.allow_custom
        )
    elif isinstance(state_data, ApFlowState):
        opt = random.choice(state_data.options)

        response = await generate_message(
            conversation.agent,
            user,
            conversation.messages,
            opt.prompt,
        )

        conversation.events.append(
            ApMessageLogEntry(
                state=conversation.state.id.id,
                message=response,
            )
        )

        conversation.messages.append(
            Message(sender=conversation.agent.name, message=response)
        )

        conversation.state = StateActiveData(id=opt.next)

        result = ApMessageStep(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(user, conversation, state_data)
        conversation.last_feedback_received = len(conversation.messages)

        conversation.events.append(
            FeedbackLogEntry(
                state=conversation.state.id.id,
                content=response,
            )
        )

        if response.follow_up is not None:
            options = [
                MessageOption(
                    response=response.follow_up, next=state_data.next_needs_improvement
                )
            ]

            conversation.state = StateAwaitingUserChoiceData(
                options=options, allow_custom=False
            )
        else:
            conversation.state = StateActiveData(state=state_data.next_ok)

        result = FeedbackStep(content=response)
    else:
        raise RuntimeError(f"Invalid state: {state_data}")

    await conversations.update(conversation)

    return result
