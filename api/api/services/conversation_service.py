import random
from dataclasses import dataclass
from typing import Literal, Union

from pydantic import AfterValidator, BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.schemas.conversation import (
    ConversationData,
    ConversationInfo,
    ConversationNormal,
    ConversationScenario,
    ConversationWaiting,
    Message,
    MessageOption,
)
from api.schemas.persona import BasePersona, Persona

from . import llm_service as llm
from .conversation_generation import generate_message
from .feedback_generation import Feedback, generate_feedback
from .flow_state.base import ApFlowState, FeedbackFlowState, NpFlowState
from .flow_state.blunt_language import BLUNT_LANGUAGE_LEVEL
from .flow_state.figurative_language import FIGURATIVE_LANGUAGE_LEVEL

LEVELS = [FIGURATIVE_LANGUAGE_LEVEL, BLUNT_LANGUAGE_LEVEL]


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
        "string describing the subject's perspective (begin with 'You...'), the "
        f"'user_goal' key should be a string describing {user.name}'s objective in the "
        "scenario (begin with a verb, e.g., 'Convince', 'Explain', 'Find out'), and "
        "the 'is_user_initiated' key should be a boolean that is true if the "
        f"conversation is initiated by {user.name} and false if initiated by "
        f"{subject_name}. Do not generate scenarios that involve significant external "
        "elements, such as finding a bug in a software program (it is not possible to "
        "send the code). Examples:\n"
        "\n".join(
            [
                ex.model_dump_json()
                for ex in [
                    ConversationScenario(
                        user_scenario=(
                            "You are texting with an unfamiliar person named Phil on a "
                            "messaging app. Phil received your number from a mutual "
                            "friend who mentioned that you both love theoretical "
                            "physics. You try to get to know Phil better and discuss "
                            "your favorite physicists, theories, and upcoming physics "
                            "events."
                        ),
                        subject_scenario=(
                            "You are texting with Ben, who you reached out to after "
                            "receiving their number from a mutual friend. Ben is "
                            "interested in discussing theoretical physics, just like "
                            "you. You want to get to know Ben better and discuss your "
                            "favorite physicists, theories, and upcoming physics "
                            "events."
                        ),
                        user_goal=(
                            "Discuss theoretical physics with Phil and learn more "
                            "about their favorite physicists and theories."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "You just started a new job at a pharmaceutical company "
                            "and met a colleague named Jake. You asked Jake for his "
                            "number to discuss work and get to know him better. You "
                            "start texting with Jake to learn more about his role in "
                            "the company, his experience, and his interests outside "
                            "of work."
                        ),
                        subject_scenario=(
                            "You gave your number to a new colleague named Christina, "
                            "who recently joined your team at the pharmaceutical "
                            "company you work for. Christina is interested in "
                            "discussing work and getting to know you better."
                        ),
                        user_goal=(
                            "Learn more about Jake's role in the company and his "
                            "interests to build a friendly working relationship."
                        ),
                        is_user_initiated=True,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "You met a fellow student named Avery in photography class "
                            "and exchanged numbers. You start texting with Avery to "
                            "discuss photography. You ask Avery about their favorite "
                            "subjects to photograph and any tips."
                        ),
                        subject_scenario=(
                            "You exchanged numbers with a fellow student named Joe in "
                            "photography class. Joe is interested in discussing "
                            "photography with you."
                        ),
                        user_goal=(
                            "Discuss photography with Avery and learn more about their "
                            "favorite subjects and tips."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "You are new to the neighborhood and are texting with a "
                            "neighbor named Jordan. You want to get to know "
                            "Jordan better and learn more about the community. "
                            "You ask Jordan about local events, good places to eat, "
                            "and any tips for newcomers."
                        ),
                        subject_scenario=(
                            "You are texting with a new neighbor named David. "
                            "David recently moved into the neighborhood and is "
                            "interested in getting to know you better."
                        ),
                        user_goal=(
                            "Learn more about the community and build a friendly "
                            "relationship with Jordan."
                        ),
                        is_user_initiated=True,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "You are taking an online physics course and are texting "
                            "with a classmate named Morgan. You want to get to know "
                            "Morgan better and possibly collaborate on projects. "
                            "You ask Morgan about their background, why they took "
                            "the course, and their career goals."
                        ),
                        subject_scenario=(
                            "You are texting with a classmate named Belle. "
                            "Belle recently joined the course and asked for your "
                            "number to discuss the course and potential projects."
                            "You are interested in collaborating with Belle."
                        ),
                        user_goal=(
                            "Learn more about Morgan's background and explore "
                            "possible collaboration on projects."
                        ),
                        is_user_initiated=True,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "You are attending a math conference and are texting with "
                            "a fellow attendee named Riley. You are both interested "
                            "in topological algebra and category theory. You want to "
                            "get to know Riley better and learn more about their "
                            "field of work. You ask Riley about their research, "
                            "favorite mathematicians, and future projects."
                        ),
                        subject_scenario=(
                            "You are texting with a fellow conference attendee named "
                            "Eden. You gave Eden your number to discuss topological "
                            "algebra and category theory after meeting at the "
                            "conference and learning about their interests."
                        ),
                        user_goal=(
                            "Discuss topological algebra and category theory with "
                            "Riley and learn more about their research and interests "
                            "to build a professional connection."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_scenario=(
                            "At a social event, you met a new acquaintance named Finn, "
                            "who is an avid hiker, like you. You are texting with Finn "
                            "to discuss hiking trails, gear, and experiences. You ask "
                            "Finn about their favorite trails, future hiking plans, "
                            "and any advice for beginners."
                        ),
                        subject_scenario=(
                            "You exchanged numbers with a new acquaintance named Sam "
                            "at a social event. Sam is interested in discussing hiking "
                            "with you."
                        ),
                        user_goal=(
                            "Discuss hiking with Finn and learn more about their "
                            "experiences and advice."
                        ),
                        is_user_initiated=True,
                    ),
                ]
            ]
        )
    )

    sampled_interests = random.sample(user.interests, min(6, len(user.interests)))

    prompt_data = Persona(
        **user.model_dump(exclude="interests"), interests=sampled_interests
    ).model_dump_json()

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

    prompt_data = subject.model_dump_json()

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


