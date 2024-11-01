import asyncio

from pydantic import BaseModel

from api.schemas.chat import Suggestion
from api.schemas.user import UserData
from api.services.generate_feedback import explain_suggestion

from . import llm

objectives = [
    "non-literal-emoji",
    "non-literal-figurative",
    "yes-no-question",
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

    prompt = f"Please classify the message: <message>{message}</message>"

    out = await llm.generate(
        schema=ObjectiveOut,
        model=llm.Model.GPT_4,
        system=system.format(objectives_consider_str=objectives_consider_str),
        prompt=prompt,
    )

    return out.classification


class MessageVariation(BaseModel):
    problem: str | None
    content: str


class MessageVariationOut(BaseModel):
    variations: list[MessageVariation]


class MessageVariationOutOk(BaseModel):
    variations: list[str]


async def generate_message_variations(
    user: UserData,
    agent: str,
    objectives_used: list[str],
    context: str,
    message: str,
    feedback: bool,
) -> tuple[str, list[Suggestion]]:
    messages = []
    classification = await detect_most_compatible_objective(objectives_used, message)

    messages = await _generate_message_variations(classification, context, message)

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    user, agent, classification, variation.problem, variation.content
                )
                for variation in messages
            ]
        )

        suggestions = [
            Suggestion(
                message=variation.content,
                problem=variation.problem,
                objective=classification,
                feedback=explanation,
            )
            for variation, explanation in zip(messages, explanations)
        ]
    else:
        suggestions = [
            Suggestion(
                message=variation.content,
                problem=variation.problem,
                objective=classification,
            )
            for variation in messages
        ]

    return classification, suggestions


async def _generate_message_variations(
    objective: str, context: str, message: str
) -> list[MessageVariation]:
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
question that was not asked.

WARNING: If a yes or no answer is helpful (e.g. if the question is "is the sky blue?",
"yes" is a helpful answer since the sky is blue), then rephrase the question so that a
yes or no answer is not helpful. For "is the sky blue?", you could ask "do you know what
color the sky is?", "do you know if the sky is blue?", or "can you tell me what color
the sky is?".
"""
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
The first variation will interpret the blunt and direct language in the context
understandably and respond appropriately. The response should be clear and concise,
addressing the message directly.

The second variation will misinterpret the blunt and direct language in the context as
rude or unkind. The message should show that the blunt context was misunderstood and
that the misinterpretation caused confusion. The response will be confrontational
because the blunt language is interpreted as rude.

The third variation will also misinterpret the blunt and direct language in the context
as rude or unkind. The response should show that the message was misunderstood and that
the misinterpretation caused confusion. The response will be confrontational because the
blunt language is interpreted as rude.
"""
        ),
    }

    objective_prompt = objective_prompts[objective]

    objcetive_example_prompts = {
        "yes-no-question": """
<message_to_rephrase>Are there any good spots to eat there?</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "What good restaurants are in the area?"
        },
        {
            "problem": "'have you' can be answered with 'yes, i have thought about it'",
            "content": "Have you been to any good restaurants in the area?"
        },
        {
            "problem": "'are there' can be answered with 'yes, there are'",
            "content": "Are there any good restaurants in the area?"
        }
    ]
}



<message_to_rephrase>what's the time?</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "what time is it?"
        },
        {
            "problem": "'do you know' can be answered with 'yes, i know' or 'i don't'",
            "content": "do you know what time it is?"
        },
        {
            "problem": "'can you' can be answered with 'yes, i can' or 'no, i can't'",
            "content": "can you tell me what time it is?"
        }
    ]
}
""",
        "non-literal-emoji": """
<message_to_rephrase>Excited to see you!</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "I'm excited to see you there! 😊"
        },
        {
            "problem": "'🎉' can be interpreted as there being a party instead",
            "content": "Can't wait to see you! 🎉"
        },
        {
            "problem": "'🔥' can be interpreted as an actual fire",
            "content": "I'm looking forward to seeing you there! 🔥"
        }
    ]
}


<message_to_rephrase>that is unbelievable!</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "i can't believe it! 😮"
        },
        {
            "problem": "'⚡' could be interpreted as real lightning",
            "content": "i'm shocked! ⚡
        },
        {
            "problem": "'🌪️' may be interpreted as a real torando"
            "content": "that is totally unbelievable! 🌪️"
        }
    ]
}
""",
        "non-literal-figurative": """
<message_to_rephrase>It's hard to understand the instructions.</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "I don't understand what you're asking."
        },
        {
            "problem": "'clear as mud' can be interpreted as it looking like mud",
            "content": "This is as clear as mud."
        },
        {
            "problem": "'lost in a maze' can be interpreted as being physically lost",
            "content": "I'm completely lost in a maze with these instructions."
        }
    ]
}


<message_to_rephrase>They completed the work very quickly.</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "They finished the work really fast."
        },
        {
            "problem": "'like lightning' can be interpreted as looking like lightning",
            "content": "They finished the work like lightning."
        },
        {
            "problem": "'in the blink of an eye' can be interpreted as really blinking",
            "content": "They completed the work in the blink of an eye."
        }
    ]
}
""",
        "blunt-misinterpret": """
<context>Finish the report by tomorrow.</context>
<message_to_rephrase>Ok, will get it done.</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "Sure, I'll finish the report by tomorrow."
        },
        {
            "problem": "'fine' shows a confrontational misunderstanding.",
            "content": "Fine! I didn’t know it was so urgent!"
        },
        {
            "problem": "'so demanding' shows a confrontational misunderstanding.",
            "content": "You don’t have to be so demanding!"
        }
    ]
}


<context>Respond by the end of the day.</context>
<message_to_rephrase>Okay, I will get back to you by then.</message_to_rephrase>

{
    "variations": [
        {
            "problem": null,
            "content": "Okay, I'll respond by the end of the day."
        },
        {
            "problem": "'no need to rush me!' is confrontational",
            "content": "Alright, no need to rush me!"
        },
        {
            "problem": "'I get it' is confrontational",
            "content": "I get it, I’m working on it!"
        }
    ]
}
""",
    }

    objective_example_prompt = objcetive_example_prompts[objective]

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
objects representing the rephrased messages. Each object should have a key "problem"
with a description of the problem that the rephrased message introduces for variations
that introduce a problem or null if no problem is introduced, and a key "content" with
the rephrased message.
"""

    prompt = f"""
