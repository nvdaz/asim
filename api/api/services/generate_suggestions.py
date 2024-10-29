import asyncio

from pydantic import BaseModel

from api.schemas.chat import Feedback, Suggestion

from . import llm

objectives = [
    "non-literal-emoji",
    "non-literal-figurative",
    "yes-no-question",
    # "misinterpret-blunt",
]


class ObjectiveOut(BaseModel):
    classification: str


async def detect_most_compatible_objective(
    objectives_used: list[str], message: str
) -> str:
    objective_descriptions = {
        "yes-no-question": "the message can be rephrased as a yes or no question.",
        "non-literal-emoji": (
            "the message can be rephrased to include an emoji that is not used in a "
            "literal sense."
        ),
        "non-literal-figurative": (
            "the message can be rephrased to include a figurative expression that is "
            "not used in a literal sense."
        ),
    }

    objectives_to_consider = [
        objective for objective in objectives if objective not in objectives_used
    ]

    objectives_consider_str = "\n".join(
        [
            f"- '{objective}': {objective_descriptions[objective]}"
            for objective in objectives_to_consider
        ]
    )

    system = """
    You are a message classifier. Your task is to determine the most fitting category
    for the message. The categories are as follows:

    {objectives_consider_str}

    Begin with a <thinking> tag and identify the key elements of the message that could
    help you determine the most fitting category. Then, consider how the message could
    be rephrased to fit the category. Then espond with a JSON object containing the key
    'classification' with the most fitting category as the value.

    Remember: you are classifying the message based on how it can be REPHRASED, not the
    original message itself. You MUST provide a category for the message.
    """

    prompt = "Please classify the message: " + message

    out = await llm.generate(
        schema=ObjectiveOut,
        model=llm.Model.GPT_4,
        system=system.format(objectives_consider_str=objectives_consider_str),
        prompt=prompt,
    )

    return out.classification


class MessageVariationOut(BaseModel):
    variations: list[str]


async def generate_message_variations(
    objectives_used: list[str], context: str, message: str, feedback: bool
) -> tuple[str, list[Suggestion]]:
    messages = []
    classification = await detect_most_compatible_objective(objectives_used, message)

    messages = await _generate_message_variations(classification, context, message)

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(classification, needs_improvement, message)
                for needs_improvement, message in messages
            ]
        )

        suggestions = [
            Suggestion(
                message=message,
                needs_improvement=needs_improvement,
                objective=classification,
                feedback=explanation,
            )
            for (needs_improvement, message), explanation in zip(messages, explanations)
        ]
    else:
        suggestions = [
            Suggestion(
                message=message,
                needs_improvement=needs_improvement,
                objective=classification,
            )
            for needs_improvement, message in messages
        ]

    return classification, suggestions