async def _create_conversation_info(user: Persona):
    scenario = await _generate_conversation_scenario(user, "Alex")
    subject_persona = await _generate_subject_persona(scenario.subject_scenario)

    return ConversationInfo(
        scenario=scenario,
        user=user,
        subject=subject_persona,
    )


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
    level: int
    scenario: ConversationScenario
    subject_name: str
    messages: list[Message]

    @staticmethod
    def from_data(data: ConversationData):
        return Conversation(
            id=data.id,
            level=data.level,
            scenario=data.info.scenario,
            subject_name=data.info.subject.name,
            messages=data.messages,
        )


async def create_conversation(user: Persona, level: int) -> Conversation:
    conversation_info = await _create_conversation_info(user)

    id = len(_CONVERSATIONS)

    _CONVERSATIONS.append(
        ConversationData(
            id=str(id),
            level=level,
            info=conversation_info,
            state=ConversationNormal(
                state=(
                    LEVELS[level].initial_np_state
                    if conversation_info.scenario.is_user_initiated
                    else LEVELS[level].initial_ap_state
                )
            ),
            messages=[],
            last_feedback_received=0,
        )
    )

    return Conversation.from_data(_CONVERSATIONS[-1])


def get_conversation(conversation_id: str) -> Conversation:
    return Conversation.from_data(_CONVERSATIONS[int(conversation_id)])


async def progress_conversation(
    conversation_id: str, option: int | None
) -> ConversationEvent:
    conversation = _CONVERSATIONS[int(conversation_id)]

    if isinstance(conversation.state, ConversationWaiting):
        assert option is not None
        response = conversation.state.options[option]

        conversation.messages.root.append(
            Message(sender=conversation.info.user.name, message=response.response)
        )

        conversation.state = ConversationNormal(state=response.next)

    assert isinstance(conversation.state, ConversationNormal)

    state_data = (
        LEVELS[conversation.level].get_flow_state(conversation.state.state).root
    )

    if isinstance(state_data, NpFlowState):
        options: list[MessageOption] = []
        for opt in state_data.options:
            response = await generate_message(
                conversation.info.user,
                conversation.info.scenario.user_scenario,
                conversation.messages,
                opt.prompt,
            )

            options.append(MessageOption(response=response, next=opt.next))

        random.shuffle(options)
        conversation.state = ConversationWaiting(options=options)

        return NpMessageEvent(options=[o.response for o in options])
    elif isinstance(state_data, ApFlowState):
        opt = random.choice(state_data.options)

        response = await generate_message(
            conversation.info.subject,
            conversation.info.scenario.subject_scenario,
            conversation.messages,
            opt.prompt,
        )

        conversation.messages.root.append(
            Message(sender=conversation.info.subject.name, message=response)
        )
        conversation.state = ConversationNormal(state=opt.next)

        return ApMessageEvent(content=response)
    elif isinstance(state_data, FeedbackFlowState):
        response = await generate_feedback(conversation, state_data)
        conversation.last_feedback_received = len(conversation.messages.root)

        if response.follow_up is not None:
            conversation.messages.root.append(
                Message(
                    sender=conversation.info.user.name,
                    message=response.follow_up,
                )
            )
            conversation.state = ConversationNormal(
                state=state_data.next_needs_improvement
            )
        else:
            conversation.state = ConversationNormal(state=state_data.next_ok)

        return FeedbackEvent(content=response)
