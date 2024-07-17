from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from api.schemas.conversation import (
    ConversationDataInit,
    FailedCheck,
    Feedback,
    Message,
    MessageElement,
    message_list_adapter,
)
from api.schemas.persona import Persona

from . import llm
from .flow_state.base import FeedbackFlowState, FeedbackFlowStateRef
from .message_generation import generate_message


class FeedbackWithPromptResponse(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    instructions: str


async def generate_feedback(
    user: Persona, conversation: ConversationDataInit, state: list[FeedbackFlowState]
) -> Feedback:
    agent = conversation.agent
    elements = conversation.elements[conversation.last_feedback_received :]
    messages = [elem.content for elem in elements if isinstance(elem, MessageElement)]

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
        f"autistic individual. The conversation is happening over text. Address the "
        "following points in your feedback:\n"
        + "\n".join(f"{fb.prompt}" for fb in state)
        + f"\nUse second person pronouns to address {user.name} directly. Respond with "
        "a JSON object with the key 'title' containing the title (less than 50 "
        "characters) of your feedback, the key 'body' containing the feedback (less "
        f"than 100 words), and the key 'instructions' explaining what {user.name} "
        "could do to clarify the situation. The 'instructions' should not be a "
        f"message, but a string that outlines what {user.name} should do to clarify "
        f"the misunderstanding.The instructions should tell {user.name} to apologize "
        "for their mistake and clarify their message. Examples: \n"
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
        instructions=(
            "You are writing a follow-up to your previous message. "
            f"{feedback_base.instructions}"
        ),
    )

    return Feedback(
        title=feedback_base.title,
        body=feedback_base.body,
        follow_up=follow_up,
    )


async def check_messages(
    user: str,
    agent: str,
    messages: list[Message],
    checks: list[tuple[FeedbackFlowStateRef, FeedbackFlowState]],
) -> list[FailedCheck]:
    check_names: set[str] = set(check.id for check, _ in checks)

    def validate_failed_check_name(failed_check: str) -> str:
        if failed_check not in check_names:
            raise ValueError(f"Invalid check ID: {failed_check}")

        return failed_check

    class FailedCheckNamed(BaseModel):
        check: Annotated[str, AfterValidator(validate_failed_check_name)]
        reason: str

    class Analysis(BaseModel):
        failed_checks: list[FailedCheckNamed]

    system = (
        "You are a social skills coach. Your task is to analyze the following "
        f"conversation between the user, {user}, and {agent}, who is an autistic "
        f"individual, and determine whether the latest message sent by {user} passes "
        "the provided checks. Here is list of checks that you should perform:\n"
        + "\n".join(f"{id}: {check.check}" for id, check in checks)
        + "\nA check should fail if the user's message does not meets the criteria "
        "described in the check. Provide a JSON object with the key 'failed_checks' "
        "with a list of objects with the keys 'check' containing the ID of the check "
        "that failed and 'reason' explaining why the check failed. DO NOT perform any "
        "checks that are not listed above."
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    result = await llm.generate(
        schema=Analysis,
        model=llm.Model.GPT_4,
        system=system,
        prompt=prompt_data,
    )

    failed_checks = [
        FailedCheck(
            source=FeedbackFlowStateRef(id=check.check),
            reason=check.reason,
        )
        for check in result.failed_checks
    ]

    return failed_checks
