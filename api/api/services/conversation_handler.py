import asyncio
import random

from bson import ObjectId
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
    ConversationSetup,
    ConversationStep,
    FeedbackElement,
    FeedbackLogEntry,
    FeedbackStep,
    LevelConversationInfo,
    LevelConversationOptions,
    Message,
    MessageElement,
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
    StateFeedbackData,
)
from api.schemas.persona import Persona, PersonaName

from .conversation_generation import (
    generate_agent_persona,
    generate_conversation_scenario,
    generate_conversation_topic,
)
from .feedback_generation import check_messages, generate_feedback
from .flow_state.base import (
    ApFlowState,
    NormalApFlowStateRef,
    NormalNpFlowStateRef,
    NpFlowState,
)
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL_CONTEXT
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL_CONTEXT
from .flow_state.playground import PLAYGROUND_CONTEXT
from .message_generation import generate_message

random.seed(0)

LEVEL_CONTEXTS = [FIGURATIVE_LANGUAGE_LEVEL_CONTEXT, BLUNT_LANGUAGE_LEVEL_CONTEXT]


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
            topic = await generate_conversation_topic(user_id, user_persona.interests)

            setup = ConversationSetup(
                user_perspective=(
                    f"You are interested in {topic} and want to learn more about the "
                    f"topic. Your engage in a conversation with {agent_name}, who is "
                    "an expert in the field to further your understanding."
                ),
                agent_perspective=(
                    f"You are an expert in {topic} and are highly knowledgeable "
                    f"about the subject. Your goal is to help {user_persona.name} "
                    "understand the topic better."
                ),
            )

            info = PlaygroundConversationInfo(
                topic=topic,
                setup=setup,
            )

    data = BaseConversationUninit(
        user_id=user_id, info=info, agent=PersonaName(name=agent_name), elements=[]
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

            case PlaygroundConversationInfo():
                agent = await generate_agent_persona(
                    conversation.info.setup.agent_perspective,
                    conversation.agent.name,
                )
                state = StateActiveData(id=NormalNpFlowStateRef)

        conversation = ConversationDataInit(
            id=conversation.id,
            user_id=conversation.user_id,
            info=conversation.info,
            agent=agent,
            state=state,
            events=[],
            elements=[],
            last_feedback_received=0,
        )

    if isinstance(conversation.info, LevelConversationInfo):
        context = LEVEL_CONTEXTS[conversation.info.level]
    elif isinstance(conversation.info, PlaygroundConversationInfo):
        context = PLAYGROUND_CONTEXT
    else:
        raise RuntimeError(f"Invalid conversation info: {conversation.info}")

    if isinstance(conversation.state, StateAwaitingUserChoiceData):
        match option:
            case SelectOptionIndex(index=index) if index < len(
                conversation.state.options
            ):
                response = conversation.state.options[index]
            case SelectOptionCustom(message=message) if conversation.state.allow_custom:
                response = MessageOption(
                    response=message,
                    checks=context.get_feedback_refs(),
                    next=NormalApFlowStateRef,
                )
            case _:
                raise InvalidSelection()

        conversation.events.append(
            NpMessageSelectedLogEntry(
                message=response.response,
            )
        )

        conversation.elements.append(
            MessageElement(content=Message(sender=user.name, message=response.response))
        )

        messages = [
            elem.content
            for elem in conversation.elements[conversation.last_feedback_received :]
            if isinstance(elem, MessageElement)
        ]

        checks = [(check, context.get_state(check)) for check in response.checks]

        failed_checks = await check_messages(
            user.name, conversation.agent.name, messages, checks
        )

        if failed_checks:
            conversation.state = StateFeedbackData(
                failed_checks=failed_checks, next=response.next
            )
        else:
            conversation.state = StateActiveData(id=response.next)
    else:
        if not isinstance(option, SelectOptionNone):
            raise InvalidSelection()

    messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    if isinstance(conversation.info, LevelConversationInfo):
        setup = conversation.info.scenario
    elif isinstance(conversation.info, PlaygroundConversationInfo):
        setup = conversation.info.setup
    else:
        raise RuntimeError(f"Invalid conversation info: {conversation.info}")

    if isinstance(conversation.state, StateActiveData):
        state_data = context.get_state(conversation.state.id)

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
                        messages,
                        scenario=setup.user_perspective,
                        instructions=opt.prompt,
                    )
                    for opt in state_options
                ]
            )

            options = [
                MessageOption(
                    response=response,
                    checks=opt.checks,
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
                options=[o.response for o in options],
                allow_custom=state_data.allow_custom,
            )
        elif isinstance(state_data, ApFlowState):
            opt = random.choice(state_data.options)

            response = await generate_message(
                conversation.agent,
                user,
                messages,
                scenario=setup.agent_perspective,
                instructions=opt.prompt,
            )

            conversation.events.append(
                ApMessageLogEntry(
                    state=conversation.state.id.id,
                    message=response,
                )
            )

            conversation.elements.append(
                MessageElement(
                    content=Message(sender=conversation.agent.name, message=response)
                )
            )

            conversation.state = StateActiveData(id=opt.next)

            result = ApMessageStep(content=response)
        else:
            raise RuntimeError(f"Invalid state: {state_data}")
    elif isinstance(conversation.state, StateFeedbackData):
        state_data = [
            context.get_state(check.source)
            for check in conversation.state.failed_checks
        ]

        response = await generate_feedback(
            user, conversation, state_data, setup.user_perspective
        )
        conversation.last_feedback_received = len(conversation.elements)

        conversation.events.append(
            FeedbackLogEntry(
                failed_checks=conversation.state.failed_checks,
                content=response,
            )
        )

        if response.follow_up is not None:
            options = [
                MessageOption(
                    response=response.follow_up,
                    checks=[],
                    next=conversation.state.next,
                )
            ]

            conversation.state = StateAwaitingUserChoiceData(
                options=options, allow_custom=False
            )
        else:
            conversation.state = StateActiveData(id=conversation.state.next)

        conversation.elements.append(
            FeedbackElement(
                content=response,
            )
        )

        result = FeedbackStep(content=response)
    else:
        raise RuntimeError(f"Invalid state: {state}")

    await conversations.update(conversation)

    return result
