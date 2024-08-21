import asyncio
import random

import faker
from bson import ObjectId

from api.db import conversations, users
from api.levels.all import get_level_states
from api.levels.states import (
    AgentState,
    FeedbackState,
    UserState,
)
from api.schemas.conversation import (
    AgentMessage,
    ApMessageLogEntry,
    ApMessageStep,
    BaseConversation,
    CompletedStep,
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
    SelectOptionIndex,
    SelectOptionNone,
    StateActiveData,
    StateAwaitingUserChoiceData,
    StateCompletedData,
    UserMessage,
)
from api.schemas.user import UserData

from . import conversation_pregen
from .conversation_generation import (
    generate_agent_persona,
    generate_level_conversation_scenario,
)
from .feedback_generation import generate_feedback
from .message_generation import generate_message


def _next_stage(stage: ConversationStage) -> ConversationStage:
    match stage:
        case LevelConversationStage(level=level) if level < 2:
            return LevelConversationStage(level=level + 1)
        case _:
            return PlaygroundConversationStage()


def _is_unlocked_stage(
    stage: ConversationStage, max_unlocked_stage: ConversationStage
) -> bool:
    match (max_unlocked_stage, stage):
        case (PlaygroundConversationStage(), _):
            return True
        case (
            LevelConversationStage(level=max_level),
            LevelConversationStage(level=level),
        ):
            return level <= max_level
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

    # if isinstance(stage, LevelConversationStage):
    #     conversation = await conversations.query_one(user.id, stage)
    #     if conversation is not None:
    #         return Conversation.from_data(conversation)

    return await _create_conversation_internal(user, stage)


fake = faker.Faker()


async def _create_conversation_internal(
    user: UserData,
    stage: ConversationStage,
) -> Conversation:
    assert isinstance(stage, LevelConversationStage)
    agent_name = fake.first_name()
    states = get_level_states(stage)

    match stage:
        case LevelConversationStage(level=level):
            scenario = await generate_level_conversation_scenario(
                user.persona, agent_name, stage
            )

            info = LevelConversationInfo(level=level, scenario=scenario)

            agent = await generate_agent_persona(
                scenario.agent_perspective,
                agent_name,
                user.persona.culture,
            )
            state = StateActiveData(data=states.init())

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
                user.persona.culture,
            )
            state = StateActiveData(data=states.init())

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

    assert isinstance(conversation.info, LevelConversationInfo)
    states = get_level_states(conversation.info)

    unlocked_stage = user.max_unlocked_stage

    if isinstance(conversation.state, StateAwaitingUserChoiceData):
        match option:
            case SelectOptionIndex(index=index) if index < len(
                conversation.state.options
            ):
                response = conversation.state.options[index]
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

        conversation.state = StateActiveData(data=response.next)
    else:
        if not isinstance(option, SelectOptionNone):
            raise InvalidSelection()

    messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    if isinstance(conversation.state, StateActiveData):
        if conversation.state.data is None:
            conversation.state = StateCompletedData()

            unlocked_stage = user.max_unlocked_stage
            if str(conversation.info) == str(user.max_unlocked_stage):
                unlocked_stage = _next_stage(user.max_unlocked_stage)

                await unlock_stage(user, unlocked_stage)
                await _enqueue_pregenerate_conversations(user)

            result = CompletedStep(max_unlocked_stage=str(unlocked_stage))
        else:
            state_data = states.next(conversation.state.data)

            if isinstance(state_data, UserState):
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
                            instructions=opt.instructions,
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
                        options=options,
                    )
                )

                conversation.state = StateAwaitingUserChoiceData(
                    options=options, allow_custom=False
                )

                result = NpMessageStep(
                    options=[o.response for o in options],
                    allow_custom=False,
                    max_unlocked_stage=str(unlocked_stage),
                )
            elif isinstance(state_data, AgentState):
                response = await generate_message(
                    user_sent=False,
                    user=user.persona,
                    agent=conversation.agent,
                    messages=messages,
                    scenario=conversation.info.scenario,
                    instructions=state_data.instructions,
                )

                conversation.events.append(
                    ApMessageLogEntry(
                        message=response,
                    )
                )

                conversation.elements.append(
                    MessageElement(content=AgentMessage(message=response))
                )

                conversation.state = StateActiveData(data=state_data.next)

                result = ApMessageStep(
                    content=response, max_unlocked_stage=str(unlocked_stage)
                )
            elif isinstance(state_data, FeedbackState):
                response = await generate_feedback(
                    user.persona,
                    conversation,
                    state_data,
                )

                conversation.events.append(
                    FeedbackLogEntry(
                        content=response,
                    )
                )

                if response.follow_up is not None:
                    options = [
                        MessageOption(
                            response=response.follow_up,
                            next=state_data.next,
                        )
                    ]

                    conversation.state = StateAwaitingUserChoiceData(
                        options=options,
                        allow_custom=isinstance(
                            conversation.info, PlaygroundConversationInfo
                        ),
                    )
                else:
                    conversation.state = StateActiveData(data=state_data.next)

                conversation.elements.append(
                    FeedbackElement(
                        content=response,
                    )
                )

                result = FeedbackStep(
                    content=response, max_unlocked_stage=str(unlocked_stage)
                )
            else:
                raise RuntimeError(f"Invalid state: {state_data}")
    elif isinstance(conversation.state, StateCompletedData):
        result = CompletedStep(max_unlocked_stage=str(unlocked_stage))
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


PREGENERATION_COUNT = 3 if conversation_pregen.DEFER_PREGENERATION else 0


async def _enqueue_pregenerate_conversations(user: UserData):
    stage = user.max_unlocked_stage

    stages: list[ConversationStage] = [
        stage := _next_stage(stage) for _ in range(PREGENERATION_COUNT)
    ]

    await asyncio.gather(
        *[_enqueue_pregenerate_conversation_ifne(user, stage) for stage in stages]
    )


async def pregenerate_initial_conversations(user: UserData):
    await pregenerate_conversation(user.id, LevelConversationStage(level=1))
    await _enqueue_pregenerate_conversations(user)
