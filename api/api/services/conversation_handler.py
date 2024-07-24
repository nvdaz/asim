import asyncio
import random

from bson import ObjectId
from faker.providers.person.en import Provider as PersonProvider

from api.db import conversations, users
from api.schemas.conversation import (
    ApMessageLogEntry,
    ApMessageStep,
    BaseConversationUninit,
    Conversation,
    ConversationDataInit,
    ConversationDataUninit,
    ConversationDescriptor,
    ConversationOptions,
    ConversationScenario,
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
from api.schemas.persona import PersonaName
from api.schemas.user import UserData

from .conversation_generation import (
    determine_conversation_topic,
    generate_agent_persona,
    generate_conversation_scenario,
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

LEVEL_CONTEXTS = [FIGURATIVE_LANGUAGE_LEVEL_CONTEXT, BLUNT_LANGUAGE_LEVEL_CONTEXT]


def _should_unlock_next_stage(
    current_stage: str, sent_message_counts: dict[str, int]
) -> str:
    if not sent_message_counts.get(current_stage, 0) >= 8:
        return current_stage

    match current_stage:
        case "level-0":
            return "level-1"
        case "level-1":
            return "playground"
        case _:
            return current_stage


def _is_unlocked_stage(stage: str, max_unlocked_stage: str) -> bool:
    print(stage, max_unlocked_stage)
    return {
        "playground": True,
        "level-1": stage in ["level-0", "level-1"],
        "level-0": stage == "level-0",
    }.get(max_unlocked_stage, False)


class StageNotUnlocked(Exception):
    pass


async def create_conversation(
    user: UserData,
    options: ConversationOptions,
) -> Conversation:
    if not _is_unlocked_stage(options.stage_name(), user.max_unlocked_stage):
        raise StageNotUnlocked()

    return await create_conversation_unchecked(user, options)


async def create_conversation_unchecked(
    user: UserData,
    options: ConversationOptions,
) -> Conversation:
    agent_name = random.choice(PersonProvider.first_names)

    match options:
        case LevelConversationOptions(level=level):
            scenario = await generate_conversation_scenario(
                user.id, user.persona, agent_name
            )

            info = LevelConversationInfo(scenario=scenario, level=level)

        case PlaygroundConversationOptions():
            scenario = ConversationScenario(
                user_perspective=(
                    "You are interested in learning more about a topic of your choice. "
                    "Engage in a conversation with an expert to further your "
                    "understanding. Ask questions and engage in a conversation to "
                    "learn more."
                ),
                agent_perspective=(
                    "You are an expert and are highly knowledgeable in various fields. "
                    "Your goal is to help the user understand their chosen topic "
                    "better by engaging in a conversation with them, detailing the key "
                    "points, and answering any questions they may have."
                ),
                user_goal=None,
                is_user_initiated=True,
            )

            info = PlaygroundConversationInfo(
                topic=None,
                scenario=scenario,
            )

    data = BaseConversationUninit(
        user_id=user.id, info=info, agent=PersonaName(name=agent_name), elements=[]
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
    user: UserData,
    option: SelectOption,
) -> ConversationStep:
    conversation = await conversations.get(conversation_id, user.id)

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
                    conversation.info.scenario.agent_perspective,
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

    unlocked_stage = user.max_unlocked_stage

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
            MessageElement(content=Message(user_sent=True, message=response.response))
        )

        if (
            isinstance(conversation.info, PlaygroundConversationInfo)
            and conversation.info.topic is None
        ):
            topic = await determine_conversation_topic(conversation.elements)
            conversation.info.topic = topic

        sent_message_counts = await users.increment_message_count(
            user.id, conversation.info.stage_name()
        )

        unlocked_stage = _should_unlock_next_stage(
            conversation.info.stage_name(), sent_message_counts
        )

        if unlocked_stage != user.max_unlocked_stage:
            await users.unlock_stage(user.id, unlocked_stage)

        checks = [(check, context.get_state(check)) for check in response.checks]

        failed_checks = await check_messages(
            user.persona.name, conversation.agent.name, conversation, checks
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
                        user_sent=True,
                        user=user.persona,
                        agent=conversation.agent,
                        messages=messages,
                        scenario=conversation.info.scenario,
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
                max_unlocked_stage=unlocked_stage,
            )
        elif isinstance(state_data, ApFlowState):
            opt = random.choice(state_data.options)

            response = await generate_message(
                user_sent=False,
                user=user.persona,
                agent=conversation.agent,
                messages=messages,
                scenario=conversation.info.scenario,
                instructions=opt.prompt,
            )

            conversation.events.append(
                ApMessageLogEntry(
                    state=conversation.state.id.id,
                    message=response,
                )
            )

            conversation.elements.append(
                MessageElement(content=Message(user_sent=False, message=response))
            )

            conversation.state = StateActiveData(id=opt.next)

            result = ApMessageStep(content=response, max_unlocked_stage=unlocked_stage)
        else:
            raise RuntimeError(f"Invalid state: {state_data}")
    elif isinstance(conversation.state, StateFeedbackData):
        state_data = [
            context.get_state(check.source)
            for check in conversation.state.failed_checks
        ]

        response = await generate_feedback(user.persona, conversation, state_data)
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
                options=options,
                allow_custom=isinstance(conversation.info, PlaygroundConversationInfo),
            )
        else:
            conversation.state = StateActiveData(id=conversation.state.next)

        conversation.elements.append(
            FeedbackElement(
                content=response,
            )
        )

        result = FeedbackStep(content=response, max_unlocked_stage=unlocked_stage)
    else:
        raise RuntimeError(f"Invalid state: {state}")

    await conversations.update(conversation)

    return result


async def setup_initial_level_state(user: UserData, options: ConversationOptions):
    conversation = await create_conversation_unchecked(user, options)

    step = None

    while not isinstance(step, NpMessageStep):
        step = await progress_conversation(
            conversation.id,
            user,
            SelectOptionNone(),
        )


async def setup_initial_state(user: UserData):
    options = [
        LevelConversationOptions(level=0),
        LevelConversationOptions(level=1),
        PlaygroundConversationOptions(),
    ]
    await asyncio.gather(
        *[setup_initial_level_state(user, option) for option in options]
    )
