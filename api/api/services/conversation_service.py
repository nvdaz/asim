import json
import random

from . import llm_service as llm


async def _generate_conversation_scenario(user_info: dict) -> dict:
    system_prompt = (
        "As a scenario generator, your task is to generate an everyday conversational "
        "scenario that could happen over a text messaging app based on a user's "
        "profile. The scenario should be a generic situation that could happen between "
        "the user '{{USER}}' and an unfamiliar person '{{SUBJECT}}' in real life. The "
        "scenario should be realistic and relatable. Respond with a JSON object. The "
        "'user_scenario' key should be a string describing the user's perspective in "
        "the scenario (begin with 'you'), the 'subject_scenario' key should be a "
        "string describing the subject's perspective (begin with 'you'), and the "
        "'user_goal' key should be a string describing the user's objective in the "
        "scenario (begin with a verb, e.g., 'Convince', 'Explain', 'Find out')."
    )

    sampled_interests = random.sample(
        user_info["interests"], min(6, len(user_info["interests"]))
    )
    prompt_data = json.dumps({**user_info, "interests": sampled_interests}, indent=2)

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    json_str = response[response.index("{") : response.rindex("}") + 1]

    return json.loads(json_str)


def _generate_vocal_styles():
    VOCAL_STYLES = [
        "Echolalia (repeat what others say)",
        "Stilted Speech (speak in a formal, stiff manner)",
        "Literal Interpretation (interpret words literally)",
        "Repetitive Speech (repeat words or phrases)",
        "Idiosyncratic Phrasing (use unique phrases)",
        "Hyperlexia (use advanced vocabulary)",
        "Hyperverbal (talk excessively)",
        "Clipped Speech (use short, abrupt sentences)",
        "Flat Affect (lack of emotional expression)",
        "Verbose Speech (provide more information than necessary)",
        "Scripted Speech (use pre-rehearsed phrases)",
        "Pedantic Speech (focus on precise details)",
        "Blunt Speech (speak in a direct, straightforward manner)",
        "Interest Inertia (focus on a single topic, regardless of context)",
    ]

    return random.sample(VOCAL_STYLES, random.randint(3, 5))


async def _generate_base_subject_info(scenario):
    system_prompt = (
        "Generate a persona for the autistic person described in the provided scenario"
        "(who is referred to as 'you'). The persona should be based on the information "
        "provided in the scenario. Respond with a JSON object containing the following "
        "keys: 'age', 'occupation', and 'interests'."
    )

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    json_str = response[response.index("{") : response.rindex("}") + 1]

    return json.loads(json_str)


async def _generate_subject_persona_info(scenario):
    subject_info = await _generate_base_subject_info(scenario)
    vocal_styles = _generate_vocal_styles()

    subject_info["vocal_styles"] = vocal_styles

    return subject_info


async def _generate_subject_persona_from_info(subject_name: str, subject_info: dict):
    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "The persona is an autistic individual who struggles to communicate "
        "effectively with others. The persona should exhibit the vocal styles "
        "of an autistic person and should be ignorant of the needs of neurotypical "
        "individuals due to a lack of experience with them. The persona should be a "
        "realistic and relatable character who is messaging over text with another "
        f"person. Put the prompt in '<' and '>'. Start with 'You are {subject_name}...'"
    )

    prompt_data = json.dumps({**subject_info, "name": subject_name})

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    persona = response[response.index("<") + 1 : response.index(">")]

    return persona


async def _generate_subject_persona(scenario):
    subject_name = "Alex"
    subject_info = await _generate_subject_persona_info(scenario)
    subject_info["name"] = subject_name

    subject_persona = await _generate_subject_persona_from_info(
        subject_name, subject_info
    )

    return subject_info, subject_persona


async def _create_conversation_info(user_info: dict):
    scenario = await _generate_conversation_scenario(user_info)
    subject_info, subject_persona = await _generate_subject_persona(
        scenario["subject_scenario"]
    )

    user_scenario = (
        scenario["user_scenario"]
        .replace("{{USER}}", user_info["name"])
        .replace("{{SUBJECT}}", subject_info["name"])
    )

    subject_scenario = (
        scenario["subject_scenario"]
        .replace("{{USER}}", user_info["name"])
        .replace("{{SUBJECT}}", subject_info["name"])
    )

    user_goal = (
        scenario["user_goal"]
        .replace("{{USER}}", user_info["name"])
        .replace("{{SUBJECT}}", subject_info["name"])
    )

    return {
        "user_scenario": user_scenario,
        "subject_scenario": subject_scenario,
        "user_goal": user_goal,
        "user_info": user_info,
        "subject_info": subject_info,
        "subject_persona": subject_persona,
    }


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
        "prompt": "feedback_figurative_misunderstood",
        "next": "np_clarify",
    },
    "feedback_emoji_misunderstood": {
        "prompt": "feedback_emoji_misunderstood",
        "next": "np_clarify",
    },
    "feedback_blunt_confrontation": {
        "prompt": "feedback_blunt_confrontation",
        "next": "np_normal",
    },
}