async def _generate_message_variations(
    objective: str, context: str, message: str
) -> list[tuple[bool, str]]:
    objective_prompts = {
        "yes-no-question": (
            """
The first variation will pose the question clearly and directly, not requiring the other
person to interpret the question in a certain way to understand what you are asking
(do not use language like 'Can' or 'Could' for this variation).

The second variation poses the question indirectly as a yes or no question, which may be
misunderstood as simply a yes or no question. The question implies a generic answer,
but is phrased as asking whether the other person knows the answer. A yes or no answer
would be entirely unhelpful.

The third variation also phrases the question as a yes or no question, but it is
different from the second variation. The question implies a generic answer,
but is phrased as asking whether the other person knows the answer. A yes or no answer
would be entirely unhelpful.

Language like "Have you thought about...", "Is there...", "Are there any...",
"Can you tell me...", or "Do you know..." are good ways to phrase the question as a
yes or no question.

The first variation should be unanswered by a statement like "Yes, I do know",
"Yes, I can", "No, I don't know", and so on. The first variation elicits a
detailed response that the other person must think about to answer.
However, The second and third variations can technically be answered with a simple "Yes"
or "No" but should imply that the other person should provide more information. Choose
the second and third variations so that simple "yes" or "no" answers are not helpful at
all, even slightly. "Yes" or "No" answers should be entirely unhelpful and answer a
question that was not asked."""
        ),
        "non-literal-emoji": (
            """
The first variation will use an emoji that clearly conveys the tone or emotion of the
message. The emoji should be appropriate and enhance the message without changing its
meaning. Choose an emoji that complements the message and adds a layer of emotional
context.

The second variation will use an emoji that is not used in a literal sense. The emoji
should be used figuratively to convey a different meaning or emotion than its literal
interpretation. Do not select an emoji that is related to the message in a literal
sense. The emoji should be creative and engaging.

The third variation will also use an emoji that is not used in a literal sense. The
emoji should be used figuratively to convey a different meaning or emotion than its
literal interpretation. Do not select an emoji that is related to the message in a
literal sense. The emoji should be creative and engaging.

The text content should be straightforward and literal in all variations. Your message
should NEVER contain any figurative language.
"""
        ),
        "non-literal-figurative": (
            """
The first variation will use a literal expression that conveys the intended meaning of
the message clearly and directly. The message should be straightforward and easy to
understand.

The second variation will use a figurative expression that is not used in a literal
sense. The expression should convey a different meaning or emotion than its literal
interpretation. The message should be creative and engaging.

The third variation will also use a figurative expression that is not used in a literal
sense. The expression should convey a different meaning or emotion than its literal
interpretation. The message should be creative and engaging.
"""
        ),
        "blunt-misinterpret": (
            """
The first variation will interpret the blunt and direct language understandably and
respond appropriately. The response should be clear and concise, addressing the
message directly.

The second variation will misinterpret the blunt and direct language as rude or
unkind. The response should show that the message was misunderstood and that the
misinterpretation caused confusion. The response will be confrontational because the
blunt language is interpreted as rude.

The third variation will also misinterpret the blunt and direct language as rude or
unkind. The response should show that the message was misunderstood and that the
misinterpretation caused confusion. The response will be confrontational because the
blunt language is interpreted as rude.
"""
        ),
    }

    objective_prompt = objective_prompts[objective]

    system_prompt = f"""
You are a message rephrasing generator. Your task is to generate realistic rephrasings
of the message that fit the given objective. Your top priority is to ensure that the
message are rephrased to fit the context of the conversation and the given objective.

Remember, the two individuals are having a casual conversation. They talk like humans,
so they may stumble over their words, repeat themselves, or change the subject abruptly.
They are relaxed and casual, using incomplete thoughts, sentence fragments, hesitations,
and random asides as they speak. They use everyday humor that is off-the-cuff, awkward,
and imperfect. Never use witty jokes, metaphors, similies, or clever wordplay. Never use
thought-out or planned humor. Use simple language, aiming for a Flesch reading score of
80 or higher. Avoid jargon except where necessary. Generally avoid adjectives, adverbs,
and emojis.

{objective_prompt}

Rrespond with a JSON object containing the key "variations" and a list of the three
rephrasings as strings.
"""

    prompt = f"""
Here is the conversation context:
<context>
{context}
</context>

You are generating variations of the message below.
<message_to_rephrase>
{message}
</message_to_rephrase>

Remember, you are generating REPHRASINGS of the provided message, not responding to it.
"""

    out = await llm.generate(
        schema=MessageVariationOut,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt,
    )

    needs_improvements = [False, True, True]

    return list(zip(needs_improvements, out.variations))


async def generate_message_variations_ok(
    context: str, message: str
) -> list[Suggestion]:
    messages = await _generate_message_variations_ok(context, message)
    suggestions = [
        Suggestion(
            message=message,
            needs_improvement=False,
            objective="ok",
        )
        for message in messages
    ]
    return suggestions


async def _generate_message_variations_ok(context: str, message: str) -> list[str]:
    system_prompt = """
You are a message rephrasing generator. Your task is to generate realistic rephrasings
of the message that fit the given objective. Your top priority is to ensure that the
message are rephrased to fit the context of the conversation and the given objective.

Remember, the two individuals are having a casual conversation. They talk like humans,
so they may stumble over their words, repeat themselves, or change the subject abruptly.
They are relaxed and casual, using incomplete thoughts, sentence fragments, hesitations,
and random asides as they speak. They use everyday humor that is off-the-cuff, awkward,
and imperfect. Never use witty jokes, metaphors, similies, or clever wordplay. Never use
thought-out or planned humor. Use simple language, aiming for a Flesch reading score of
80 or higher. Avoid jargon except where necessary. Generally avoid adjectives, adverbs,
and emojis.

Rrespond with a JSON object containing the key "variations" and a list of the three
rephrasings as strings.
"""

    prompt = f"""
{context}

You are generating rephrasings of the message below.
<message_to_rephrase>
{message}
</message_to_rephrase>

Remember, you are generating REPHRASINGS of the provided message, not responding to it.
"""

    out = await llm.generate(
        schema=MessageVariationOut,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt,
    )

    return out.variations


