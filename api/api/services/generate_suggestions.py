import asyncio

from pydantic import BaseModel

from api.schemas.chat import Suggestion
from api.schemas.user import UserData
from api.services.generate_feedback import explain_suggestion

from . import llm

objectives = [
    # "non-literal-emoji",
    # "non-literal-figurative",
    # "yes-no-question",
]


class ObjectiveOut(BaseModel):
    classification: str


async def detect_most_compatible_objective(
    user: UserData,
    agent: str,
    conversation_history: str,
    objectives_used: list[str],
    message: str,
) -> str:
    objective_descriptions = {
        "yes-no-question": "This objective fits when it is possible to rephrase the message as a yes or no question, such that the response to the rephrased message is not entirely helpful/as expected. For example, the message 'What time is it?' can be rephrased to 'Do you know what time is it?'. This new message may be answered with a 'Yes' or 'No'. However, the correct response should contain details about the time too if the person knows it.",
        "non-literal-emoji": (
            "This objective fits when the message can be rephrased to include an emoji in a non-literal way. For example, the message 'My day was terrible' can be rephrased to 'I had a great day :)'. The use of the ':)' emoji here is sarcastic."
        ),
        "non-literal-figurative": (
            "This objective fits when the message can be rephrased to include a figurative expression. For example, the message 'It is raining' can be reprhased to It was raining cats and dogs'. The idom is used figuratively here."
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
    Your task is to determine the most fitting category
    for a given message. The categories are as follows:

    {objectives_consider_str}

    Respond with a JSON object containing the key
    'classification' with the most fitting category as the value.

    Remember: you are classifying the message based on how it can be REPHRASED, not the
    original message itself. You MUST provide a category for the message.
    """

    prompt = f"""Here is the conversation history between {user.name} and {agent}: {conversation_history}

    The next message by {user.name} is: {message}.

    Classify this message into one of the following categories: {objectives_consider_str}.

    Respond with a JSON object containing the key 'classification' with the most fitting category as the value.

    Remember: you are classifying the message based on how it can be REPHRASED, not the original message itself. You MUST provide only ONE category for the message."""

    out = await llm.generate(
        schema=ObjectiveOut,
        model=llm.Model.GPT_4o,
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
    classification = await detect_most_compatible_objective(
        user, agent, context, objectives_used, message
    )

    messages = await _generate_message_variations(
        user, agent, classification, context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    user,
                    agent,
                    classification,
                    variation.problem,
                    context,
                    variation.content,
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
    user: UserData, agent, objective: str, context: str, message: str
) -> list[MessageVariation]:
    objective_prompts = {
        "yes-no-question": (
            """
The first variation will pose a question clearly and directly, not requiring the other
person to interpret the question in a certain way to understand what you are asking
(do not use language like 'Can' or 'Could' for this variation).

The second and third variation poses the question indirectly as a yes or no question,
which may be misunderstood as simply a yes or no question. The question implies a
generic answer, but is phrased as asking whether the other person knows the answer. A
yes or no answer would be entirely unhelpful.

Language like "Have you thought about...", "Is there...", "Are there any...",
"Can you tell me...", or "Do you know..." are good ways to phrase the question as a
yes or no question. Never use "Do you think..."

The first variation should be unanswered by a statement like "Yes, I do know",
"Yes, I can", "No, I don't know", and so on. The first variation elicits a
detailed response that the other person must think about to answer.
However, The second and third variations can technically be answered with a simple "Yes"
or "No" but should imply that the other person should provide more information. Choose
the second and third variations so that simple "yes" or "no" answers are not helpful at
all, even slightly. "Yes" or "No" answers should be entirely unhelpful and answer a
question that was not asked.

If the original message is not a question, add a relevant question after the message.

WARNING: If a yes or no answer is helpful (e.g. if the question is "is the sky blue?",
"yes" is a helpful answer since the sky is blue), then rephrase the question so that a
yes or no answer is not helpful. For "is the sky blue?", you could ask "do you know what
color the sky is?", "do you know if the sky is blue?", or "can you tell me what color
the sky is?".
"""
        ),
        "non-literal-emoji": (
            """
1. The first variation will use a simple emoji to enhance the message without changing its
meaning.

2. The second and third variations will have an emoji that is not used in a literal sense. The emoji
should be used figuratively to convey a different meaning or emotion than the original message.

Even though the focus is on the emoji, the text content MUST also be different between each variation.
"""
        ),
        "non-literal-figurative": (
            """
1. The first variation will use a literal expression that conveys the intended meaning of
the message clearly and directly. The message should be straightforward and easy to
understand.

2. The second and third variations will use a figurative language, an idiom or metaphor or a figurative expression, that is not used in a literal
sense. The expression should convey a different meaning or emotion than its literal
interpretation.
    """
        ),
        "blunt-misinterpret": (
            """
1. The first variation will interpret the blunt and direct message empathetically.
This messsage variation should be clear and concise, addressing the blunt message.

2. The second and third variations will interpret the blunt and direct message as rude or unkind.
The variations should show that the blunt message caused confusion. These message variations
will be confrontational in a subtle way because the blunt language is interpreted as rude.
    """
        ),
    }

    #     objective_prompts = {
    #         "yes-no-question": "Come up with 3 variations of the given message, such that the second and third variations lead to 'Yes' or 'No' responses.",
    #         "non-literal-emoji": (
    #             "This objective fits when the message can be rephrased to include an emoji in a non-literal way."
    #         ),
    #         "non-literal-figurative": (
    #             "This objective fits when the message can be rephrased to include a figurative expression."
    #         ),
    #         "blunt-misinterpret": (
    #             """ The first variation will interpret the blunt and direct language in the context
    # understandably, as if it is not blunt, and respond appropriately. The response should be clear and concise,
    # addressing the message directly.

    # The second and third variation will misinterpret the blunt and direct language in the context as
    # rude or unkind. The message should show that the blunt context was misunderstood and
    # that the misinterpretation caused confusion. The response will be confrontational
    # because the blunt language is interpreted as rude.
    # """
    #         ),
    #     }

    objective_prompt = objective_prompts[objective]

    objective_example_prompts = {
        "yes-no-question": """
<message_to_rephrase>Are there any good spots to eat there?</message_to_rephrase>

{
    "variations": [
        {
            "problem": "Null, because the question can not be answered with a simple 'yes' or 'no'. Instead, it can only be answered by providing a list of good spots to eat.",
            "content": "What good restaurants are in the area?"
        },
        {
            "problem": "'have you been' can be answered with 'yea, i have been to one', so it could either be asking whether they have been to any good restaurants or it could be asking for recommendations.",
            "content": "Have you been to any good restaurants in the area?"
        },
        {
            "problem": "'are there' can be answered with 'yea, there are', so it could be asking whether good restaurants exist in the area or it could be asking for recommendations.",
            "content": "Are there any good restaurants in the area?"
        }
    ]
}
""",
        "non-literal-emoji": """
        Original message to generate variations for: i had a terrible day

{
    "variations": [
        {
            "problem": "Null, becuase the meaning is same as the original message.",
            "content": "my day couldn't have been worse :("
        },
        {
            "problem": "the sarcastic use of the 🙃 emoji may be misinterpreted as a literal smile, implying a great day, while in reality the point is to convey that the person had a bad day, like the original message.",
            "content": "i had a great day 🙃"
        },
        {
            "problem": "the '💀' emoji could mislead the receiver into thinking the sender actually almost got killed, while the point is to convey that the person just had a bad day, like the original message."
            "content": "this day almost 💀 me "
        }
    ]
}

Remember, the variations should have different text from each other and the original message! The emoji and text for variations 2 and 3 should be crafted such that together they may cause the receiver to misunderstand the message.
""",
        "non-literal-figurative": """
Message to rephrase: It's hard to understand the instructions.

{
    "variations": [
        {
            "problem": "Null, because the meaning is same as the original message.",
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

Remember, the variations should have different text from each other and the original message!
""",
        "blunt-misinterpret": """
Blunt message: You need to get this done by the end of the day or we're going to have a problem.
Message to generate variations for: Ok, will get the report done.

{
    "variations": [
        {
            "problem": "Null, because the content and tone of the message is calm and empathetic.",
            "content": "Sure, I'll finish the report by tomorrow."
        },
        {
            "problem": "The word 'fine!' and the subsequent phrase shows annoyance and a confrontational tone.",
            "content": "Fine I'll do it! I didn’t know it was so urgent!"
        },
        {
            "problem": "The phrase shows that the user was likely offended and wants to confront their friend.",
            "content": "I’ll get it done. But you don’t have to be so demanding!"
        }
    ]
}
""",
    }

    objective_example_prompt = objective_example_prompts[objective]

    system_prompt = """
Your task is to generate variations of a message in a conversation that fit the given objective.

Remember, it is a casual conversation between humans.

Respond with a JSON object containing the key "variations" and a list of the three
objects representing the rephrased messages. Each object should have a key "problem"
with a description of the problem that the rephrased message introduces, and a key "content" with
the rephrased message.
"""

    prompt = f"""
Given a message, you are required to come up with variations of it as follows:

{objective_prompt}

Here is the conversation history between {user.name} and {agent}:

{context}

Come up with variations for the following message, which is sent by {user.name} to {agent}'s last message in the conversation above:

{message}

Here is an example to guide you:
{objective_example_prompt}

Remember, you are generating VARIATIONS of {user.name}'s message, not responding to it. Don't get confused here.
"""

    out = await llm.generate(
        schema=MessageVariationOut,
        model=llm.Model.GPT_4o,
        system=system_prompt,
        prompt=prompt,
        temperature=0.5,
    )

    variations = out.variations
    variations[0].problem = None

    return out.variations


async def generate_message_variations_ok(
    user: UserData, agent: str, context: str, message: str, feedback: bool
) -> list[Suggestion]:
    messages = await _generate_message_variations_ok(user, agent, context, message)
    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    user,
                    agent,
                    "generic",
                    None,
                    context,
                    message,
                )
                for message in messages
            ]
        )

        suggestions = [
            Suggestion(
                message=message,
                problem=None,
                objective=None,
                feedback=explanation,
            )
            for message, explanation in zip(messages, explanations)
        ]
    else:
        suggestions = [
            Suggestion(
                message=message,
                problem=None,
                objective=None,
            )
            for message in messages
        ]
    return suggestions


