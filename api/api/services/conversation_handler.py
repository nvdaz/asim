import asyncio
import random

import faker
from bson import ObjectId

from api.db import conversations, users
from api.schemas.conversation import (
    AgentMessage,
    ApMessageLogEntry,
    ApMessageStep,
    BaseConversation,
    Conversation,
    ConversationDescriptor,
    ConversationStage,
    ConversationStep,
    FeedbackElement,
    FeedbackLogEntry,
    FeedbackStep,
    LevelConversationInfo,
    LevelConversationStage,
    MessageElement,
    MessageOption,
    NpMessageOptionsLogEntry,
    NpMessageSelectedLogEntry,
    NpMessageStep,
    PlaygroundConversationInfo,
    PlaygroundConversationScenario,
    PlaygroundConversationStage,
    SelectOption,
    SelectOptionCustom,
    SelectOptionIndex,
    SelectOptionNone,
    StateActiveData,
    StateAwaitingUserChoiceData,
    StateFeedbackData,
    UserMessage,
)
from api.schemas.user import UserData

from . import conversation_pregen
from .conversation_generation import (
    determine_conversation_topic,
    generate_agent_persona,
    generate_agent_persona_from_topic,
    generate_level_conversation_scenario,
)
from .feedback_generation import check_messages, generate_feedback
from .flow_state.base import (
    ApFlowState,
    ConversationContext,
    NormalApFlowStateRef,
    NormalNpFlowStateRef,
    NpFlowState,
    UserFlowOption,
)
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL_CONTEXT
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL_CONTEXT
from .flow_state.playground import PLAYGROUND_CONTEXT
from .message_generation import generate_message

LEVEL_CONTEXTS = [FIGURATIVE_LANGUAGE_LEVEL_CONTEXT, BLUNT_LANGUAGE_LEVEL_CONTEXT]


def _get_stage_context(stage: ConversationStage) -> ConversationContext:
    match stage:
        case LevelConversationStage(level=level):
            return LEVEL_CONTEXTS[level - 1]
        case PlaygroundConversationStage():
            return PLAYGROUND_CONTEXT
        case _:
            raise ValueError("Invalid stage")


def _next_stage(stage: ConversationStage) -> ConversationStage:
    match stage:
        case LevelConversationStage(level=level, part=part) if part < 5:
            return LevelConversationStage(level=level, part=part + 1)
        case LevelConversationStage(level=level, part=part) if level < 2 and part == 5:
            return LevelConversationStage(level=level + 1, part=1)
        case _:
            return PlaygroundConversationStage()


def _should_unlock_next_stage(
    current_stage: ConversationStage,
    sent_message_counts: dict[str, int],
) -> ConversationStage:
    if not sent_message_counts.get(str(current_stage), 0) >= 8:
        return current_stage

    return _next_stage(current_stage)


def _is_unlocked_stage(
    stage: ConversationStage, max_unlocked_stage: ConversationStage
) -> bool:
    match (max_unlocked_stage, stage):
        case (PlaygroundConversationStage(), _):
            return True
        case (
            LevelConversationStage(level=max_level, part=max_part),
            LevelConversationStage(level=level, part=part),
        ):
            return level < max_level or (level == max_level and part <= max_part)
        case _:
            return False


class StageNotUnlocked(Exception):
    pass


async def create_conversation(
    user: UserData,
    stage: ConversationStage,
) -> Conversation:
    if not _is_unlocked_stage(stage, user.max_unlocked_stage):
        raise StageNotUnlocked()

    if isinstance(stage, LevelConversationStage):
        conversation = await conversations.query_one(user.id, stage)
        if conversation is not None:
            return Conversation.from_data(conversation)

    return await _create_conversation_internal(user, stage)


fake = faker.Faker()


async def _create_conversation_internal(
    user: UserData,
    stage: ConversationStage,
) -> Conversation:
    agent_name = fake.first_name()

    match stage:
        case LevelConversationStage(level=level, part=part):
            scenario = await generate_level_conversation_scenario(
                user.persona, agent_name, stage
            )

            info = LevelConversationInfo(level=level, part=part, scenario=scenario)

            agent = await generate_agent_persona(
                scenario.agent_perspective,
                agent_name,
            )
            state = StateActiveData(
                id=(
                    NormalNpFlowStateRef
                    if scenario.is_user_initiated
                    else NormalApFlowStateRef
                )
            )

        case PlaygroundConversationStage():
            scenario = PlaygroundConversationScenario(
                user_perspective=(
                    "You have the opportunity to learn more about a topic that you "
                    "are interested in. You are chatting with an expert who will help "
                    "you understand the topic of your choice better. You are just "
                    "meeting the expert for the first time. Ask questions about the "
                    "topic and engage in a conversation with the expert."
                ),
                agent_perspective=(
                    "You are an expert and are highly knowledgeable in various fields. "
                    "Your goal is to help the user select a topic of interest "
                    "to chat about. You will help the user understand their "
                    "chosen topic better by engaging in a conversation with them, "
                    "detailing the key points, and answering any questions they have."
                ),
                topic=None,
            )

            info = PlaygroundConversationInfo(
                scenario=scenario,
            )

            agent = await generate_agent_persona(
                scenario.agent_perspective,
                agent_name,
            )
            state = StateActiveData(id=NormalNpFlowStateRef)

    data = BaseConversation(
        user_id=user.id,
        info=info,
        agent=agent,
        state=state,
        elements=[],
        events=[],
    )

    conversation = await conversations.insert(data)

    return Conversation.from_data(conversation)