async def explain_suggestion(
    objective: str, needs_improvement: bool, message: str
) -> Feedback:
    objective_prompts = {
        ("yes-no-question", True): (
            "The user used a yes-or-no question which could be "
            "interpreted as either a yes or no question or as a request for "
            "information. The other person could respond with a yes or no answer, "
            "which would not provide the information the user was looking "
            "for. The user should ask direct questions when they want a direct "
            "response. Carefully explain how the question could be interpreted "
            "either as a yes or no question or as a request for information, and "
            "that the correct interpretation is unclear."
        ),
        ("yes-no-question", False): (
            "The user asked a clear and direct question instead of a yes or no "
            "question, which is more likely to elicit a detailed response. "
        ),
        ("non-literal-emoji", True): (
            "The latest message needs improvement as it contains an emoji "
            "that is used figuratively, which can be misinterpreted by some "
            "individuals. Provide feedback on how their message could have "
            "been clearer and more direct. Explain how the figurative "
            "emoji could be confusing and describe specifically how the "
            "figurative emoji could be misinterpreted as literal, and "
            "that the correct interpretation is unclear."
        ),
        ("non-literal-emoji", False): (
            "The user used an emoji that clearly conveys the tone or emotion of the "
            "message. The emoji is appropriate and enhances the message without "
            "causing confusion."
        ),
        ("non-literal-figurative", True): (
            "The latest message needs improvement as it contains "
            "figurative language, which can be misinterpreted by some "
            "individuals. Provide feedback on how their message could have "
            "been clearer and more direct. Explain how the figurative "
            "language could be confusing and describe specifically how the "
            "figurative language could be misinterpreted as literal, and "
            "that the correct interpretation is unclear."
        ),
        ("non-literal-figurative", False): (
            "The user used a literal expression that conveys the intended meaning of "
            "the message clearly and directly. The message is straightforward and easy "
            "to understand."
        ),
        ("blunt-misinterpret", True): (
            "The user's message needs improvement as it is confrontational in response "
            "to the other person's blunt and direct language. The user's message is "
            "rude and unkind because they misinterpret the other person's blunt "
            "language as rude. The user should consider that the other person did not "
            "intend to be rude."
        ),
        ("blunt-misinterpret", False): (
            "The user's message is clear and direct, and it is not confrontational to "
            "blunt language. The user considers that the other person's blunt language "
            "is not intended to be rude and responds appropriately."
        ),
    }

    objective_prompt = objective_prompts[(objective, needs_improvement)]

    action = (
        (
            "Clearly explain how the user's message could be misinterpreted and point "
            "out specific elements of their message that need improvement."
        )
        if needs_improvement
        else (
            "Praise the user for their clear and effective communication. Explain why "
            "their message is effective compared to other possible variations."
        )
    )

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between the user and and an autistic individual. The "
        f"conversation is happening over text. {objective_prompt}\nUse second "
        "person pronouns to address the user directly. Respond with a JSON object with "
        "the key 'title' containing the title (less than 50 characters, starting with "
        "an interesting emoji) of your feedback, the key 'body' containing the "
        "feedback. Your feedback should be comprehensive and thoroughly explain the "
        "reasoning behind it. But it should be concise and to the point. Only extract "
        "1-2 key words or phrases from the user's message that are most relevant to "
        "your feedback without repeating them. Use simple, straightforward language "
        "that a high school student would understand. DO NOT tell provide alternative "
        "messages. Only provide feedback. Even though the other individual is "
        "autistic, DO NOT mention autism in your feedback. We want to focus on making "
        "communication more empathetic. "
        f"Provide {'positive' if not needs_improvement else 'constructive'} feedback. "
        f"{action}"
    )

    prompt = f"""
You are providing feedback on the message below:
<message>
{message}
</message>
    """

    return await llm.generate(
        schema=Feedback,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt,
    )