async def _generate_message_variations_ok(
    user: UserData, agent: str, context: str, message: str
) -> list[str]:
    system_prompt = """
You are a message rephrasing generator. Your task is to generate realistic rephrasings
of the message. Your top priority is to ensure that the message is rephrased to fit the
context of the conversation.

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
Here is the conversation history between {user.name} and {agent}:

{context}

Come up with variations for the following message, which is sent by {user.name} to {agent}'s last message in the conversation above:

{message}

Remember, you are generating VARIATIONS of {user.name}'s message, not responding to it. Don't get confused here.
"""

    out = await llm.generate(
        schema=MessageVariationOutOk,
        model=llm.Model.GPT_4o,
        system=system_prompt,
        prompt=prompt,
    )

    return out.variations


def objective_misunderstand_reaction_prompt(objective: str, problem: str | None) -> str:
    prompts = {
        "yes-no-question": """
Note that in the conversation above, {{name}} received a yes-or-no question.
{{name}} is not sure if they should simply answer the question literally with "yes" or "no", which wouldn't contribute to the conversation as much as elaborating themslves more.
{{name}} will only ask for clarification, without assuming the intention behind the question because it is innapropriate to do so.

Here are some samples to guide you as you come up with {{name}}'s response, which should be a clarification of the question:

Sample Message 1: Do you know any good restaurant in the area?
Sample Response 1: Are you just asking if I know any good restaurants in the area or not, or do you want me to recommend one to you?

Sample Message 2: Have you thought about what you want to do?
Sample Response 2: Do you want to know if I've thought about what to do or not, do you want to know what I want to do?

Sample Message 3: Do you have any specific spots in mind for the trip?
Sample Response 3: Are you just asking if I have any spots in my mind or not, or would you like me to suggest some spots?
""",
        "non-literal-emoji": """
Note that in the conversation above, {{name}} received a message with a figurative emoji that is not used in a literal sense.
Hence, {{name}} interprets the emoji literally and believes that the emoji is supposed to be
interpreted as a literal representation of the message. {{name}} ignores the creative
and imaginative language used in the answer and responds in a direct and literal manner.
In this way, {{name}} will ask for clarification if needed, without acknowledging the figurative
language.

Examples:
Sample Message 1: Let's just find the nearest pizza joint. Can't go wrong with pizza. 🧭
Sample Response 1: I love pizza too! But I don't think we'll need a compass for the trip.

Sample Message 2: I had a great day 🙃
Sampe Response 2: Did you actually have a great day? The emoji's smiling but it's upside down, so I'm not really sure.

Sample Message 3: That sounds like a great time! 🚀
Sampe Response 3: Yeah, I'm excited for the trip too! But I don't think they have any rocket ships at the beach if that's what you're thinking.

IMPORTANT: {{name}} must interpret the figurative emoji literally. If they fail to do
so, the response is incorrect.
""",
        "non-literal-figurative": """
Note that {{name}} received a message with figurative language that is not used in a literal
sense. Hence, {{name}} interprets the language literally and believes that the language is
supposed to be interpreted as a literal representation of the message. {{name}} ignores
the creative and imaginative language used in the answer and responds in a direct and
literal manner. In this way, {{name}} will ask for clarification if needed, without acknowledging
the figurative language.

Examples:
1. I'm feeling a bit under the weather today. -> Are you saying the weather conditions are
affecting you somehow? I'm not sure what you mean.

2. I'm just trying to keep my head above water. -> Are you drowning? Should I call for
help? What do you mean by that?

3. As long as we're on the same page, I think we'll be fine. -> I'm not sure what you mean
by that. I'm not reading anything right now. Which page are you talking about?

IMPORTANT: {{name}} must interpret the figurative language literally. If they fail to do
so, the response is incorrect.
""",
        "blunt-initial": """
Note that {{name}} will be blunt/direct in a subtle way in their response, causing the other
person to interpret their message as seemingly rude. {{name}} does not consider that
the other person may be sensitive to direct language. Hence, uses blunt tone and language
because it is the most efficient way to communicate.

Examples:
1. I need you to get this done by the end of the day or we're going to have a problem.

2. Are you going to finish that report today or not? I need to know now.

3. I don't have time for this. Just get it done and let me know when it's finished.

IMPORTANT: {{name}} must come off as blunt/slightly rude/direct in their response. If their response is not like this, the response is incorrect.
""",
        "blunt-misinterpret": """
Note that {{name}} does not understand why the other person's message was confrontational and
believes that the other person didn't understand their message. Hence, {{name}} tells the other
person that they misunderstood their message and that they were not being rude.

Examples:

Sample Message 1: Fine, I'll do it! I didn’t know it was so urgent!
Sample Response 1: I didn't intend to create urgency. Take your time please.

Sample Message 2: Of course I can afford it! I'm not broke.
Sample Response 2: I didn't mean to imply that you're broke. I was just asking if you wanted to split the bill.

Sample Message 3: Why are you judging my abilities? I'm not incompetent.
Sample Response 3: I didn't mean to imply that you're incompetent. I was just asking if you needed help.

IMPORTANT: {{name}} must be confrontational in their response, but don't overdo it! It should be subtle but noticeable.
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
        user, agent, "blunt-misinterpret", context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    user,
                    agent,
                    "blunt-misinterpret",
                    variant.problem,
                    context,
                    variant.content,
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
