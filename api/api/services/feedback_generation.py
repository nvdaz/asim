from typing import Literal, Union

from pydantic import BaseModel, Field, RootModel, StringConstraints
from typing_extensions import Annotated

from api.schemas.conversation import ConversationData, Message, Messages

from . import llm_service as llm
from .conversation_generation import generate_message
from .flow_state.base import FeedbackFlowState


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

    response = await llm.generate_strict(
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

    return await llm.generate_strict(
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


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str | None = None


async def _generate_feedback_with_follow_up(
    conversation: ConversationData, feedback: FeedbackFlowState
):
    class FeedbackWithPromptResponse(BaseModel):
        title: Annotated[str, StringConstraints(max_length=50)]
        body: Annotated[str, StringConstraints(max_length=600)]
        instructions: str

    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. The latest message from {user.name} was unclear and "
        f"was misinterpreted by {subject.name}. The conversation is happening over "
        f"text.\n{feedback.prompt_misunderstanding}\n Respond with a JSON object with "
        "the key 'title' containing the title (less than 50 characters) of your "
        "feedback, the key 'body' containing the feedback (less than 100 words), and "
        f"the key 'instructions' explaining what {user.name} could do to clarify the "
        f"situation. The 'instructions' should not be a message, but a string that "
        f"outlines what {user.name} should do to clarify the misunderstanding."
        f"The instructions should tell {user.name} to apologize for their mistake and "
        "clarify their message."
        "Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I feel like a million bucks today!"),
                Message(
                    sender="Chris",
                    message="Did you just win the lottery? That's great!",
                ),
            ]
        ).model_dump_json()
        + "\n"
        + FeedbackWithPromptResponse(
            title="Avoid Figurative Language",
            body=(
                "Your message relied on figurative language, which can be "
                "misinterpreted by autistic individuals. Consider using more "
                "direct language to avoid confusion."
            ),
            instructions=(
                "Your next message should apologize for the misunderstanding "
                "and clarify that you're not actually a millionaire, but you're "
                "feeling really good today. Be direct and avoid figurative language."
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    feedback_base = await llm.generate_strict(
        schema=FeedbackWithPromptResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    follow_up = await generate_message(
        user,
        conversation.info.scenario.user_scenario,
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
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual.\n{feedback.prompt_needs_improvement}\n The conversation "
        f"is happening over text. Describe how {user.name} could have improved their "
        "message to avoid confusion and misunderstanding. Respond with a JSON object "
        "with the key 'title' containing the title (less than 50 characters) of your "
        "feedback and the key 'body' containing the feedback (less than 100 words). "
        "Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I feel like a million bucks today!"),
                Message(
                    sender="Chris",
                    message="You must have had a great day! That's awesome!",
                ),
            ]
        ).model_dump_json()
        + "\n"
        + Feedback(
            title="Avoid Figurative Language",
            body=(
                "Your message relied on figurative language, which can be "
                "misinterpreted by autistic individuals. In this case, your message "
                "could be misinterpreted as a literal statement. Consider using more "
                "direct language to avoid confusion."
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate_strict(
        schema=Feedback,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _generate_feedback_ok(
    conversation: ConversationData, feedback: FeedbackFlowState
):
    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. {user.name} has been considerate and clear in their "
        "communication. The conversation is happening over text. \n"
        f"{feedback.prompt_ok}\nProvide positive reinforcement and encouragement for "
        "clear communication. Respond with a JSON object with the key 'title' "
        "containing the title (less than 50 characters) of your feedback and the key "
        "'body' containing the feedback (less than 100 words). Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I'm feeling great today!"),
                Message(
                    sender="Chris", message="That's awesome! I'm glad to hear that!"
                ),
            ]
        ).model_dump_json()
        + "\n"
        + Feedback(
            title="Clear Communication",
            body=(
                "Your message was clear and considerate. You successfully "
                "communicated your feelings without relying on unclear language. "
                "Keep up the good work!"
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate_strict(
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
