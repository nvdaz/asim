from pydantic import BaseModel

from api.schemas.chat import Feedback, Suggestion
from api.schemas.user import UserPersonalizationOptions

from . import llm


async def explain_suggestion(
    pers: UserPersonalizationOptions,
    agent: str,
    objective: str,
    problem: str | None,
    context: str,
    message: str,
) -> Feedback:
    objective_prompts = {
        ("yes-no-question", True): """
{user} asked a yes-or-no question that could be interpreted as either a yes or no
question or as a request for more information. {agent} could respond with a yes or no
answer, which is not what {user} is looking for. Instead, {user} should ask a
direct question to get the information they wanted from {agent}. Explain the specific
phrasing of the question that could be misinterpreted as simply a yes or no question,
and explain that the correct interpretation is unclear. Briefly mention people have
different communication styles and some may prefer direct language to avoid confusion.
""",
        ("yes-no-question", False): """
{user} asked a clear and direct question, avoiding the use of a yes-or-no question
that could be misinterpreted. This phrasing is more likely to elicit the information
that {user} is looking for as it is clear what information is being requested. Briefly
mention people have different communication styles and some may prefer direct language
to avoid confusion.
""",
        ("non-literal-emoji", True): """
{user} used an emoji in a non-literal way that could be misinterpreted by {agent}.
Explain specifically how emoji could be interpreted literally,and how this could be
confusing and misinterpreted. Therefore, {user} should use an emoji that clearly conveys
the intended meaning of the message. Briefly mention people have different communication
styles and some may prefer straightforward or no use of emojis to avoid confusion.

""",
        ("non-literal-emoji", False): """
{user} used an emoji in a clear and direct way, adding a visual element to their
message that enhances the meaning in a way that does not cause confusion. Briefly
mention people have different communication styles and some may prefer straightforward
or no use of emojis to avoid confusion.
""",
        ("non-literal-figurative", True): """
{user} used figurative language that could be misinterpreted as literal. Explain
specifically how the figurative language could be interpreted literally by {agent}, and
how this could be confusing and misinterpreted. Therefore, {user} should use clear and
direct language to convey their message. Briefly mention people have different
communication styles and some may prefer straightforward language to avoid confusion.
""",
        ("non-literal-figurative", False): """
{user} used clear and direct language to convey their message, avoiding the use of
figurative language that could be misinterpreted. This direct language is more likely
to be understood as intended. Briefly mention people have different communication styles
and some may prefer straightforward language to avoid confusion.
""",
        ("blunt-misinterpret", True): """
{user} was confrontational in response to {agent}'s blunt and direct language and
misinterpreted {agent}'s blunt language as rude. Explain how this might be {agent}'s
natural way of speaking. Clarify to {user}
what {agent} probably wanted to convey and that they did not intend to be rude. Briefly
mention that {user} should consider resonding in a more neutral way since people may
have different communication styles, and some may naturally sound blunt.
""",
        ("blunt-misinterpret", False): """
{user} responded appropriately to {agent}'s blunt language, considering that their blunt
language was not intended to be rude. {user}'s message is clear and direct, and it is
not confrontational to blunt language. Briefly mention that {user} should consider
resonding in a more neutral way since people may have different communication styles,
and some may naturally sound blunt.
""",
        ("generic", False): """
You are provided with {user}'s response to {agent}. Explain how {agent} will likely
interpret {user}'s emotional tone and intent from their message.
""",
    }
    objective_prompt = objective_prompts[(objective, problem is not None)].format(
        user=pers.name, agent=agent
    )

    action = (
        (
            """
Now, explain to {user} why their original message could be misinterpreted by {agent}.
The problem might possibly be that {problem}. Base your feedback on {agent}'s likely
thought process, their understanding of the tone and intent of {user}'s message, and
their likely response.

Here are some guidelines to help you provide feedback:
{objective_prompt}

Make sure to:

1. In your explanation, refer to specific aspect(s) using quotation marks from the original message that make it confusing.
2. Use simple, friendly, and straightforward language.
3. Limit your answer to less than 100 words.
4. Provide feedback, but NEVER provide alternative messages.

Secondly, provide a title with less than 50 characters that accurately summarizes your feedback alongside an emoji.

Remember, explain to {user} what elements of the original message might be confusing for {agent}.
You MUST NEVER repeat the original message in your feedback.


At the end is a model output based on the following sample original message:
"How about we find a place where we can dip our toes in the ocean right from our balcony?"

{{
    "title": "Clarify Figurative Expressions 🗣️",
    "feedback": "When you mention 'dip our toes in the ocean right from our balcony,' Stephanie could take it literally, thinking you actually want to be able to dip your toes in the ocean from the balcony. It might help to clearly specify that you're looking for a place with an ocean view and easy beach access to avoid confusion! 😊"
}}
"""
        )
        if problem is not None
        else (
            """
Now, explain to {user} why their original message is likely to be interpreted in the intended way by {agent}.
Base your feedback on {agent}'s likely thought process, their understanding of the tone and intent of {user}'s message, and their likely response.

Here are some guidelines to help you provide feedback:
{objective_prompt}

Make sure to:

1. In your explanation, refer to specific aspect(s) using quotation marks from the original message that make it clear.
2. Use simple, friendly, and straightforward language.
3. Limit your answer to less than 100 words.

Secondly, provide a title with less than 50 characters that accurately summarizes your feedback alongside an emoji.

Remember, explain to {user} what elements of the original message make it a clear message for {agent}.
You MUST NEVER repeat the original message in your feedback.


At the end is a model output based on the following sample original message:
"When would be a good time for you to plan a trip to Gloucester?"

{{
    "title": "Clear and Specific 🗓️",
    "feedback": "Your message seems clear and direct, asking for specific information regarding the timing of the trip. This will likely make it easier for Sean to understand exactly what information you are seeking and provide a useful and detailed response. There is no figurative language or ambiguity that could lead to confusion."
}}
"""
        )
    )

    action = action.format(
        user=pers.name, agent=agent, problem=problem, objective_prompt=objective_prompt
    )

    system_prompt_template = """
As a helpful communication guide, you are guiding {user} on their conversation with {agent}.

Respond with a JSON object with keys "title" and "feedback" containing your feedback.
"""

    system = system_prompt_template.format(
        objective_prompt=objective_prompt,
        user=pers.name,
        agent=agent,
    )

    prompt_template = """
Here is the conversation history between {user} and {agent}:
{context}

Here is the original message last sent by {user}:
{original}

{action}
"""

    prompt = prompt_template.format(
        user=pers.name, agent=agent, context=context, original=message, action=action
    )

    out = await llm.generate(
        schema=FeedbackOutput,
        model=llm.Model.GPT_4o,
        system=system,
        prompt=prompt,
    )

    return Feedback(title=out.title, body=out.feedback)


