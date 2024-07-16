from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, TypeAdapter

from api.schemas.conversation import (
    ConversationDataInit,
    Feedback,
    Message,
    MessageElement,
    message_list_adapter,
)
from api.schemas.persona import Persona

from . import llm
from .flow_state.base import FeedbackFlowState, FeedbackFlowStateRef, FlowStateRef
from .message_generation import generate_message


class BaseFeedbackAnalysisNeedsImprovement(BaseModel):
    needs_improvement: Literal[True] = True


class FeedbackAnalysisNeedsImprovement(BaseModel):
    needs_improvement: Literal[True] = True
    misunderstanding: bool


class FeedbackAnalysisOk(BaseModel):
    needs_improvement: Literal[False] = False


BaseFeedbackAnalysis = Annotated[
    BaseFeedbackAnalysisNeedsImprovement | FeedbackAnalysisOk,
    Field(discriminator="needs_improvement"),
]


FeedbackAnalysis = Annotated[
    FeedbackAnalysisNeedsImprovement | FeedbackAnalysisOk,
    Field(discriminator="needs_improvement"),
]

feedback_analysis_adapter: TypeAdapter[FeedbackAnalysis] = TypeAdapter(FeedbackAnalysis)


async def _analyze_messages_base(
    user: Persona, agent: Persona, messages: list[Message], state: FeedbackFlowState
) -> FeedbackAnalysis:
    system_prompt = (
        "You are a social skills coach. Your task is to analyze the ongoing "
        f"conversation between the user, {user.name}, and {agent.name}, who is "
        "an autistic individual. Determine if communication is going well or if "
        f"there are areas that need improvement.\n{state.prompt_analysis}\nRespond "
        "with a JSON object containing the following keys: 'needs_improvement': a "
        f"boolean indicating whether the messages sent by {user.name} need "
        "improvement and 'analysis': a string containing your analysis of the "
        "conversation."
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    response = await llm.generate(
        schema=BaseFeedbackAnalysis,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    if response.root.needs_improvement:
        return FeedbackAnalysisNeedsImprovement(
            needs_improvement=True, misunderstanding=True
        )
    else:
        return FeedbackAnalysisOk(needs_improvement=False)


async def _analyze_messages_with_understanding(
    user: Persona, agent: Persona, messages: list[Message], state: FeedbackFlowState
):
    system_prompt = (
        "You are a social skills coach. Your task is to analyze the ongoing "
        f"conversation between the user, {user.name}, and {agent.name}, who is "
        "an autistic individual. Determine if communication is going well or if "
        f"there are areas that need improvement and possible misunderstandings.\n"
        f"{state.prompt_analysis}\nRespond with a JSON object containing the following "
        f"keys: 'needs_improvement': a boolean indicating whether the messages sent by "
        f"{user.name} need improvement, 'misunderstanding': a boolean indicating "
        f"whether the offending messages led to a misunderstanding by {agent.name}, "
        "and 'analysis': a string containing your analysis of the conversation."
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    return await llm.generate(
        schema=feedback_analysis_adapter,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _analyze_messages(
    user: Persona, agent: Persona, messages: list[Message], state: FeedbackFlowState
) -> FeedbackAnalysis:
    if messages[-1].sender == user.name:
        return await _analyze_messages_base(user, agent, messages, state)
    else:
        return await _analyze_messages_with_understanding(user, agent, messages, state)


async def _generate_feedback_with_follow_up(
    user: Persona,
    agent: Persona,
    messages: list[Message],
    feedback: FeedbackFlowState,
    conversation: ConversationDataInit,
):
    class FeedbackWithPromptResponse(BaseModel):
        title: Annotated[str, StringConstraints(max_length=50)]
        body: Annotated[str, StringConstraints(max_length=600)]
        instructions: str

    examples = [
        (
            [
                Message(
                    sender="Ben",
                    message="I feel like a million bucks today!",
                ),
                Message(
                    sender="Chris",
                    message=("Did you just win the lottery? That's great!"),
                ),
            ],
            FeedbackWithPromptResponse(
                title="Avoid Similies",
                body=(
                    "Your message relied on Chris understanding the simile 'I feel "
                    "like a million bucks today.' However, figurative language can "
                    "be confusing for autistic individuals, and Chris interpreted it "
                    "literally. To avoid misunderstandings, use more direct language."
                ),
                instructions=(
                    "Your next message should apologize for using figurative language "
                    "and clarify that you didn't actually win the lottery but are "
                    "feeling really good today. Be direct and avoid figurative "
                    "language."
                ),
            ),
        ),
        (
            [
                Message(
                    sender="Alex", message="Break a leg in your performance today!"
                ),
                Message(
                    sender="Taylor",
                    message="That's mean! Why would you want me to get hurt?",
                ),
            ],
            FeedbackWithPromptResponse(
                title="Avoid Idioms",
                body=(
                    "Using idioms like 'break a leg' can sometimes be confusing for "
                    "autistic individuals, as they may interpret the phrase literally. "
                    "Taylor interpreted your message literally and thought you wanted "
                    "them to get hurt instead of wishing them good luck. To avoid "
                    "misunderstandings, use clear, direct language."
                ),
                instructions=(
                    "Your next message should apologize for using an idiom and clarify "
                    "that you didn't actually want Taylor to get hurt but were wishing "
                    "them good luck. Be direct and avoid figurative language."
                ),
            ),
        ),
        (
            [
                Message(sender="Morgan", message="I can't keep my head above water."),
                Message(
                    sender="Jamie",
                    message="Are you drowning? Should I call someone?",
                ),
            ],
            FeedbackWithPromptResponse(
                title="Avoid Metaphors",
                body=(
                    "Phrases like 'I can't keep my head above water', which rely on "
                    "metaphors, can sometimes be confusing for autistic individuals. "
                    "Jamie interpreted your message literally and thought you were in "
                    "danger. To avoid misunderstandings, use clear, direct language."
                ),
                instructions=(
                    "Your next message should apologize for using a metaphor and "
                    "clarify that you're not actually drowning but are just really  "
                    "busy. Be direct and avoid figurative language."
                ),
            ),
        ),
    ]

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {agent.name}, who is an "
        f"autistic individual. The conversation is happening over text."
        f"\n{feedback.prompt}\nUse second person pronouns to "
        f"address {user.name} directly. Respond with a JSON object with the key "
        "'title' containing the title (less than 50 characters) of your feedback, the "
        "key 'body' containing the feedback (less than 100 words), and the key "
        f"'instructions' explaining what {user.name} could do to clarify the "
        f"situation. The 'instructions' should not be a message, but a string that "
        f"outlines what {user.name} should do to clarify the misunderstanding."
        f"The instructions should tell {user.name} to apologize for their mistake and "
        "clarify their message."
        "Examples: \n"
        + "\n\n".join(
            [
                f"{message_list_adapter.dump_json(messages).decode()}\n{fb.model_dump_json()}"
                for messages, fb in examples
            ]
        )
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    feedback_base = await llm.generate(
        schema=FeedbackWithPromptResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    all_messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    follow_up = await generate_message(
        user,
        agent,
        all_messages,
        instructions=feedback_base.instructions,
    )

    return Feedback(
        title=feedback_base.title,
        body=feedback_base.body,
        follow_up=follow_up,
    )


async def _generate_feedback_needs_improvement(
    user: Persona,
    agent: Persona,
    messages: list[Message],
    feedback: FeedbackFlowState,
):
    examples = [
        (
            [
                Message(
                    sender="Ben",
                    message="I feel like a million bucks today!",
                ),
                Message(
                    sender="Chris",
                    message=("You must have had a great day! That's awesome to hear!"),
                ),
            ],
            Feedback(
                title="Avoid Similies",
                body=(
                    "Your message relied on figurative language, which can sometimes "
                    "be misunderstood by autistic individuals. In this case, 'I feel "
                    "like a million bucks today' might be interpreted literally. To "
                    "avoid confusion, use more straightforward language like 'I'm "
                    "feeling really good today!' instead."
                ),
            ),
        ),
        (
            [
                Message(
                    sender="Alex", message="Break a leg in your performance today!"
                ),
                Message(
                    sender="Taylor",
                    message="Thank you! I'll do my best to impress the audience!",
                ),
            ],
            Feedback(
                title="Avoid Idioms",
                body=(
                    "Using idioms like 'break a leg' can sometimes be confusing for "
                    "autistic individuals, as they may interpret the phrase literally. "
                    "Use clear, direct language to avoid misunderstandings. You could "
                    "say 'Good luck in your performance today!' instead to be more "
                    "clear."
                ),
            ),
        ),
        (
            [
                Message(sender="Morgan", message="I can't keep my head above water."),
                Message(sender="Jamie", message="Sounds like you're really busy!"),
            ],
            Feedback(
                title="Avoid Metaphors",
                body=(
                    "Metaphors like 'I can't keep my head above water' can sometimes "
                    "be confusing for autistic individuals, as they may interpret the "
                    "phrase literally. Use clear, direct language to avoid "
                    "misunderstandings. You could say 'I'm really busy right now!' "
                    "instead to be more clear."
                ),
            ),
        ),
    ]

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {agent.name}, who is an "
        "autistic individual. The conversation is happening over text.\n"
        f"{feedback.prompt}\n Use second person pronouns to address "
        f"{user.name} directly. Respond with a JSON object with the key 'title' "
        "containing the title (less than 50 characters) of your feedback and the key "
        "'body' containing the feedback (less than 100 words). Examples:\n"
        + "\n\n".join(
            [
                f"{message_list_adapter.dump_json(messages)}\n{fb.model_dump_json()}"
                for messages, fb in examples
            ]
        )
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    return await llm.generate(
        schema=Feedback,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _generate_feedback_ok(
    user: Persona,
    agent: Persona,
    messages: list[Message],
    feedback: FeedbackFlowState,
):
    examples = [
        (
            [
                Message(sender="Ben", message="I'm feeling great today!"),
                Message(
                    sender="Chris", message="That's awesome! I'm glad to hear that!"
                ),
            ],
            Feedback(
                title="Clear Communication",
                body=(
                    "Your latest message was clear and considerate. You successfully "
                    "communicated your feelings without relying on unclear language. "
                    "'I'm feeling great today!' was straightforward and easy to "
                    "understand for Chris, which is great for clear communication. "
                    "Keep up the good work!"
                ),
            ),
        )
    ]

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {agent.name}, who is an "
        f"autistic individual. The conversation is happening over text.\n"
        f"{feedback.prompt_ok}\nProvide positive reinforcement and encouragement for "
        f"clear communication. Use second person pronouns to address {user.name} "
        "directly. Respond with a JSON object with the key 'title' containing the "
        "title (less than 50 characters) of your feedback and the key 'body' "
        "containing the feedback (less than 100 words). Examples:\n"
        + "\n\n".join(
            [
                f"{message_list_adapter.dump_json(msg)}\n{fb.model_dump_json()}"
                for msg, fb in examples
            ]
        )
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    return await llm.generate(
        schema=Feedback,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def generate_feedback(
    user: Persona, conversation: ConversationDataInit, state: FeedbackFlowState
) -> Feedback:
    agent = conversation.agent
    elements = conversation.elements[conversation.last_feedback_received :]
    messages = [elem.content for elem in elements if isinstance(elem, MessageElement)]

    # analysis = await _analyze_messages(user, agent, messages, state)

    # if isinstance(analysis, FeedbackAnalysisNeedsImprovement):
    #     if analysis.misunderstanding:
    #         return await _generate_feedback_with_follow_up(
    #             user, agent, messages, state, conversation
    #         )
    #     else:
    #         return await _generate_feedback_needs_improvement(
    #             user, agent, messages, state
    #         )
    # else:
    #     return await _generate_feedback_ok(user, agent, messages, state)

    return await _generate_feedback_with_follow_up(
        user, agent, messages, state, conversation
    )


class AnalysisPassed(BaseModel):
    passed: Literal[True] = True


class AnalysisFailed(BaseModel):
    passed: Literal[False] = False
    failed_checks: Annotated[list[str], Field(min_items=1)]


Analysis = Annotated[AnalysisPassed | AnalysisFailed, Field(discriminator="passed")]


async def _analyze_message(
    user: str,
    agent: str,
    messages: list[Message],
    checks: list[tuple[FeedbackFlowStateRef, FeedbackFlowState]],
) -> Analysis:
    check_names: set[str] = set(check.id for check, _ in checks)

    def validate_failed_checks(failed_checks: list[str]) -> list[str]:
        for check in failed_checks:
            if check not in check_names:
                raise ValueError(f"Invalid check ID: {check}")
        return failed_checks

    class AnalysisFailedChecked(AnalysisFailed):
        failed_checks: Annotated[
            list[str], Field(min_length=1), AfterValidator(validate_failed_checks)
        ]

    AnalysisChecked = Annotated[
        AnalysisPassed | AnalysisFailedChecked,
        Field(discriminator="passed"),
    ]

    analysis_adapter = TypeAdapter(AnalysisChecked)

    system = (
        "You are a social skills coach. Your task is to analyze the following "
        f"conversation between the user, {user}, and {agent}, who is an autistic "
        f"individual, and determine whether the latest message sent by {user} is clear "
        "and considerate. Here is list of checks that you should perform:\n"
        + "\n".join(f"{id}: {check.check}" for id, check in checks)
        + "\nFor each check, provide a boolean value indicating whether the check "
        "passes or fails. A check should fail if the user's message does not meets the "
        "criteria described in the check. Provide a JSON object with the key "
        "'passed' with a boolean value indicating whether the user's message passes "
        "every check (the user's message is clear and considerate) and the key "
        "'failed_checks' with a list of strings containing the IDs of the checks that "
        "the user's message failed."
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    return await llm.generate(
        schema=analysis_adapter,
        model=llm.Model.GPT_4,
        system=system,
        prompt=prompt_data,
    )


async def check_messages(
    user: str,
    agent: str,
    messages: list[Message],
    checks: list[tuple[FeedbackFlowStateRef, FeedbackFlowState]],
) -> FlowStateRef | None:
    analysis = await _analyze_message(user, agent, messages, checks)

    if isinstance(analysis, AnalysisFailed):
        return FeedbackFlowStateRef(id=analysis.failed_checks[0])

    return None