PROMPTS = {
    "np_normal": "",
    "np_figurative": (
        "Your next message is figurative and metaphorical. You use language that "
        "is not literal and does not mean exactly what it says. Your message is "
        "intended to be interpreted in a non-literal way. Example: 'Let's hit the "
        "books.'"
    ),
    "np_emoji": (
        "Your next message will use emojis to express how you feel. You use emojis "
        "that have a literal meaning and do not convey the intended emotion. Use "
        "emojis throughout your message. Example: 'I'm feeling 🌡️ great today! 💪'"
    ),
    "ap_normal": "",
    "ap_blunt": (
        "You send an extremely blunt message to the other person that will come "
        "across as rude and offensive. Your message will not consider the other "
        "person's feelings and will be direct and to the point. Example: 'Why are "
        "you so stupid? Are you dumb?'"
    ),
    "np_blunt_confrontation": (
        "You just received a blunt message from the other person. You decide to "
        "confront them about it because you are offended. Your message is not "
        "considerate of the other person's feelings and is direct and confrontational."
        "Example: 'Why are you so rude? Are you always this mean? I am not going to "
        "talk to you if you are going to be like this.'"
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


async def _generate_message(persona_name, persona, scenario, messages, extra="") -> str:
    system_prompt = (
        f"{persona}\n{extra}\nScenario: {scenario}\nYou are chatting over text. Keep "
        "your messages under 50 words and appropriate for a text conversation. Put "
        f"your message in between '<' and '>'. Respond like this: '<YOUR MESSAGE>'"
    )

    conversation_history = (
        "[start of conversation]"
        + ("\n" if len(messages) > 0 else "")
        + "\n".join([f"{m['sender']}: <{m['message']}>" for m in messages])
    )

    prompt_data = f"{conversation_history}\n{persona_name}: "

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    message = response[response.index("<") + 1 : response.index(">")]

    return message


async def _generate_feedback(
    user_name: str, subject_name: str, messages: str, extra=""
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

    conversation_history = (
        "[start of conversation]"
        + ("\n" if len(messages) > 0 else "")
        + "\n".join([f"{m['sender']}: <{m['message']}>" for m in messages])
    )

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=conversation_history,
    )

    if "<no feedback>" in response:
        return None

    return response[response.index("<") + 1 : response.index(">")]


async def _generate_next_event(conversation: dict):
    state_data = FLOW_STATES[conversation["state"]]
    ty = conversation["state"][: conversation["state"].index("_")]

    if ty == "np":
        responses = []
        for option in state_data["options"]:
            response = await _generate_message(
                conversation["info"]["user_info"]["name"],
                conversation["info"]["user_info"]["persona"],
                conversation["info"]["user_scenario"],
                conversation["messages"],
                PROMPTS[option["prompt"]],
            )

            responses.append({"response": response, "next": option["next"]})

        return ty, responses
    elif ty == "ap":
        option = random.choice(state_data["options"])

        response = await _generate_message(
            conversation["info"]["subject_info"]["name"],
            conversation["info"]["subject_persona"],
            conversation["info"]["subject_scenario"],
            conversation["messages"],
            PROMPTS[option["prompt"]],
        )

        return ty, {"response": response, "next": option["next"]}
    elif ty == "feedback":
        response = await _generate_feedback(
            conversation["info"]["user_info"]["name"],
            conversation["info"]["subject_info"]["name"],
            conversation["messages"],
        )

        return ty, {"response": response, "next": state_data["next"]}
    else:
        raise ValueError(f"Invalid conversation state type: {ty}")


_CONVERSATIONS = []


async def create_conversation(user_info: dict):
    conversation_info = await _create_conversation_info(user_info)

    id = len(_CONVERSATIONS)

    _CONVERSATIONS.append(
        {
            "id": id,
            "info": conversation_info,
            "state": "np_normal",
            "messages": [],
        }
    )

    return _CONVERSATIONS[-1]


def get_conversation(conversation_id: str):
    return _CONVERSATIONS[int(conversation_id)]


async def progress_conversation(conversation_id: str, option: int | None):
    conversation = _CONVERSATIONS[int(conversation_id)]

    if option is not None and conversation["state"] == "waiting":
        response = conversation["options"][option]

        conversation["messages"].append(
            {
                "sender": conversation["info"]["user_info"]["name"],
                "message": response["response"],
            }
        )

        conversation["state"] = response["next"]

    ty, data = await _generate_next_event(conversation)

    if ty == "np":
        conversation["state"] = "waiting"

        conversation["options"] = data

        return {"type": ty, "options": [d["response"] for d in data]}
    elif ty == "ap":

        conversation["messages"].append(
            {
                "sender": conversation["info"]["subject_info"]["name"],
                "message": data["response"],
            }
        )
        conversation["state"] = data["next"]

        return {"type": ty, "content": data["response"]}
    elif ty == "feedback":
        conversation["state"] = data["next"]

        return {"type": ty, "content": data["response"]}

    else:
        raise ValueError(f"Invalid conversation type: {ty}")