async def list_conversations(user_id: ObjectId, options: ConversationStage):
    convs = await conversations.query(user_id, options)
    return [ConversationDescriptor.from_data(c) for c in convs]


async def get_conversation(
    conversation_id: ObjectId, user_id: ObjectId
) -> Conversation | None:
    conversation = await conversations.get(conversation_id, user_id)
    return Conversation.from_data(conversation) if conversation else None


class InvalidSelection(Exception):
    pass


async def unlock_stage(user: UserData, stage: ConversationStage):
    await users.unlock_stage(user.id, stage)


async def progress_conversation(
    conversation_id: ObjectId,
    user: UserData,
    option: SelectOption,
) -> ConversationStep:
    conversation = await conversations.get(conversation_id, user.id)

    if not conversation:
        raise RuntimeError("Conversation not found")

    context = _get_stage_context(conversation.info)
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
            MessageElement(content=UserMessage(message=response.response))
        )

        if (
            isinstance(conversation.info, PlaygroundConversationInfo)
            and conversation.info.scenario.topic is None
        ):
            topic = await determine_conversation_topic(conversation.elements)
            conversation.info.scenario.topic = topic

            if topic is not None:
                conversation.agent = await generate_agent_persona_from_topic(
                    conversation.agent.name, topic
                )

                conversation.info.scenario = PlaygroundConversationScenario(
                    user_perspective=(
                        f"You have the opportunity to explore {topic} by engaging in "
                        "a conversation with an expert who you are meeting for the "
                        "first time and are eager to share your thoughts and feelings. "
                        "Ask questions about the topic, share your own experiences, "
                        "and ask about the expert's background. Open up about your "
                        "interests and engage in a meaningful conversation that "
                        "connects with the expert on a personal level."
                    ),
                    agent_perspective=(
                        "Connect with the user on a personal level by considering "
                        "their perspective. Ask open-ended questions to learn more "
                        "about them and actively listen to their responses. Share "
                        "relevant personal experiences and insights as an expert in "
                        f"{topic} to foster a meaningful and engaging conversation. "
                        "Your goal is to create an emotionally captivating dialogue "
                        "that resonates with the user."
                    ),
                )

        sent_message_counts = await users.increment_message_count(
            user.id, conversation.info
        )

        unlocked_stage = _should_unlock_next_stage(
            conversation.info, sent_message_counts
        )

        if unlocked_stage != user.max_unlocked_stage:
            await unlock_stage(user, unlocked_stage)
            await _enqueue_pregenerate_conversations(user)

        checks = [(check, context.get_state(check)) for check in response.checks]

        failed_checks = await check_messages(
            user.persona, conversation.agent, conversation, checks
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

            def generate_message_for_option(opt: UserFlowOption):
                instructions = opt.prompt
                if (
                    isinstance(conversation.info, PlaygroundConversationInfo)
                    and conversation.info.scenario.topic is None
                ):
                    selected_topic = random.choice(user.persona.interests)
                    instructions = (
                        f"Your chosen topic is {selected_topic}. {instructions}"
                    )

                return generate_message(
                    user_sent=True,
                    user=user.persona,
                    agent=conversation.agent,
                    messages=messages,
                    scenario=conversation.info.scenario,
                    instructions=instructions,
                )

            responses = await asyncio.gather(
                *[generate_message_for_option(opt) for opt in state_options]
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
                MessageElement(content=AgentMessage(message=response))
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
        raise RuntimeError(f"Invalid state: {conversation.state}")

    await conversations.update(conversation)

    return result


async def pregenerate_conversation(user_id: ObjectId, stage: ConversationStage):
    user = await users.get(user_id)
    if not user:
        raise RuntimeError("User not found")

    conversation = await conversations.query_one(user.id, stage)
    if conversation is not None:
        return

    conversation = await _create_conversation_internal(user, stage)

    step = None
    while isinstance(step, ApMessageStep):
        step = await progress_conversation(
            conversation.id,
            user,
            SelectOptionNone(),
        )


async def _enqueue_pregenerate_conversation_ifne(
    user: UserData, stage: ConversationStage
):
    conversation = await conversations.query_one(user.id, stage)
    if not conversation:
        if conversation_pregen.DEFER_PREGENERATION:
            await conversation_pregen.create_pregenerate_task(user.id, stage)
        else:
            await pregenerate_conversation(user.id, stage)


PREGENERATION_COUNT = 3 if conversation_pregen.DEFER_PREGENERATION else 1


async def _enqueue_pregenerate_conversations(user: UserData):
    stage = user.max_unlocked_stage

    stages: list[ConversationStage] = [
        stage := _next_stage(stage) for _ in range(PREGENERATION_COUNT)
    ]

    await asyncio.gather(
        *[_enqueue_pregenerate_conversation_ifne(user, stage) for stage in stages]
    )


async def pregenerate_initial_conversations(user: UserData):
    await pregenerate_conversation(user.id, LevelConversationStage(level=1, part=1))
    await _enqueue_pregenerate_conversations(user)
    await _enqueue_pregenerate_conversations(user)