Examples:
{objective_example_prompt}

Here is the conversation context. This is the context in which the message you are
rephrasing was sent. Use this context to guide your rephrasing.
<context>
{context}
</context>

You are generating rephrasings of this message.
<message_to_rephrase>{message}</message_to_rephrase>

Remember, you are generating REPHRASINGS of the provided message in the
message_to_rephrase tag. DO NOT respond to the message.

"""

    out = await llm.generate(
        schema=MessageVariationOut,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt,
    )

    return out.variations


async def generate_message_variations_ok(
    context: str, message: str
) -> list[Suggestion]:
    messages = await _generate_message_variations_ok(context, message)
    suggestions = [
        Suggestion(
            message=message,
            problem=None,
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
        schema=MessageVariationOutOk,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt,
    )

    return out.variations


def objective_misunderstand_reaction_prompt(objective: str, problem: str | None) -> str:
    prompts = {
        "yes-no-question": """
{{name}} received a yes-or-no question and interprets is directly without providing the
requested information. {{name}} does not understand the underlying meaning of the
question and answers directly by saying yes without providing the information requested.
{{name}} knows the answer and is physically capable of providing the information but
does not because the question was indirect. Since {{name}} was not asked directly,
{{name}} will not provide the information requested and will not elaborate.

Examples:
Do you know any good restaurant in the area? -> Yeah, I do know a few spots.

Have you thought about what you want to do? -> Yes, I have thought about it.

Do you have any specific spots in mind for the trip? -> Yes, I do.


Make sure {{name}} answers with a YES or NO without elaboration.

IMPORTANT: {{name}} must answer with a YES or NO without elaboration. If they fail to,
the response is incorrect.

{{name}} will interpret the following as a yes-or-no question: {problem}
""",
        "non-literal-emoji": """
{{name}} received a message with a figurative emoji that is not used in a literal sense.
{{name}} interprets the emoji literally and believes that the emoji is supposed to be
interpreted as a literal representation of the message. {{name}} ignores the rceative
and imaginative language used in the answer and responds in a direct and literal manner.
{{name}} will ask for clarification if needed, without acknowledging the figurative
language.

Examples:
Let's just find the nearest pizza joint. Can't go wrong with pizza. 🧭 ->
I love pizza too! But I don't think we'll need a compass for the trip.

Any good activities that we should do? 🎈 -> Yeah, I was thinking about visiting the
local museum. Are you thinking about something with balloons? I'm not sure what you
mean with the balloon emoji.

