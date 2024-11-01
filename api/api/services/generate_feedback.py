from api.schemas.chat import Feedback
from api.schemas.user import UserData

from . import llm


async def explain_suggestion(
    user: UserData, agent: str, objective: str, problem: str | None, message: str
) -> Feedback:
    objective_prompts = {
        ("yes-no-question", True): """
{user} asked a yes-or-no question that could be interpreted as either a yes or no
question or as a request for more information. {agent} could respond with a yes or no
answer, which is not what {user} is looking for. Instead, {user} should have asked a
direct question to get the information they wanted from {agent}. Explain the specific
phrasing of the question that could be misinterpreted as simply a yes or no question,
and explain that the correct interpretation is unclear.
""",
        ("yes-no-question", False): """
{user} asked a clear and direct question, avoiding the use of a yes-or-no question
that could be misinterpreted. This phrasing is more likely to elicit the information
that {user} is looking for as it is clear what information is being requested.
""",
        ("non-literal-emoji", True): """
{user} used an emoji in a non-literal way that could be misinterpreted by {agent}.
Explain specifically how emoji could be interpreted in literally,and how this could be
confusing and misinterpreted. Instead, {user} should use an emoji that clearly conveys
the intended meaning of the message.
""",
        ("non-literal-emoji", False): """
{user} used an emoji in a clear and direct way, adding a visual element to their
message that enhances the meaning in a way that does not cause confusion.
""",
        ("non-literal-figurative", True): """
{user} used figurative language that could be misinterpreted {agent}. Explain
specifically how the figurative language could be interpreted literally, and how this
could be confusing and misinterpreted. Instead, {user} should use clear and direct
language to convey their message.
""",
        ("non-literal-figurative", False): """
{user} used clear and direct language to convey their message, avoiding the use of
figurative language that could be misinterpreted. This direct language is more likely
to be understood as intended.
""",
        ("blunt-misinterpret", True): """
{user} was confrontational in response to {agent}'s blunt and direct language and
misinterpreted {agent}'s blunt language as rude. Explain how some individuals naturally
use blunt language and that {agent} did not intend to be rude. Instead, {user} should
consider that {agent} did not intend to be rude, and resond in a more neutral and
understanding way.
""",
        ("blunt-misinterpret", False): """
{user} responded appropriately to {agent}'s blunt language, considering that their blunt
language was not intended to be rude. {user}'s message is clear and direct, and it is
not confrontational to blunt language.
""",
    }
    objective_prompt = objective_prompts[(objective, problem is not None)].format(
        user=user.name, agent=agent
    )

    action = (
        (
            "Clearly explain how the user's message could be misinterpreted and point "
            "out specific elements of their message that need improvement."
        )
        if problem is not None
        else (
            "Praise the user for their clear and effective communication. Briefly "
            "explain why their message is effectives."
        )
    )

    system_prompt_template = """
As an expert in different communication styles, you are providing feedback on a possible
message in an ongoing conversation between {user} and {agent}.

{objective_prompt}

You are providing feedback directly to {user}, so address them using second person
pronouns (begin with "Your").
Provide a title with less than 50 characters that briefly summarizes the lesson of your
feedback and ending with an engaging emoji.
Then, provide comprehensive feedback and thoroughly explain the reasoning behind it.
Extract 1-2 key words or phrases from {user}'s message that are most relevant to your
feedback, while avoiding repeating more than necessary.
Be thorough in your explanation, but be concise and to the point.
Never provide alternative messages, only provide feedback on the current message.
Use simple, straightforward language that a high school student would understand.

Respond with a JSON object with keys "title" and "body" containing your feedback.

Here is the problem you need to address:
{problem}

{action}
"""

    system = system_prompt_template.format(
        objective_prompt=objective_prompt,
        action=action,
        user=user.name,
        agent=agent,
        problem=problem,
    )

    prompt_template = """
You are providing feedback on this message from {user} to {agent}:
<message>{message}</message>
"""

    prompt = prompt_template.format(user=user.name, agent=agent, message=message)

    return await llm.generate(
        schema=Feedback,
        model=llm.Model.GPT_4,
        system=system,
        prompt=prompt,
    )


async def explain_message(
    user: UserData,
    agent: str,
    objective: str,
    problem: str,
    message: str,
    reaction: str,
) -> Feedback:
    objective_prompts = {
        "yes-no-question": """
{user} asked a yes-or-no question that was interpreted as either a yes or no question or
as a request for more information. {agent} responded with a yes or no answer, which is
not what {user} is looking for. Instead, {user} should have asked a direct question to
get the information they wanted from {agent}. Explain how the specific phrasing of the
question caused their question to be misinterpreted as a simple yes or no question,
and explain that the correct interpretation is unclear.
""",
        "non-literal-emoji": """
{user} used an emoji in a non-literal way that was be misinterpreted. Explain
specifically how the emoji was interpreted literally by {agent}, and why this was
confusing. {user} should use an emoji that clearly conveys the intended meaning of their
message.
""",
        "non-literal-figurative": """
{user} used figurative language that was misinterpreted as literal. Explain specifically
how the figurative language was interpreted literally by {agent}, and how this could be
confusing. Instead, {user} should use clear and direct language to convey their message.
""",
        "blunt-misinterpret": """
{user} was confrontational in response to {agent}'s blunt and direct language, and
misinterpreted {agent}'s blunt language as rude. Explain how some individuals naturally
use blunt language and that {agent} did not intend to be rude. Instead, {user} should
consider that {agent} did not intend to be rude, and resond in a more understanding way.
""",
    }

    objective_prompt = objective_prompts[objective].format(user=user.name, agent=agent)

    system_prompt_template = """
As an expert in different communication styles, you are providing feedback on a possible
message in an ongoing conversation between {user} and {agent}.

{objective_prompt}

You are providing feedback directly to {user}, so address them using second person
pronouns (begin with "Your").
Provide a title with less than 50 characters that briefly summarizes the lesson of your
feedback and ending with an engaging emoji.
Then, provide comprehensive feedback and thoroughly explain the reasoning behind it.
Extract 1-2 key words or phrases from {user}'s message that are most relevant to your
feedback, while avoiding repeating more than necessary.
Never provide alternative messages, only provide feedback on the current message.
Use simple, straightforward language that a high school student would understand.

Here is the problem you need to address:
{problem}

Respond with a JSON object with keys "title" and "body" containing your feedback.
"""

    system = system_prompt_template.format(
        objective_prompt=objective_prompt,
        user=user.name,
        agent=agent,
        problem=problem,
    )

    prompt_template = """
You are providing feedback on this message from {user}:
<message>{message}</message>
<reaction>{reaction}</reaction>
"""

    prompt = prompt_template.format(
        user=user.name, agent=agent, message=message, reaction=reaction
    )

    return await llm.generate(
        schema=Feedback,
        model=llm.Model.GPT_4,
        system=system,
        prompt=prompt,
    )
