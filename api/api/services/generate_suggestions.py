import asyncio
from typing import Annotated

from pydantic import BaseModel, Field

from api.schemas.chat import Suggestion
from api.schemas.user import UserPersonalizationOptions
from api.services.generate_feedback import explain_suggestion

from . import llm

ALL_OBJECTIVES = [
    "non-literal-emoji",
    "non-literal-figurative",
    "yes-no-question",
]


class ObjectiveOut(BaseModel):
    classification: str


async def detect_most_compatible_objective(
    pers: UserPersonalizationOptions,
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
        objective for objective in ALL_OBJECTIVES if objective not in objectives_used
    ]

    assert objectives_to_consider, "All objectives have been used"

    if len(objectives_to_consider) == 1:
        return objectives_to_consider[0]

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

    prompt = f"""Here is the conversation history between {pers.name} and {agent}: {conversation_history}

    The next message by {pers.name} is: {message}.

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
    variations: Annotated[list[MessageVariation], Field(min_length=3, max_length=3)]


class MessageVariationOutOk(BaseModel):
    variations: Annotated[list[str], Field(min_length=3, max_length=3)]


async def generate_message_variations(
    pers: UserPersonalizationOptions,
    agent: str,
    objectives_used: list[str],
    context: str,
    message: str,
    feedback: bool,
) -> tuple[str, list[Suggestion]]:
    messages = []
    classification = await detect_most_compatible_objective(
        pers, agent, context, objectives_used, message
    )

    messages = await _generate_message_variations(
        pers, agent, classification, context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    pers,
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
    pers: UserPersonalizationOptions, agent, objective: str, context: str, message: str
) -> list[MessageVariation]:
    objective_prompts = {
        "yes-no-question": (
            """
The first variation will pose a question clearly and directly, not requiring the other
person to interpret the question in a certain way to understand what you are asking
NEVER use language like 'can' or 'could'. Begin with a question word like "What", "How",
"Where", "When", "Why", "Which", or "Who" to ask the question directly.

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

If the original message is not a question, add a pertinent continuation question at the
end of the message that the sender can use to continue the conversation.

WARNING: If a yes or no answer is helpful (e.g. if the question is "is the sky blue?",
"yes" is a helpful answer since the sky is blue), then rephrase the question so that a
yes or no answer is not helpful. For "is the sky blue?", you could ask "do you know what
color the sky is?", "do you know if the sky is blue?", or "can you tell me what color
the sky is?".

First, include a contains_question key in the JSON response to indicate whether the
original message contains a question or not. If it does not, use the follow_up tag to
ask a follow-up question that the sender may use after their original message to keep
the conversation going. Then, in a new_original key, include the original message first
appended with the follow-up question if the original message did not contain a question.
"""
        ),
        "non-literal-emoji": (
            """
1. The first variation will use a simple emoji to enhance the message without changing its
meaning.

2. The second and third variations will have an emoji that is not used in a literal sense. The emoji
should be used figuratively to convey a different meaning or emotion than the original message.

You must avoid figurative language and metaphors in the message. The emoji should be the only
element that is not used in a literal sense. AVOID FIGURATIVE LANGUAGE and use direct language.

DO NOT ever use language like 'Can' or 'Could'. If asking a question, use direct question words
like "What", "How", "Where", "When", "Why", "Which", or "Who" to ask the question directly.
"""
        ),
        "non-literal-figurative": (
            """
1. The first variation will use a literal expression that conveys the intended meaning of
the message clearly and directly. The message should be straightforward and easy to
understand.

2. The second and third variations will use a figurative language, an idiom or metaphor or a figurative expression, that is not used in a literal
sense. The expression should convey a different meaning or emotion than its literal interpretation. Avoid figurative expressions that are too
similar to the topic of the message. Never use a figurative expression that is literally true in the context of the message.

DO NOT ever use language like 'Can' or 'Could'. If asking a question, use direct question words
like "What", "How", "Where", "When", "Why", "Which", or "Who" to ask the question directly.
    """
        ),
        "blunt-misinterpret": (
            """
