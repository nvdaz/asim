from api import llm

FLOW_STATES = {
    "np_normal": {
        "options": [
            {"prompt": "np_normal", "next": "ap_normal"},
            {"prompt": "np_figurative", "next": "ap_figurative_misunderstood"},
            {"prompt": "np_emoji", "next": "ap_emoji_misunderstood"},
        ]
    },
    "ap_normal": {
        "options": [
            {"prompt": "ap_normal", "next": "np_normal"},
            {"prompt": "ap_blunt", "next": "np_blunt_confrontation"},
        ]
    },
    "ap_figurative_misunderstood": {
        "options": [
            {
                "prompt": "ap_figurative_misunderstood",
                "next": "feedback_figurative_misunderstood",
            }
        ]
    },
    "ap_emoji_misunderstood": {
        "options": [
            {
                "prompt": "ap_emoji_misunderstood",
                "next": "feedback_emoji_misunderstood",
            }
        ]
    },
    "np_blunt_confrontation": {
        "options": [
            {
                "prompt": "np_blunt_confrontation",
                "next": "feedback_blunt_confrontation",
            }
        ]
    },
    "np_clarify": {
        "options": [
            {"prompt": "np_clarify", "next": "ap_normal"},
        ]
    },
    "feedback_figurative_misunderstood": {
        "options": [
            {"prompt": "feedback_figurative_misunderstood", "next": "np_clarify"}
        ]
    },
    "feedback_emoji_misunderstood": {
        "options": [{"prompt": "feedback_emoji_misunderstood", "next": "np_clarify"}]
    },
    "feedback_blunt_confrontation": {
        "options": [{"prompt": "feedback_blunt_confrontation", "next": "np_normal"}]
    },
}

PROMPTS = {
    "np_normal": "",
    "np_figurative": (
        "Your next message is figurative and metaphorical. You are not "
        "aware of the needs of autistic individuals and send a message "
        "that is confusing or difficult to understand for them."
    ),
    "np_emoji": (
        "Your next message will use emojis to express how you feel. You use emojis "
        "that have a literal meaning and do not convey the intended emotion. Use "
        "emojis throughout your message. Example: 'I'm feeling 🌡️ great today! 💪'"
    ),
    "ap_normal": "",
    "ap_blunt": (
        "You send an extremely blunt message to the other person that will come "
        "acros as rude and offensive. Your message will not consider the other "
        "person's feelings and will be direct and to the point. Example: 'Why are "
        "you so stupid? Are you dumb?'"
    ),
    "np_blunt_confrontation": (
        "You just received a blunt message from the other person. You decide to "
        "confront them about it because you are offended. Your message is not "
        "considerate of the other person's feelings."
    ),
    "feedback_blunt_confrontation": (
        "The user just confronted the other person about a blunt message. The user "
        "could have been more considerate of the other person's feelings. The user "
        "could have expressed their feelings in a more respectful manner."
    ),
    "ap_figurative_misunderstood": (
        "You are responding to a figurative and metaphorical message. You "
        "misunderstand the figurative language and your next message will"
        "confidently interpret the message literally, missing the intended "
        "meaning. The response should be literal and direct, only addressing "
        "the figurative meaning and ignoring the intended message."
        "Example: NP: 'Let's hit the books' -> AP: 'Why would you want to "
        "hit books? That would damage them.'"
    ),
    "ap_emoji_misunderstood": (
        "You are responding to a message that uses emojis. You are confused "
        "by the emojis and your next message will confidently interpret the "
        "emojis literally, missing the intended emotional context. The "
        "response should be literal and direct, only addressing the literal "
        "meaning of the emojis and ignoring the intended emotional context."
        "Example: NP: 'I'm feeling great today! 💪' -> AP: 'Why the muscle "
        "emoji? Are you lifting weights?'"
    ),
    "np_clarify": (
        "You just sent a message that was misunderstood by the other person. "
        "You decide to clarify your message and provide more context to help the "
        "other person understand what you meant."
    ),
    "feedback_figurative_misunderstood": (
        "The autistic individual just misunderstood a figurative message. The user "
        "could have been more considerate and provided more context to help the "
        "autistic individual understand the intended meaning of the message."
    ),
    "feedback_emoji_misunderstood": (
        "The autistic individual just misunderstood a message that used emojis. "
        "The user could have been more considerate and provided more context to "
        "help the autistic individual understand the intended emotional context of "
        "the message."
    ),
}


async def __generate_chat_message(
    persona_name, persona, scenario, conversation_history, extra=""
) -> str:
    system_prompt = (
        f"{persona}\n{extra}\nScenario: {scenario}\nYou are chatting over text. Keep "
        "your messages under 50 words and appropriate for a text conversation. Put "
        f"your message in between '<' and '>'. Respond like this: "
        "'{persona_name}: <Hello!>'"
    )

    prompt_data = f"{conversation_history}\n{persona_name}: "

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    message = response[response.index("<") + 1 : response.index(">")]

    return message


async def __generate_feedback(
    user_name: str, subject_name: str, conversation_history: str, extra=""
) -> str:
    system_prompt = (
        "You are a feedback generator. Your task is to provide feedback on the "
        f"ongoing conversation between {user_name} and {subject_name}, who is "
        "an autistic individual. The conversation is happening over text."
        "Point out any misunderstandings, offensive remarks, or areas where"
        f"{user_name} could have been more considerate. Respond with a message that "
        f"directly address {user_name} as 'You' and provide constructive feedback in "
        "at most 50 words. Put your response in between '<' and '>'. If the user "
        "could not have done better, respond with '<no feedback>' and provide an "
        "analysis of the conversation using [analysis] tags outside of the '<' and '>' "
        f"describing why the user could not have done better. \n{extra}"
    )

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=conversation_history,
    )

    if "<no feedback>" in response:
        return None

    return response[response.index("<") + 1 : response.index(">")]


async def generate_next(
    state,
    user,
    user_persona,
    user_scenario,
    subject,
    subject_persona,
    subject_scenario,
    conversation_history,
):
    state_data = FLOW_STATES[state]

    ty = state[: state.index("_")]

    responses = []

    for option in state_data["options"]:
        prompt = PROMPTS[option["prompt"]]

        print(f"\033[90m[state: {state}, prompt: {option['prompt']}]\033[0m")
        if ty == "np":
            response = await __generate_chat_message(
                user,
                user_persona,
                user_scenario,
                conversation_history,
                extra=prompt,
            )

            responses.append({"response": response, "next": option["next"]})
        elif ty == "ap":
            response = await __generate_chat_message(
                subject,
                subject_persona,
                subject_scenario,
                conversation_history,
                extra=prompt,
            )

            responses.append({"response": response, "next": option["next"]})
        elif ty == "feedback":
            response = await __generate_feedback(
                user, subject, conversation_history, extra=prompt
            )

            responses.append({"response": response, "next": option["next"]})
        else:
            raise ValueError(f"Invalid type: {ty}")

    return ty, responses