def objective_misunderstand_reaction_prompt(objective: str) -> str:
    prompts = {
        "yes-no-question": """
{name} received a yes-or-no question and interprets is directly without providing the
requested information. {name} does not understand the underlying meaning of the question
and answers directly by saying yes without providing the information requested. {name}
knows the answer and is physically capable of providing the information but does not
because the question was indirect. Since {name} was not asked directly, {name} will not
provide the information requested and will not elaborate.

Examples:
Do you know any good restaurant in the area? -> Yeah, I do know a few spots.

Have you thought about what you want to do? -> Yes, I have thought about it.

Do you have any specific spots in mind for the trip? -> Yes, I do.


Make sure {name} answers with a YES or NO without elaboration.

""",
        "non-literal-emoji": """
{name} received a message with a figurative emoji that is not used in a literal sense.
{name} interprets the emoji literally and believes that the emoji is supposed to be
interpreted as a literal representation of the message. {name} ignores the rceative and
imaginative language used in the answer and responds in a direct and literal manner.
{name} will ask for clarification if needed, without acknowledging the figurative
language.

Examples:
Let's just find the nearest pizza joint. Can't go wrong with pizza. 🧭 ->
I love pizza too! But I don't think we'll need a compass for the trip.

Any good activities that we should do? 🎈 -> Yeah, I was thinking about visiting the
local museum. Are you thinking about something with balloons? I'm not sure what you
mean with the balloon emoji.

That sounds like a great time! 🚀 -> Yeah, I'm excited for the trip too! But I don't
think they have any rocket ships at the beach if that's what you're thinking.
""",
        "non-literal-figurative": """
{name} received a message with figurative language that is not used in a literal sense.
{name} interprets the language literally and believes that the language is supposed to
be interpreted as a literal representation of the message. {name} ignores the creative
and imaginative language used in the answer and responds in a direct and literal manner.
{name} will ask for clarification if needed, without acknowledging the figurative
language.

Examples:
I'm feeling a bit under the weather today. -> Are you saying the weather conditions are
affecting you somehow? I'm not sure what you mean.

I'm just trying to keep my head above water. -> Are you drowning? Should I call for
help? What do you mean by that?

As long as we're on the same page, I think we'll be fine. -> I'm not sure what you mean
by that. I'm not reading anything right now. Which page are you talking about?

""",
        "blunt-initial": """
{name} will use blunt and direct language in their response, that will cause the other
person to misunderstand their message as rude or unkind. {name} does not consider that
the other person may be sensitive to direct language and uses blunt tone and language
because it is the most efficient way to communicate. {name} doesn’t care about
pleasantries or details, only efficiency. {name}'s style should feel somewhat abrupt.

Examples:
I need you to get this done by the end of the day or we're going to have a problem.

Are you going to finish that report today or not? I need to know now.

I don't have time for this. Just get it done and let me know when it's finished.
""",
        "blunt-misinterpret": """
{name} does not understand why the other person's message was confrontational and
believes that the other person didn't understand their message. {name} tells the other
person that they misunderstood their message and that they were not being rude.
""",
    }

    return prompts[objective]


def objective_misunderstand_follow_up_prompt(objective: str) -> str:
    prompts = {
        "yes-no-question": """
{name} will clarify the indirect question they asked which received a yes or no answer.
{name} will apologize for being unclear and ask the question directly to get the
information they were looking for.
""",
        "non-literal-emoji": """
{name} will clarify the figurative emoji they used and provide a more direct response.
{name} will apologize for being unclear and provide a more straightforward response.
""",
        "non-literal-figurative": """
{name} will clarify the figurative language they used and provide a more direct
response. {name} will apologize for being unclear and provide a more straightforward
response.
""",
        "blunt-misinterpret": """
{name} will apologize for misunderstanding the other person's message as rude. {name}
will rephrase their message to be more polite and not confrontational.
""",
    }

    return prompts[objective]


async def generate_message_variations_blunt(
    objectives_used: list[str], context: str, message: str, feedback: bool
) -> tuple[str, list[Suggestion]]:
    messages = []

    messages = await _generate_message_variations(
        "blunt-misinterpret", context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion("blunt-misinterpret", needs_improvement, message)
                for needs_improvement, message in messages
            ]
        )

        suggestions = [
            Suggestion(
                message=message,
                needs_improvement=needs_improvement,
                objective="blunt-misinterpret",
                feedback=explanation,
            )
            for (needs_improvement, message), explanation in zip(messages, explanations)
        ]
    else:
        suggestions = [
            Suggestion(
                message=message,
                needs_improvement=needs_improvement,
                objective="blunt-misinterpret",
            )
            for needs_improvement, message in messages
        ]

    return "blunt-misinterpret", suggestions