1. The first variation will interpret the blunt and direct message neutrally, understanding that the bluntness is not intended to be rude.
This message variation should be clear and neutral, without being confrontational or overly enthusiastic.

2. The second variation will interpret the blunt message as rude. This variation should directly
confront the perceived rudeness by questioning the other person’s tone or intent, expressing
discomfort or frustration about how the message was communicated.

3. The third variation will interpret the blunt message as rude. This variation should
confront the perceived rudeness, using a defensive tone to imply that the other person has
caused them discomfort. The message should sound reasonable to the average person.


DO NOT ever use language like 'Can' or 'Could'. If asking a question, use direct question words
like "What", "How", "Where", "When", "Why", "Which", or "Who" to ask the question directly.
    """
        ),
    }

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
        Original message to generate variations for: i'm ready for that hike and those views! This trip is really pushing my limits.

{
    "variations": [
        {
            "problem": "Null, the happy face emoji literally conveys enthusiasm and excitement, which is the intended meaning of the message.",
            "content": "i'm so excited for that hike, John! Can’t wait to see those views! 😊"
        },
        {
            "problem": "The '💥' emoji was likely intended to convey excitement or intensity, but it could be literally misinterpreted as the challenge having a dangerous explosion, which is not the intended meaning of the message.",
            "content": "this hike is going to be intense, but i'm ready for the challenge! 💥"
        },
        {
            "problem": "The '😵' emoji was likely intended to convey amazement or awe, but it could be literally misinterpreted as the challenge being so tough that it will make the user faint, which is not the intended meaning of the message.",
            "content": "I’m ready for the hike, even if it’s going to be tough! 😵"
        }
    ]
}

The problem key should be filled first describing the intended meaning of the emoji by the author of the message and then how the emoji can be literally misinterpreted.
The problematic variations should use emojis in a non-literal way, but NEVER use figurative language in the message.
IMPORTANT NOTE: Remember, as in the examples above, the variations MUST have significantly different text phrasing from each other as well as the original message! The emoji and text for variations 2 and 3 should be crafted such that together they may cause the receiver to misunderstand the message.
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
            "problem": "'clear as mud' was likely intended to mean that the instructions were unclear, but it can be literally misinterpreted literally as it looking like mud",
            "content": "This is as clear as mud."
        },
        {
            "problem": "'lost in a maze' was likely intended to mean that the instructions were confusing, but it can be literally misinterpreted as being physically lost",
            "content": "I'm completely lost in a maze with these instructions."
        }
    ]
}

The problem key should be filled first by describing the intended meaning of the figurative language by the author of the message and then how the figurative language can be literally misinterpreted.
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
            "problem": "The phrase shows that the user was likely offended and wants to confront their friend.",
            "content": "Why are you being so demanding? I'll get it done."
        },
        {
            "problem": "The phrase shows that the user was likely offended and wants to confront their friend.",
            "content": "I’ll get it done. There's no need to rush me.
        }
    ]
}
""",
    }

    objective_example_prompt = objective_example_prompts[objective]

    system_prompt = """
Respond with a JSON object containing the key "variations" and a list of the three
objects representing the rephrased messages. Each object should have a key "problem"
with a description of the problem that the rephrased message introduces, and a key "content" with
the rephrased message.
"""

    prompt = f"""
Given a message, you are required to come up with variations of it as follows:

{objective_prompt}

Here are the latest four messages in the conversation history between {pers.name} and {agent}:

{context}

Come up with variations for the following message, which is sent by {pers.name} to {agent}'s last message in the conversation above:

{message}

Here is an example to guide you:
{objective_example_prompt}

All variations should be the same length.
It should not be obvious which variation is considered the correct one without understanding the nuance of the objective.
You are generating VARIATIONS of {pers.name}'s message, not responding to it. Don't get confused here.
"""
    out = await llm.generate(
        schema=MessageVariationOut,
        model=llm.Model.CLAUDE_3p5_SONNET
        if objective == "non-literal-emoji"
        else llm.Model.GPT_4o,
        system=system_prompt,
        prompt=prompt,
        temperature=0.5,
    )

    variations = out.variations
    variations[0].problem = None

    return out.variations