class FeedbackOutput(BaseModel):
    title: str
    feedback: str


async def explain_message(
    pers: UserPersonalizationOptions,
    agent: str,
    objective: str,
    problem: str | None,
    message: str,
    context: str,
    reaction: str,
    last3: str | None,
    suggestions: list[Suggestion] | None,
) -> Feedback:
    if not last3:
        last3 = "** Not given **"
    objective_prompts = {
        ("yes-no-question", True): """
{user} asked a question that could be interpreted either as requiring a yes or no answer
or as a request for more information. {agent} wasn't sure which interpretation of the
question was intended, so they asked for clarification.

Explain the specific wording in {user}’s question that led {agent} to be unsure of
whether to provide more information or simply give a yes or no answer. Emphasize that
there are two possible interpretations of the question and that it's not clear which one
was intended. Mention that people have different communication styles, and some, like
{agent}, may interpret questions in different ways.
""",
        ("yes-no-question", False): """
{user} asked a clear and direct question, avoiding the use of a yes-or-no question
that could be misinterpreted. This phrasing is unlikely to confuse {agent} as its
intended meaning is clear. Briefly mention people have different communication styles
and some may prefer direct language to avoid confusion.
""",
        ("non-literal-emoji", True): """
{user} used an emoji that could be interpreted in different ways, and {agent} understood
it in one specific way. While {user} may have intended the same meaning as {agent}, it’s
important to be aware that emojis can carry multiple interpretations depending on
context and personal perspective. Justify the emoji's intended meaning and explain how
it could be unclear.

Explain how the emoji could be understood differently and what factors might cause such
interpretations. Mention that people have diverse communication styles, and emojis can
be especially prone to varied meanings. Being mindful of this can help ensure the
intended message is received clearly.
""",
        ("non-literal-emoji", False): """
{user} used an emoji in a clear and direct way, adding a visual element to their
message without causing confusion. The intended meaning of the emoji is unlikely to be
confused by {agent} as it aligns with the message’s tone and context. Briefly mention
people have different communication styles and some may prefer straightforward or no
use of emojis to avoid confusion.
""",
        ("non-literal-figurative", True): """
{user} used figurative language that could be interpreted by {agent} in many ways,
leading to potential confusion. While {user} may have intended a specific meaning,
figurative language can be open to interpretation, so {agent} may not have understood it
as intended.

Explain how the figurative language used could have been interpreted either
literally or figuratively by {agent}. Discuss the intended meaning of {user}’s
figurative language and describe how it relies on a figurative interpretation. Then
describe in detail why it might have been misunderstood. Mention that people have
different communication styles, and some may prefer straightforward, direct language to
minimize misunderstandings.
""",
        ("non-literal-figurative", False): """
{user} used clear and direct language to convey their message, avoiding the use of
figurative language that could be misinterpreted. This direct language is more likely
to be understood as intended. Briefly mention people have different communication styles
and some may prefer straightforward language to avoid confusion.
""",
        ("blunt-misinterpret", True): """
Begin by mentioning how {user}'s latest message was confrontational towards {agent}.
This was possibly because they misinterpreted {agent}'s blunt language as rude. Consider
that {agent} might naturally express themselves in a straightforward manner, which could
be perceived as blunt by {user}. Explain why {user} might have found {agent}'s message
rude and how {agent}’s blunt language could have been misinterpreted from their message:

{last3}

Briefly mention that {user} could approach responses more thoughtfully, keeping in mind
that people communicate differently. What may seem rude to one person could simply be
directness from another.
""",
        ("blunt-misinterpret", False): """
{user} responded empathetically to {agent}'s blunt language, considering that their
blunt language was not intended to be rude. {user}'s message is clear and direct, and it
is not confrontational to blunt language. Briefly mention that {user} should consider
resonding in a more neutral way since people may have different communication styles,
and some may naturally sound blunt.
""",
    }

    examples_problem = {
        "blunt-misinterpret": """
At the end is a model output to help you out:
Blunt message by John: Kyle, we already talked about finding budget-friendly places. How about you just search for some cheap hostels or Airbnbs? We don't have time to go back and forth on this.
Confrontational message by Kyle: I thought you would have some suggestions ready.
John's reaction: I didn't mean I wouldn't help, Kyle. I thought you'd want to find some options since you're so into exploring and all that. I can help you search if you need it.

{
    "title": "Avoid Confrontational Tone 🗣️",
    "feedback": "John was possibly just being straightforward and wanted to clarify that you should look for cheap hostels or Airbnbs as there is not a lot of time left until the trip. The phrase 'I thought you would have some suggestions ready' can come across as confrontational and show annoyance. John might have taken this as you being upset that he didn't have recommendations prepared. This might not have been clear, likely causing the misunderstanding."
}
""",
        "non-literal-figurative": """
At the end is a model output to help you out:
Sample original message: "How about we find a place where we can dip our toes in the ocean right from our balcony?"

{
    "title": "Clarify Figurative Expressions 🗣️",
    "feedback": "When you said “dip our toes,” you were probably thinking of a place with an ocean view and easy beach access. However, Stephanie took the phrase literally, thinking you meant being able to physically dip your toes into the ocean directly from the balcony since dipping toes is a literal action. Specifying directly that you’re looking for an ocean-view property with convenient beach access could help prevent any mix-ups! 😊"
}
""",
        "yes-no-question": """
At the end is an example that you should use to model your output on:
Sample message that caused confusion: "Do you know any good restaurants in NYC?"
Sample response from confused recipient: "Are you just asking if i know any good restaurants in NYC or not, or do you want me to share names of my favorite restaurants with you?"

{
    "title": "Be Direct for Clear Communication 🎯",
    "feedback": "The phrase 'Do you know' might prompt Maria to interpret the question literally and respond with just a 'yes' or 'no' but it could also be seen as a request for Maria to elaborate and provide recommendations for specific good restaurants in NYC. Maria's response shows she was unsure if you were asking for information or recommendations. If you want specific recommendations, it's best to ask directly for them to avoid confusion. 😊"
}
""",
        "non-literal-emoji": """
At the end is a model output to help you out:
Sample original message with confusing emoji: "Can't wait for our adventure! This trip will be unforgettable 🏥"
Sample reaction of the confused recipient: "sounds great, frank! but i noticed the hospital emoji, are you worried about something happening on the trip?"

{
    "title": "Emoji Confusion Explanation 🙃",
    "feedback": "When you described the trip as ‘unforgettable’ and used the hospital emoji 🏥, Regina might have thought you were referencing something serious, like an injury or emergency. You likely intended it to emphasize how intense or memorable the trip could be — similar to how a hospital visit might be an unforgettable experience. However, the hospital emoji can also suggest something negative or concerning, such as getting seriously hurt during the trip. This likely led Regina to ask if you were worried. Since emojis can have different meanings depending on context, it’s helpful to consider how they might be interpreted, as people have varying communication styles. 😊"
}
""",
    }

    examples_good = {
        "yes-no-question": """
At the end is a model output to help you out:
Sample original message that was clear: "What books would you recommend, Joseph?"

{
    "title": "Clear and Direct 🎯",
    "feedback": "Frank, your question worked well because it directly asked Joseph for book recommendations, making your intent clear. In comparison, asking "Is there a good book you know of?" could be interpreted as asking for confirmation with a response like "Yes, there is," OR as a request for specific recommendations. Similarly, "Have you read any good books lately?" could prompt a response like "I have," OR lead Joseph to share book titles. Both interpretations are valid for these suggestions, but your clear and direct question avoided potential ambiguity and encouraged useful recommendations. Keep using straightforward language for effective communication!"
}
""",
        "non-literal-emoji": """
At the end is a model output to help you out:
Sample original message that was clear: "Great idea, Joseph! Let's explore more seafood places in Gloucester. 🦞 We have beach barbecue, whale watching, and fresh seafood on our list. I want to visit some historical sites too. This trip will be amazing!"

{
    "title": "Good Emoji Usage 🎨",
    "feedback": "Frank, your choice of '🦞' fit the context of exploring seafood spots, adding clarity without causing confusion. Unlike '🚀,' which might suggest space-related activities, or '️‍🔥,' which could imply an actual fire, your message stayed focused and relevant. This thoughtful approach aligned well with Joseph's expectations, resulting in a positive and engaging response."
}
""",
        "non-literal-figurative": """
At the end is a model output to help you out:
Sample original message that was clear: "Let's meet there at 6pm, and we can enjoy the sunset after dinner 🌅"

{
    "title": "Clear Invitation to Enjoy Sunset 🌅",
    "feedback": "Frank, your message was clear and straightforward. Kaitlin responded with a relevant question about whale watching, showing she understood your plan to meet at 6pm and enjoy the sunset. The other suggestions like 'paint the sky' and 'chase the sun' might have confused Kaitlin, making her think of actual activities like painting or running. Your choice avoided these potential misunderstandings, making your plan clear and easy to follow."
}
        """,
        "blunt-misinterpret": """
At the end is a model output to help you out:
Sample blunt message: "We need to book the whale tour now. Check your schedule."
Sample constructive response: "I understand the urgency. I'll check my calendar right away and get back to you."

{
    "title": "Positive Response to Direct Communication 🤝",
    "feedback": "Your response acknowledged the urgency while maintaining a cooperative tone. Remember that some people naturally communicate in a direct, blunt way without intending to be rude. Unlike responses like 'Why are you being so pushy?' which can escalate tension, you focused on the task while understanding different communication styles. This approach helped maintain a positive interaction and showed your willingness to cooperate. Keep up the good work!"
}
""",
    }

    example = (
        examples_problem.get(objective, examples_problem["non-literal-figurative"])
        if problem is not None
        else examples_good.get(objective, examples_good["non-literal-figurative"])
    )

    objective_prompt = objective_prompts[(objective, problem is not None)].format(
        user=pers.name, agent=agent, last3=last3
    )

    system_prompt_template = """
As a helpful communication guide, you provide communication assistance and feedback.

Respond with a JSON object with keys "title" and "feedback" containing your feedback.
"""

    system = system_prompt_template.format(
        user=pers.name,
        agent=agent,
    )

    if problem is None:
        assert suggestions is not None
        suggestions_str = "\n".join(
            [
                f"Message: {s.message} | Problem: {s.problem}"
                for s in suggestions
                if s.problem is not None
            ]
        )
    else:
        suggestions_str = ""

    action = (
        f"""
Now, based on {agent}'s response, explain to {pers.name} why their original message was {"confrontational towards" if objective == "blunt-misinterpret" else "confusing for"} {agent}.
Use {agent}'s response to extract their likely thought process and ground your explanation in it.
{f"Some people naturally use blunt language, so {agent} might not have intended to be rude." if objective == "blunt-misinterpret" else ""}

Make sure to:

1. In your explanation, refer to specific aspect(s) using quotation marks from the original message that make it {"confrontational" if objective == "blunt-misinterpret" else "unclear"}.
2. Use simple, friendly, and straightforward language.
3. Limit your answer to less than 100 words.
4. Provide feedback, but NEVER provide alternative messages.

Secondly, provide a title with less than 50 characters that accurately summarizes your feedback alongside an emoji.

Remember, explain to {pers.name} what elements of the original message are {"confrontational" if objective == "blunt-misinterpret" else "confusing"} for {agent}.
"""
        if problem is not None
        else f"""
Now, based on {agent}'s response, explain to {pers.name} why their original message was interpreted in the intened way by {agent}.
Use {agent}'s response to extract their likely thought process and ground your explanation in it.

Compare it to the following suggestions, which were problematic:
{suggestions_str}

Make sure to:
1. In your explanation, refer to the key aspect from each problematic suggestion using quotation marks.
2. Explain, in detail, why the problematic suggestions (refer to them as the other suggestions) were {"confrontational" if objective == "blunt-misinterpret" else "confusing"} and how {agent} might have interpreted them.
3. Briefly say that the message {pers.name} selected was a good choice because they avoided the issues present in the other suggestions.
4. Use simple, friendly, and straightforward language.
5. Limit your answer to less than 100 words.
6. Provide feedback, but NEVER provide alternative messages.

Secondly, provide a title with less than 50 characters that accurately summarizes your feedback alongside an emoji.

Remember, explain to {pers.name} what elements of the original message make it a clear message for {agent}.
"""
    )

    prompt_template = """
{objective_prompt}

Here is the conversation history between {user} and {agent}:
{context}

Here is the original message last sent by {user}:
{original}

Here is {agent}'s response to {user}'s message above:
{reaction}

{action}

You MUST NEVER repeat the original message in your feedback.

Your feedback should be so detailed and simple that it explains every bit step-by-step, such that a five-year-old could understand it.
Reinforce the main points of the feedback to ensure {user} understands it.

{example}
"""

    prompt = prompt_template.format(
        user=pers.name,
        agent=agent,
        context=context,
        original=message,
        reaction=reaction,
        problem=problem,
        objective_prompt=objective_prompt,
        action=action,
        example=example,
    )

    out = await llm.generate(
        schema=FeedbackOutput,
        model=llm.Model.GPT_4o,
        system=system,
        prompt=prompt,
    )

    return Feedback(title=out.title, body=out.feedback)


