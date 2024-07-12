from typing import Literal, Union

from pydantic import BaseModel, Field, RootModel, StringConstraints
from typing_extensions import Annotated

from api.schemas.conversation import ConversationData, Feedback, Message, Messages

from . import llm
from .flow_state.base import FeedbackFlowState
from .message_generation import generate_message


class BaseFeedbackAnalysisNeedsImprovement(BaseModel):
    needs_improvement: Literal[True] = True


class FeedbackAnalysisNeedsImprovement(BaseModel):
    needs_improvement: Literal[True] = True
    misunderstanding: bool


class FeedbackAnalysisOk(BaseModel):
    needs_improvement: Literal[False] = False


class BaseFeedbackAnalysis(RootModel):
    root: Annotated[
        Union[
            BaseFeedbackAnalysisNeedsImprovement,
            FeedbackAnalysisOk,
        ],
        Field(discriminator="needs_improvement"),
    ]


class FeedbackAnalysis(RootModel):
    root: Annotated[
        Union[
            FeedbackAnalysisNeedsImprovement,
            FeedbackAnalysisOk,
        ],
        Field(discriminator="needs_improvement"),
    ]


async def _analyze_messages_base(
    conversation: ConversationData, state: FeedbackFlowState
) -> FeedbackAnalysis:
    user, subject = conversation.info.user, conversation.info.subject

    system_prompt = (
        "You are a social skills coach. Your task is to analyze the ongoing "
        f"conversation between the user, {user.name}, and {subject.name}, who is "
        "an autistic individual. Determine if communication is going well or if "
        f"there are areas that need improvement.\n{state.prompt_analysis}\nRespond "
        "with a JSON object containing the following keys: 'needs_improvement': a "
        f"boolean indicating whether the messages sent by {user.name} need "
        "improvement and 'analysis': a string containing your analysis of the "
        "conversation."
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    response = await llm.generate(
        schema=BaseFeedbackAnalysis,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    if response.root.needs_improvement:
        return FeedbackAnalysis(
            root=FeedbackAnalysisNeedsImprovement(
                needs_improvement=True, misunderstanding=True
            )
        )
    else:
        return FeedbackAnalysis(root=FeedbackAnalysisOk(needs_improvement=False))


async def _analyze_messages_with_understanding(
    conversation: ConversationData, state: FeedbackFlowState
):
    user, subject = conversation.info.user, conversation.info.subject

    system_prompt = (
        "You are a social skills coach. Your task is to analyze the ongoing "
        f"conversation between the user, {user.name}, and {subject.name}, who is "
        "an autistic individual. Determine if communication is going well or if "
        f"there are areas that need improvement and possible misunderstandings.\n"
        f"{state.prompt_analysis}\nRespond with a JSON object containing the following "
        f"keys: 'needs_improvement': a boolean indicating whether the messages sent by "
        f"{user.name} need improvement, 'misunderstanding': a boolean indicating "
        f"whether the offending messages led to a misunderstanding by {subject.name}, "
        "and 'analysis': a string containing your analysis of the conversation."
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate(
        schema=FeedbackAnalysis,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _analyze_messages(
    conversation: ConversationData, state: FeedbackFlowState
) -> FeedbackAnalysis:
    if conversation.messages[-1].sender == conversation.info.user.name:
        return await _analyze_messages_base(conversation, state)
    else:
        return await _analyze_messages_with_understanding(conversation, state)


async def _generate_feedback_with_follow_up(
    conversation: ConversationData, feedback: FeedbackFlowState
):
    class FeedbackWithPromptResponse(BaseModel):
        title: Annotated[str, StringConstraints(max_length=50)]
        body: Annotated[str, StringConstraints(max_length=600)]
        instructions: str

    examples = [
        (
            Messages(
                root=[
                    Message(
                        sender="Ben",
                        message="I feel like a million bucks today!",
                    ),
                    Message(
                        sender="Chris",
                        message=("Did you just win the lottery? That's great!"),
                    ),
                ]
            ),
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
            Messages(
                root=[
                    Message(
                        sender="Alex", message="Break a leg in your performance today!"
                    ),
                    Message(
                        sender="Taylor",
                        message="That's mean! Why would you want me to get hurt?",
                    ),
                ]
            ),
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
            Messages(
                root=[
                    Message(
                        sender="Morgan", message="I can't keep my head above water."
                    ),
                    Message(
                        sender="Jamie",
                        message="Are you drowning? Should I call someone?",
                    ),
                ]
            ),
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

    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. The conversation is happening over text."
        f"\n{feedback.prompt_misunderstanding}\nUse second person pronouns to "
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
                f"{messages.model_dump_json()}\n{fb.model_dump_json()}"
                for messages, fb in examples
            ]
        )
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    feedback_base = await llm.generate(
        schema=FeedbackWithPromptResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    follow_up = await generate_message(
        user,
        subject,
        conversation.info.scenario.user_perspective,
        conversation.messages,
        extra=feedback_base.instructions,
    )

    return Feedback(
        title=feedback_base.title,
        body=feedback_base.body,
        follow_up=follow_up,
    )


async def _generate_feedback_needs_improvement(
    conversation: ConversationData, feedback: FeedbackFlowState
):
    user, subject = conversation.info.user, conversation.info.subject

    examples = [
        (
            Messages(
                root=[
                    Message(
                        sender="Ben",
                        message="I feel like a million bucks today!",
                    ),
                    Message(
                        sender="Chris",
                        message=(
                            "You must have had a great day! That's awesome to hear!"
                        ),
                    ),
                ]
            ),
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
            Messages(
                root=[
                    Message(
                        sender="Alex", message="Break a leg in your performance today!"
                    ),
                    Message(
                        sender="Taylor",
                        message="Thank you! I'll do my best to impress the audience!",
                    ),
                ]
            ),
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
            Messages(
                root=[
                    Message(
                        sender="Morgan", message="I can't keep my head above water."
                    ),
                    Message(sender="Jamie", message="Sounds like you're really busy!"),
                ]
            ),
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
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        "autistic individual. The conversation is happening over text.\n"
        f"{feedback.prompt_needs_improvement}\n Use second person pronouns to address "
        f"{user.name} directly. Respond with a JSON object with the key 'title' "
        "containing the title (less than 50 characters) of your feedback and the key "
        "'body' containing the feedback (less than 100 words). Examples:\n"
        + "\n\n".join(
            [
                f"{messages.model_dump_json()}\n{fb.model_dump_json()}"
                for messages, fb in examples
            ]
        )
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate(
        schema=Feedback,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _generate_feedback_ok(
    conversation: ConversationData, feedback: FeedbackFlowState
):
    user, subject = conversation.info.user, conversation.info.subject

    examples = [
        (
            Messages(
                root=[
                    Message(sender="Ben", message="I'm feeling great today!"),
                    Message(
                        sender="Chris", message="That's awesome! I'm glad to hear that!"
                    ),
                ]
            ),
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
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. The conversation is happening over text.\n"
        f"{feedback.prompt_ok}\nProvide positive reinforcement and encouragement for "
        f"clear communication. Use second person pronouns to address {user.name} "
        "directly. Respond with a JSON object with the key 'title' containing the "
        "title (less than 50 characters) of your feedback and the key 'body' "
        "containing the feedback (less than 100 words). Examples:\n"
        + "\n\n".join(
            [f"{msg.model_dump_json()}\n{fb.model_dump_json()}" for msg, fb in examples]
        )
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate(
        schema=Feedback,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def generate_feedback(
    conversation: ConversationData, state: FeedbackFlowState
) -> Feedback:
    analysis = await _analyze_messages(conversation, state)

    if isinstance(analysis.root, FeedbackAnalysisNeedsImprovement):
        if analysis.root.misunderstanding:
            return await _generate_feedback_with_follow_up(conversation, state)
        else:
            return await _generate_feedback_needs_improvement(conversation, state)
    else:
        return await _generate_feedback_ok(conversation, state)