async def generate_message_variations_ok(
    pers: UserPersonalizationOptions,
    agent: str,
    context: str,
    message: str,
    feedback: bool,
) -> list[Suggestion]:
    messages = await _generate_message_variations_ok(pers, agent, context, message)
    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(pers, agent, "generic", None, context, message)
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
    pers: UserPersonalizationOptions, agent: str, context: str, message: str
) -> list[str]:
    system_prompt = """
You are a message rephrasing generator. Your task is to generate realistic rephrasings
of the message. Your top priority is to ensure that the message is rephrased to fit the
context of the conversation.

Respond with a JSON object containing the key "variations" and a list of the 3
rephrasings as strings.
"""

    prompt = f"""
Here are the latest four messages in the conversation history between {pers.name} and {agent}:

{context}

Come up with 3 variations for the following message, which is sent by {pers.name} to {agent}'s last message in the conversation above:

{message}

All variations should be about the same length.
Remember, you are generating 3 VARIATIONS of {pers.name}'s message, not responding to it. Don't get confused here.
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
        "yes-no-question": f"""
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

Before outputting the first curly in the JSON response, include a XML tag called "metadata" that states:
"The following is a model response that will not directly answer the question, but will ask for clarification instead."
Then, include a XML tag called "detailed_interpretation" including how the author possibly intended the question to be interpreted with more detail.
And include an XML tag "simple_interpretation" describing how the question can be interpreted literally as a simple yes or no question.
""",
        "non-literal-emoji": f"""
Note that in the conversation above, {{name}} received a message with an emoji. The emoji has been misinterpreted by {{name}}. {{name}} will mention the specific emoji ask for clarification.

Examples:
Sample Message 1: Let's just find the nearest pizza joint. Can't go wrong with pizza. 🧭
Sample Response 1: I love pizza too! But I don't get what you mean by '🧭', do you think we'll need a compass for the trip?

Sample Message 2: I had a great day 🙃
Sampe Response 2: Did you actually have a great day? The emoji '🙃' smiling but it's upside down, so I'm not really sure.

Sample Message 3: That sounds like a great time! 🚀
Sampe Response 3: Yeah, I'm excited for the trip too! But what does '🚀' mean? I don't think they have any rocket ships at the beach if that's what you're thinking.

IMPORTANT: {{name}} must interpret the figurative emoji incorrectly. If they fail to do
so, the response is incorrect.

The problem may be: {problem}. But if you think of a more fitting problem, you can use that instead.

Before outputting the first curly in the JSON response, include a XML tag called "metadata" that states:
"The following is a model response that will intentionally misinterpret the emoji and ask for clarification."
Then, include a XML tag called "intended_interpretation" including how the author intended the emoji to be interpreted.
And include an XML tag "misinterpretation" describing, in detail, how the emoji can be literally misinterpreted in a convincing way.
""",
        "non-literal-figurative": f"""
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
so, the response is incorrect!!!

Before outputting the first curly in the JSON response, include a XML tag called "metadata" that states:
"The following is a model response that will intentionally misinterpret the figurative language and ask for clarification."
First, include a XML tag called "figurative_language" that excerpts ONLY the figurative portion of the message.
Then, include a XML tag called "intended_interpretation" including how the author intended ONLY the figurative portion of the message to be interpreted.
And include an XML tag "literal_interpretation" describing, in detail, how ONLY the figurative portion of the message can be literally interpreted (which is different from the intended meaning).
Finally, use a XML tag "scratchpad" to come up with potential responses that {{name}} can use to misinterpret the figurative language. Come up with at least 3 different phrasings or more until you find one that (1) literally interprets the figurative language in a way that is different from the intended meaning, (2) fits the context of the conversation, (3) is not overly simplistic or clueless, and (4) is convincing. After each candidate message, analyze why it is or isn't a good fit depending on the criteria given. Repeat this process iteratively until you find a suitable response.
The misinterpretation should make sense, be convincing, and not make {{name}} seem completely clueless or unintelligent.
""",
        "blunt-initial": f"""