class FeedbackContentOnly(BaseModel):
    feedback: str


async def explain_message_alternative(
    pers: UserPersonalizationOptions,
    agent: str,
    objective: str,
    message: str,
    context: str,
    original: str,
    feedback_original: str,
) -> str:
    objective_prompts = {
        "yes-no-question": """
Provide feedback on the clarity of the alternative message compared to the original.
Consider how the phrasing affects how easily the recipient can understand the intended
meaning. Focus on whether the original message could be interpreted in multiple ways
(such as expecting a yes-or-no answer or more details). Discuss how the alternative
message might make the intended meaning clearer, even though it may not be inherently
better. Avoid assuming the sender’s exact intent.
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
    objective_prompt = objective_prompts[objective].format(user=pers.name, agent=agent)

    system = f"""
As a helpful communication guide, you are guiding {pers.name} on their conversation with {agent}.

{objective_prompt}

Respond with a JSON object with key "feedback" containing your feedback.
"""
    prompt = f"""
Here is the conversation history between {pers.name} and {agent}:
{context}

Here is the original message last sent by {pers.name}:
{original}

Here is the alternative message for the message above:
{message}

{pers.name} received the following feedback on their original message:
{feedback_original}

Now, explain to {pers.name} how the alternative message differs from the original.

Make sure to:

1. Focus on the specific aspect(s) in the alternative that could make it more clear.
2. Use simple, specific and straightforward language.
3. Limit your answer to less than 100 words.
4. NEVER repeat the alternative messages in your feedback, only provide feedback.

Remember, explain to {pers.name} the elements of the alternative message that could make
the intended meaning less ambiguous than the original. NEVER repeat the message.

At the end is a model output based on the following sample alternative message:
"I think we should reserve our spots for whale watching ahead of time to ensure we don't miss it."
{{
    "feedback": "The alternative message clarifies the intended meaning by specifying the action (reserving spots) and explaining the reason (ensuring participation). While the original message may not have conveyed the intended meaning clearly, the alternative version makes the purpose and required action more explicit, reducing the chance of misunderstanding. This direct approach helps ensure the intended message is easier to interpret."
}}
"""

    res = await llm.generate(
        schema=FeedbackContentOnly,
        model=llm.Model.GPT_4o,
        system=system,
        prompt=prompt,
    )

    return res.feedback
