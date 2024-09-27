from typing import Annotated

from pydantic import BaseModel, Field

from api.levels.states import MessageInstructions
from api.schemas.conversation import (
    BaseConversationScenario,
    Message,
    dump_message_list,
)
from api.schemas.persona import AgentPersona, UserPersona

from . import llm


def _format_example(
    example: tuple[str, ...] | str,
) -> str:
    if isinstance(example, tuple):
        return " -> ".join([f"'{msg}'" for msg in example])
    else:
        return f"'{example}'"


def _format_instructions(instructions: MessageInstructions | None) -> str:
    if not instructions:
        return ""

    examples_str = (
        (
            "IMPORTANT: I MUST MODEL MY RESPONSE AFTER THE EXAMPLES BELOW.\n"
            "<example_responses>\n"
            + "\n".join([_format_example(example) for example in instructions.examples])
            + "\n</example_responses>\n"
        )
        if instructions.examples
        else ""
    )

    return f"\n{instructions.description}\n{examples_str}\n"


prompt = """
Here is the memory in {name}'s head:
{memory}
Be casual and relaxed. Vary the sentence structure and inject personality into the
message to make it sound human. Mix thoughts, use incomplete sentences, and don't be
perfect. Use contractions and some casual phrases for a natural feel.
Avoid uncommon words and use simple words and phrases but use jargon when appropriate.
Reply in at most 5 short sentences.
Ask follow-up questions to show interest, but avoid changing the topic unnecessarily.
Focus on the conversation in the moment and do not schedule any external meetings.

Summary of relevant context from {name}'s memory:
{context}

{action}

Output format: Output a json of the following format:
{{
"{name}": "<{name}'s utterance>",
"Did the conversation end with {name}'s utterance?": "<json Boolean>"
}}
"""

init_conversation_prompt = "How would {name} initiate a conversation?"
continue_conversation_prompt = """{name} and {other_name} are having a conversation.
How would {name} respond to {other_name}'s message to continue the conversation?
Here is their conversation so far:
{conversation}
"""

john_memory = """
John is a student at Tufts University who studies computer science and works with large
language models.
"""

john_context = """
Bob is a friend of John's who is a student at MIT studying computer science. Bob is
interested in mathematics.
"""

bob_memory = """
Bob is a student at MIT studying mathematics. They are interested in field topology and
spend their free time rock climbing.
"""

bob_context = """
John is a friend of Bob's who is a student at Tufts University studying computer science
and working with large language models.
"""


class UserMessage(BaseModel):
    message: Annotated[str, Field(..., alias="John")]


class AgentMessage(BaseModel):
    message: Annotated[str, Field(..., alias="Bob")]


async def generate_message(
    user_sent: bool,
    user: UserPersona,
    agent: AgentPersona,
    messages: list[Message],
    scenario: BaseConversationScenario,
    instructions: MessageInstructions | None = None,
    feedback: str | None = None,
) -> str:
    sender_name = "John" if user_sent else "Bob"
    recipient_name = "Bob" if user_sent else "John"

    memory = john_memory if user_sent else bob_memory
    context = john_context if user_sent else bob_context

    system_prompt = prompt.format(
        action=(
            init_conversation_prompt.format(name=sender_name)
            if len(messages) == 0
            else continue_conversation_prompt.format(
                name=sender_name,
                other_name=recipient_name,
                conversation=dump_message_list(messages, "John", "Bob"),
            )
        ),
        name=sender_name,
        memory=memory,
        context=context,
    )
    prompt_data = "Respond with the message."

    response = await llm.generate(
        schema=UserMessage if user_sent else AgentMessage,
        model=instructions.model if instructions else llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
        temperature=0.8,
    )

    return response.message