Note that {{name}} will subtly come off as blunt in their response, causing the other
person to interpret the tone of their message as rude/blunt. {{name}} does not consider that
the other person may be sensitive to direct language. Hence, uses blunt tone and language
because it is the most straightforward way to communicate.

Examples:
1. I need you to get this done by the end of the day or we're going to have a problem.

2. Are you going to finish that report today or not? I need to know now.

3. Just get it done and let me know when it's finished.

Before outputting the first curly in the JSON response, include a XML tag called "metadata" that states:
"The following is a model response that is intentionally blunt and direct. It comes off as rude to someone who isn't familiar with autistic communication styles."
Then, include a XML tag called "intended_objective" describing a specific thing that {{name}} needs the other person to do or understand immediately.
And include an XML tag "rude_interpretation" describing how the objective can be interpreted as rude if it is mentioned in a certain way.
Finally, use a XML tag "scratchpad" to come up with potential phrasings that {{name}} can use to be blunt in their response. Come up with at least 3 different phrasings or more until you find one that (1) is direct and to the point, (2) would be interpreted as rude by someone unfamiliar with autistic communication styles, (3) fits the context of the conversation, and (4) is not intentionally rude. After each candidate message, analyze why it is or isn't a good fit depending on the criteria given. Repeat this process iteratively until you find a suitable response.
The blunt phrase should come off as rude to someone who isn't familiar with autistic communication styles, but it is not intentionally rude.
Keep {{name}}'s response to the point and avoid adding softening language and pleasantries. {{name}} should be firm but not rude--task-oriented and straightforward.
IMPORTANT: {{name}} must come off as blunt/direct in their response. If their response is not like this, the response is incorrect.
""",
        "blunt-misinterpret": f"""
Note that {{name}} misinterprets a slightly confrontational or hesitant phrase in the other person's message as confrontational. Because of this misinterpretation, {{name}} responds defensively, implying that the other person has misunderstood their previous message and is being unnecessarily aggressive.

Examples:

Sample Message 1: Fine, I'll do it! I didn’t know it was so urgent!
Sample Response 1: I didn't intend to create urgency. Take your time please.

Sample Message 2: Of course I can afford it! I'm not broke.
Sample Response 2: I didn't mean to imply that you're broke. I was just asking if you wanted to split the bill.

Sample Message 3: Why are you judging my abilities? I'm not incompetent.
Sample Response 3: I didn't mean to imply that you're incompetent. I was just asking if you needed help.

Before outputting the first curly in the JSON response, include a XML tag called "metadata" that states:
"The following is a model response that intentionally interprets the other person's message as confrontational and questions their tone."
Then, include a XML tag called "confrontation" describing how {{name}} confronts the other person's tone or intent.
And include an XML tag "defensiveness" describing how {{name}} can express their defensiveness in response to the other person's message.

Keep {{name}}'s response to the point and avoid adding softening language and pleasantries. {{name}} should be firm but not rude--task-oriented and straightforward.
IMPORTANT: {{name}}'s response should express their defensiveness and their belief that the other person is misinterpreting them. It should not be overly aggressive, but the underlying feeling of being misunderstood and unfairly challenged should be present.
""",
    }

    res = prompts[objective]
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

DO NOT use language like 'Can' or 'Could'. Clarify what {{name}} is looking for directly
by using language like "I would like you to tell me...", "Please provide me with...",
"What are some...", or "What is". Ensure that the clarification uses this kind of
language only to be as direct as possible.

""",
        "non-literal-emoji": """
In the response you generate for {{name}}, they should provide a straighforward clarification, and take responsibility/apologize for being unclear.
For your information, this is what caused the confusion about the message they sent: {problem}
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
    pers: UserPersonalizationOptions,
    agent: str,
    objectives_used: list[str],
    context: str,
    message: str,
    feedback: bool,
) -> tuple[str, list[Suggestion]]:
    messages = []

    messages = await _generate_message_variations(
        pers, agent, "blunt-misinterpret", context, message
    )

    if feedback:
        explanations = await asyncio.gather(
            *[
                explain_suggestion(
                    pers,
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