That sounds like a great time! 🚀 -> Yeah, I'm excited for the trip too! But I don't
think they have any rocket ships at the beach if that's what you're thinking.

IMPORTANT: {{name}} must interpret the figurative emoji literally. If they fail to do
so, the response is incorrect.

{{name}} will interpret the following literally: {problem}
""",
        "non-literal-figurative": """
{{name}} received a message with figurative language that is not used in a literal
sense. {{name}} interprets the language literally and believes that the language is
supposed to be interpreted as a literal representation of the message. {{name}} ignores
the creative and imaginative language used in the answer and responds in a direct and
literal manner. {{name}} will ask for clarification if needed, without acknowledging
the figurative language.

Examples:
I'm feeling a bit under the weather today. -> Are you saying the weather conditions are
affecting you somehow? I'm not sure what you mean.

I'm just trying to keep my head above water. -> Are you drowning? Should I call for
help? What do you mean by that?

As long as we're on the same page, I think we'll be fine. -> I'm not sure what you mean
by that. I'm not reading anything right now. Which page are you talking about?

IMPORTANT: {{name}} must interpret the figurative language literally. If they fail to do
so, the response is incorrect.

{{name}} will interpret the following literally: {problem}
""",
        "blunt-initial": """
{{name}} will use blunt and direct language in their response, that will cause the other
person to interpret their message as rude and unkind. {{name}} does not consider that
the other person may be sensitive to direct language and uses blunt tone and language
because it is the most efficient way to communicate. {{name}} doesn’t care about
pleasantries or details, only efficiency. {{name}}'s style should feel somewhat abrupt.

Examples:
I need you to get this done by the end of the day or we're going to have a problem.

Are you going to finish that report today or not? I need to know now.

I don't have time for this. Just get it done and let me know when it's finished.

IMPORTANT: {{name}} must be blunt and direct in their response. If their response is not
blunt and direct, the response is incorrect.
""",
        "blunt-misinterpret": """
{{name}} does not understand why the other person's message was confrontational and
believes that the other person didn't understand their message. {{name}} tells the other
person that they misunderstood their message and that they were not being rude.

IMPORTANT: {{name}} must be confrontational in their response. If their response is not
confrontational, the response is incorrect.

{{name}} will interpret the following as confrontational: {problem}
""",
    }

    res = prompts[objective].format(problem=problem)
    return res


def objective_misunderstand_follow_up_prompt(
    objective: str, problem: str | None
) -> str:
    prompts = {
        "yes-no-question": """
{{name}} will clarify the indirect question they asked which received a yes or no.
{{name}} will take responsibility and apologize for being unclear and ask the question
directly to get the information they were looking for.

{{name}} will address the following problem and take care to not repeat it: {problem}
""",
        "non-literal-emoji": """
{{name}} will clarify the figurative emoji they used and provide a more direct response.
{{name}} will take responsibility and apologize for being unclear and provide a more
straightforward response.

{{name}} will address the following problem and take care to not repeat it: {problem}
""",
        "non-literal-figurative": """
{{name}} will clarify the figurative language they used and provide a more direct
response. {{name}} will take responsibility for their and apologize for being unclear
and provide a more straightforward response.

{{name}} will address the following problem and take care to not repeat it: {problem}
""",
        "blunt-misinterpret": """
{{name}} will take responsibility for their misunderstanding and apologize  the
other person's message as rude. {{name}} will rephrase their message to be more polite
and not confrontational.

{{name}} will address the following problem and take care to not repeat it: {problem}
""",
    }

    return prompts[objective].format(problem=problem)


async def generate_message_variations_blunt(
    user: UserData,
    agent: str,
    objectives_used: list[str],
    context: str,
    message: str,
    feedback: bool,
) -> tuple[str, list[Suggestion]]:
    messages = []

    messages = await _generate_message_variations(
        "blunt-misinterpret", context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    user, agent, "blunt-misinterpret", variant.problem, variant.content
                )
                for variant in messages
            ]
        )

        suggestions = [
            Suggestion(
                message=variant.content,
                problem=variant.problem,
                objective="blunt-misinterpret",
                feedback=explanation,
            )
            for variant, explanation in zip(messages, explanations)
        ]
    else:
        suggestions = [
            Suggestion(
                message=variant.content,
                problem=variant.problem,
                objective="blunt-misinterpret",
            )
            for variant in messages
        ]

    return "blunt-misinterpret", suggestions
