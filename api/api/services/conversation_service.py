import json
import random
from dataclasses import dataclass
from typing import Literal, Union

from pydantic import AfterValidator, BaseModel, Field, RootModel, StringConstraints
from typing_extensions import Annotated

from api.schemas.persona import BasePersona, Persona

from . import llm_service as llm


class ConversationScenario(BaseModel):
    user_scenario: str
    subject_scenario: str
    user_goal: str


async def _generate_conversation_scenario(
    user: Persona, subject_name: str
) -> ConversationScenario:
    system_prompt = (
        "As a scenario generator, your task is to generate an everyday conversational "
        f"scenario that could happen over a text messaging app based on {user.name}'s "
        "profile. The scenario should be a generic situation that could happen between "
        f"{user.name} and an unfamiliar person {subject_name} over text messaging. The "
        "scenario should be realistic and relatable. Respond with a JSON object. The "
        f"'user_scenario' key should be a string describing {user.name}'s perspective "
        "in the scenario (begin with 'You...'), the 'subject_scenario' key should be a "
        "string describing the subject's perspective (begin with 'You...'), and the "
        f"'user_goal' key should be a string describing {user.name}'s objective in the "
        "scenario (begin with a verb, e.g., 'Convince', 'Explain', 'Find out')."
    )

    sampled_interests = random.sample(user.interests, min(6, len(user.interests)))

    prompt_data = json.dumps({**user.model_dump(), "interests": sampled_interests})

    scenario = await llm.generate_strict(
        schema=ConversationScenario,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return scenario


async def _generate_subject_base(scenario, name):
    def validate_name(v):
        if v != name:
            raise ValueError(f"Name must be {name}")
        return v

    class SubjectBasePersona(BasePersona):
        name: Annotated[str, AfterValidator(validate_name)]

    system_prompt = (
        f"Generate a persona for {name}, an autistic individual in the provided "
        "scenario (referred to as 'you'). Fill in the persona details based on the "
        "information provided in the scenario. Generate any missing information to "
        "create a realistic and relatable character. Respond with a JSON object "
        "containing the keys 'name' (string), 'age' (age range), 'occupation', and "
        "'interests' (list of strings)."
    )

    response = await llm.generate_strict(
        schema=SubjectBasePersona,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    return response


async def _generate_subject_persona_from_base(subject: BasePersona):
    class PersonaDescriptionResponse(BaseModel):
        persona: str

    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "The persona is an autistic individual who struggles to communicate "
        "effectively with others. The persona should exhibit the vocal styles "
        "of an autistic person and should be ignorant of the needs of neurotypical "
        "individuals due to a lack of experience with them. The persona should be a "
        "realistic and relatable character who is messaging over text with another "
        "person. Respond with a JSON object containing the key 'persona' and the "
        "system prompt as the value. The prompt should start with 'You are "
        f"{subject.name}...'."
    )

    prompt_data = json.dumps(subject.model_dump())

    response = await llm.generate_strict(
        schema=PersonaDescriptionResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return Persona(**subject.model_dump(), description=response.persona)


async def _generate_subject_persona(scenario):
    subject_name = "Alex"
    subject_info = await _generate_subject_base(scenario, subject_name)

    subject_persona = await _generate_subject_persona_from_base(subject_info)

    return subject_persona


@dataclass
class ConversationInfo:
    scenario: ConversationScenario
    user: Persona
    subject: Persona


async def _create_conversation_info(user: Persona):
    scenario = await _generate_conversation_scenario(user, "Alex")
    subject_persona = await _generate_subject_persona(scenario.subject_scenario)

    return ConversationInfo(scenario=scenario, user=user, subject=subject_persona)


FLOW_STATES = {
    "np_normal": {
        "options": [
            {"prompt": "np_normal", "next": "ap_normal"},
            {"prompt": "np_figurative", "next": "ap_figurative_misunderstood"},
            {"prompt": "np_figurative_2", "next": "ap_figurative_misunderstood"},
        ]
    },
    "ap_normal": {
        "options": [
            {"prompt": "ap_normal", "next": "np_normal"},
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
    "np_clarify": {
        "options": [
            {"prompt": "np_clarify", "next": "ap_normal"},
        ]
    },
    "feedback_figurative_misunderstood": {
        "prompt": "feedback_figurative_misunderstood",
        "next": "ap_normal",
    },
    "feedback_figurative_understood": {
        "prompt": "feedback_figurative_understood",
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
    "np_figurative_2": (
        "Your next message is mostly literal, but includes a hint of figurative "
        "language. The message is mostly straightforward, but there is also a "
        "figurative element that could be misinterpreted. Example: 'It's so hot, "
        "It feels like 1000 degrees outside.'"
    ),
    "ap_normal": "",
    "ap_figurative_misunderstood": (
        "You are responding to a figurative and metaphorical message. You "
        "misunderstand the figurative language and your next message will"
        "confidently interpret the message literally, missing the intended "
        "meaning. The response should be literal and direct, only addressing "
        "the figurative meaning and ignoring the intended message."
        "Example: NP: 'Let's hit the books' -> AP: 'Why would you want to "
        "hit books? That would damage them.'"
    ),
    "feedback_figurative_misunderstood": (
        "The autistic individual just misunderstood a figurative message. The user "
        "could have been more considerate and provided more context to help the "
        "autistic individual understand the intended meaning of the message."
    ),
    "feedback_figurative_understood": (
        "The autistic individual successfully interpreted a figurative message. "
        "The user could have been more considerate and provided more context and "
        "clarity in their communication to avoid any potential misunderstandings."
    ),
}


async def _generate_message(persona: Persona, scenario: str, messages, extra="") -> str:
    def validate_sender(v):
        if v != persona.name:
            raise ValueError(f"Sender must be {persona.name}")
        return v

    class MessageResponse(BaseModel):
        message: str
        sender: Annotated[str, AfterValidator(validate_sender)]

    system_prompt = (
        f"{persona}\n{extra}\nScenario: {scenario}\nYou are chatting over text. Keep "
        "your messages under 50 words and appropriate for a text conversation. Return "
        "a JSON object with the key 'message' and your message as the value and the "
        f"key 'sender' with '{persona.name}' as the value. Respond ONLY with your next "
        "message. Do not include the previous messages in your response."
    )

    prompt_data = json.dumps(
        [{"sender": sender, "message": message} for sender, message in messages]
    )

    response = await llm.generate_strict(
        schema=MessageResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message


class FeedbackWithoutMisunderstanding(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: str
    confused: Literal[False]


class FeedbackWithMisunderstanding(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: str
    confused: Literal[True]
    follow_up: str


class Feedback(RootModel):
    root: Annotated[
        Union[FeedbackWithoutMisunderstanding, FeedbackWithMisunderstanding],
        Field(discriminator="confused"),
    ]


async def _generate_feedback(
    user_name: str, subject_name: str, messages: list[any], extra=""
):
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user_name} and {subject_name}, who is "
        "an autistic individual. The conversation is happening over text. Point out "
        f"any areas where {user_name} could have been more considerate. Respond with "
        "a JSON object with the key 'title' containing the title (less than 50 "
        "characters) of your feedback and the key 'body' containing the feedback. "
        f"The key 'confused' should be set to true if {subject_name} misunderstood "
        "the figurative language in the latest message and is confused by it. If "
        f"there is no misunderstanding, set it to false. If {subject_name} was "
        "confused by the message and there was a potential for a serious "
        "misunderstanding, suggest a follow-up message that {user_name} could send to "
        f"clarify the situation in the 'follow_up' key.\n{extra}\nExamples:"
        + json.dumps(
            [
                {"sender": "Chris", "message": "How are you today?"},
                {"sender": "Ben", "message": "I feel great! Like a million bucks!"},
                {
                    "sender": "Chris",
                    "message": "That's awesome! Did something good happen?",
                },
            ]
        )
        + "\n"
        + json.dumps(
            {
                "title": "Be cautious with figurative language",
                "body": (
                    "Your message succesfully conveyed your feelings, but be cautious "
                    "with figurative language. Chris could have misunderstood your "
                    "message if he wasn't familiar with the idiom. Try to be more "
                    "direct in your communication to avoid confusion."
                ),
                "confused": False,
                "follow_up": None,
            }
        )
        + "\n\n"
        + json.dumps(
            [
                {"sender": "Kyle", "message": "I feel like a million bucks today!"},
                {
                    "sender": "Alex",
                    "message": "Did you just win the lottery? That's great!",
                },
            ]
        )
        + "\n"
        + json.dumps(
            {
                "title": "Avoid figurative language",
                "confused": True,
                "body": (
                    "Your message relied on figurative language, which can be "
                    "misinterpreted by autistic individuals. Consider using more "
                    "direct language to avoid confusion. Try sending the following "
                    "message to clarify:"
                ),
                "follow_up": (
                    "I'm not actually a millionaire, but I'm feeling really "
                    "good today!"
                ),
            }
        )
    )

    prompt_data = json.dumps(
        [{"sender": sender, "message": message} for sender, message in messages]
    )

    response = await llm.generate_strict(
        schema=Feedback,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response


class MessageOption(BaseModel):
    response: str
    next: str


class Message(BaseModel):
    sender: str
    message: str


class ConversationWaiting(BaseModel):
    waiting: Literal[True] = True
    options: list[MessageOption]


class ConversationNormal(BaseModel):
    waiting: Literal[False] = False
    state: str


class ConversationData(BaseModel):
    id: str
    info: ConversationInfo
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    messages: list[Message]


class NpMessageEvent(BaseModel):
    type: Literal["np"] = "np"
    options: list[str]


class ApMessageEvent(BaseModel):
    type: Literal["ap"] = "ap"
    content: str


class FeedbackEvent(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback


class ConversationEvent(RootModel):
    root: Annotated[
        Union[NpMessageEvent, ApMessageEvent, FeedbackEvent],
        Field(discriminator="type"),
    ]


_CONVERSATIONS: list[ConversationData] = []


@dataclass
class Conversation:
    id: str
    scenario: ConversationScenario
    subject_name: str
    messages: list[Message]

    @staticmethod
    def from_data(data: ConversationData):
        return Conversation(
            id=data.id,
            scenario=data.info.scenario,
            subject_name=data.info.subject.name,
            messages=data.messages,
        )


async def create_conversation(user_info: dict) -> ConversationData:
    conversation_info = await _create_conversation_info(user_info)

    id = len(_CONVERSATIONS)

    _CONVERSATIONS.append(
        ConversationData(
            id=str(id),
            info=conversation_info,
            state=ConversationNormal(state="np_normal"),
            messages=[],
        )
    )

    return Conversation.from_data(_CONVERSATIONS[-1])


def get_conversation(conversation_id: str) -> ConversationData:
    return Conversation.from_data(_CONVERSATIONS[int(conversation_id)])


async def progress_conversation(
    conversation_id: str, option: int | None
) -> ConversationEvent:
    conversation = _CONVERSATIONS[int(conversation_id)]

    if isinstance(conversation.state, ConversationWaiting):
        assert option is not None
        response = conversation.state.options[option]

        conversation.messages.append(
            Message(sender=conversation.info.user.name, message=response.response)
        )

        conversation.state = ConversationNormal(state=response.next)

    assert isinstance(conversation.state, ConversationNormal)

    state_str = conversation.state.state
    state_data = FLOW_STATES[state_str]
    ty = state_str[: state_str.index("_")]

    if ty == "np":
        options = []
        for option in state_data["options"]:
            response = await _generate_message(
                conversation.info.user,
                conversation.info.scenario.user_scenario,
                conversation.messages,
                PROMPTS[option["prompt"]],
            )

            options.append(MessageOption(response=response, next=option["next"]))

        random.shuffle(options)
        conversation.state = ConversationWaiting(options=options)

        return NpMessageEvent(options=[o.response for o in options])
    elif ty == "ap":
        option = random.choice(state_data["options"])

        response = await _generate_message(
            conversation.info.subject,
            conversation.info.scenario.subject_scenario,
            conversation.messages,
            PROMPTS[option["prompt"]],
        )

        conversation.messages.append(
            Message(sender=conversation.info.subject.name, message=response)
        )
        conversation.state = ConversationNormal(state=option["next"])

        return ApMessageEvent(content=response)
    elif ty == "feedback":
        response = await _generate_feedback(
            conversation.info.user.name,
            conversation.info.subject.name,
            conversation.messages,
        )

        if isinstance(response.root, FeedbackWithMisunderstanding):
            conversation.messages.append(
                Message(
                    sender=conversation.info.user.name,
                    message=response.root.follow_up,
                )
            )

        conversation.state = ConversationNormal(state=state_data["next"])

        return FeedbackEvent(content=response)
    else:
        raise ValueError(f"Invalid conversation state type: {ty}")
