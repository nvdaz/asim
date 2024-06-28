import random
from dataclasses import dataclass
from enum import Enum
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


@dataclass
class ConversationInfo:
    scenario: ConversationScenario
    user: Persona
    subject: Persona


async def _create_conversation_info(user: Persona):
    scenario = await _generate_conversation_scenario(user, "Alex")
    subject_persona = await _generate_subject_persona(scenario.subject_scenario)

    return ConversationInfo(scenario=scenario, user=user, subject=subject_persona)


class NpFlowStateId(Enum):
    NORMAL = "normal"
    FIGURATIVE_HEAVY = "figurative_heavy"
    FIGURATIVE_LIGHT = "figurative_light"


class NpFlowStateRef(BaseModel):
    type: Literal["np"] = "np"
    id: NpFlowStateId


class ApFlowStateId(Enum):
    NORMAL = "normal"
    FIGURATIVE_MISUNDERSTOOD = "figurative_misunderstood"


class ApFlowStateRef(BaseModel):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId


class FeedbackFlowStateRef(BaseModel):
    type: Literal["feedback"] = "feedback"


class FlowStateRef(RootModel):
    root: Annotated[
        Union[NpFlowStateRef, ApFlowStateRef, FeedbackFlowStateRef],
        Field(discriminator="type"),
    ]


class FlowOption(BaseModel):
    prompt: str
    next: FlowStateRef


class NpFlowState(BaseModel):
    type: Literal["np"] = "np"
    id: NpFlowStateId
    options: list[FlowOption]


class ApFlowState(BaseModel):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId
    options: list[FlowOption]


class FeedbackFlowState(BaseModel):
    type: Literal["feedback"] = "feedback"


class FlowState(RootModel):
    root: Annotated[
        Union[NpFlowState, ApFlowState, FeedbackFlowState],
        Field(discriminator="type"),
    ]


FLOW_STATES = [
    FlowState(
        root=NpFlowState(
            id=NpFlowStateId.NORMAL,
            options=[
                FlowOption(
                    prompt=(
                        "Do not use any figurative language in your next message. Keep "
                        "your message straightforward and literal."
                    ),
                    next=FlowStateRef(root=ApFlowStateRef(id=ApFlowStateId.NORMAL)),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is figurative and metaphorical. You use "
                        "language that is not literal and does not mean exactly what "
                        "it says. Your message is intended to be interpreted in a "
                        "non-literal way. Example: 'Let's hit the books.'"
                    ),
                    next=FlowStateRef(
                        root=ApFlowStateRef(id=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD)
                    ),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is mostly literal, but includes a hint of "
                        "figurative language. The message is mostly straightforward, "
                        "but there is also a figurative element that could be "
                        "misinterpreted. Example: 'It's so hot, it feels like 1000 "
                        "degrees outside.'"
                    ),
                    next=FlowStateRef(
                        root=ApFlowStateRef(id=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD)
                    ),
                ),
            ],
        )
    ),
    FlowState(
        root=ApFlowState(
            id=ApFlowStateId.NORMAL,
            options=[
                FlowOption(
                    prompt=(
                        "Respond to the message in a normal, direct manner. Your "
                        "response correctly interprets the message and continues the "
                        "conversation. "
                    ),
                    next=FlowStateRef(root=NpFlowStateRef(id=NpFlowStateId.NORMAL)),
                )
            ],
        )
    ),
    FlowState(
        root=ApFlowState(
            id=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD,
            options=[
                FlowOption(
                    prompt=(
                        "You are responding to a figurative and metaphorical message. "
                        "You misunderstand the figurative language and your next "
                        "message will confidently interpret the message literally, "
                        "missing the intended meaning. The response should be literal "
                        "and direct, only addressing the figurative meaning and "
                        "ignoring the intended message. Example: NP: 'Let's hit the "
                        "books' -> AP: 'Why would you want to hit books? That would "
                        "damage them.'"
                    ),
                    next=FlowStateRef(root=FeedbackFlowStateRef()),
                )
            ],
        )
    ),
    FlowState(
        root=FeedbackFlowState(),
    ),
]


def get_flow_state(ref: FlowStateRef) -> FlowState:
    if isinstance(ref.root, FeedbackFlowStateRef):
        return FlowState(root=FeedbackFlowState())
    for state in FLOW_STATES:
        if state.root.id == ref.root.id:
            return state


class Message(BaseModel):
    sender: str
    message: str


class Messages(RootModel):
    root: list[Message]

    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return Messages(root=self.root[index])
        else:
            return self.root[index]


async def _generate_message(
    persona: Persona, scenario: str, messages: Messages, extra=""
) -> str:
    def validate_sender(v):
        if v != persona.name:
            raise ValueError(f"Sender must be {persona.name}")
        return v

    class MessageResponse(BaseModel):
        message: str
        sender: Annotated[str, AfterValidator(validate_sender)]

    instr = f"Instructions: {extra}" if extra else ""

    system_prompt = (
        f"{persona.description}\nScenario: {scenario}\n{instr}\nYou are chatting over "
        "text. Keep your messages under 50 words and appropriate for a text "
        "conversation. Keep the conversation going. Return a JSON object with the key "
        "'message' and your message as the value and the key 'sender' with "
        f"'{persona.name}' as the value. Respond ONLY with your next message. Do not "
        "include the previous messages in your response."
    )

    prompt_data = messages.model_dump_json()

    response = await llm.generate_strict(
        schema=MessageResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message


class MessageOption(BaseModel):
    response: str
    next: FlowStateRef


class ConversationWaiting(BaseModel):
    waiting: Literal[True] = True
    options: list[MessageOption]


class ConversationNormal(BaseModel):
    waiting: Literal[False] = False
    state: FlowStateRef


class ConversationData(BaseModel):
    id: str
    info: ConversationInfo
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    messages: Messages
    last_feedback_received: int


class FeedbackWithoutMisunderstanding(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=300)]
    confused: Literal[False] = False


class FeedbackWithMisunderstanding(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=300)]
    confused: Literal[True] = True
    follow_up: str


class Feedback(RootModel):
    root: Annotated[
        Union[FeedbackWithoutMisunderstanding, FeedbackWithMisunderstanding],
        Field(discriminator="confused"),
    ]


class FeedbackAnalysisUnclear(BaseModel):
    clear: Literal[False] = False
    misunderstanding: bool


class FeedbackAnalysisClear(BaseModel):
    clear: Literal[True] = True


class FeedbackAnalysis(RootModel):
    root: Annotated[
        Union[FeedbackAnalysisUnclear, FeedbackAnalysisClear],
        Field(discriminator="clear"),
    ]


async def _analyze_messages_for_misunderstanding(conversation: ConversationData):
    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to identify whether the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        "autistic individual, contains any potential misunderstandings. The "
        "conversation is happening over text. Analyze the messages and determine if "
        f"there are any instances where {user.name} could have used clearer language "
        "or provided more context to avoid confusion. Then determine whether these "
        f"instances led to a misunderstanding by {subject.name}. Begin with analysis "
        "in a <analysis> tag, then provide a JSON object with the key 'clear' "
        "containing a boolean value indicating whether there were any unclear messages "
        "in the conversation. If there were unclear messages, also include the key "
        "'misunderstanding' with a boolean value indicating whether the unclear "
        "messages led to a misunderstanding."
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    response = await llm.generate_strict(
        schema=FeedbackAnalysis,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response


async def _generate_feedback_clear(conversation: ConversationData):
    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. {user.name} has been considerate and clear in their "
        "communication. The conversation is happening over text. Point out the areas "
        f"where {user.name} excelled in their communication, keeping in mind that "
        f"{subject.name} is an autistic individual, so they may find certain types of "
        "communication more challenging than others. Provide positive reinforcement "
        "and encouragement for clear communication. Respond with a JSON object with "
        "the key 'title' containing the title (less than 50 characters) of your "
        "feedback and the key 'body' containing the feedback (less than 100 words)."
        "Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I'm feeling great today!"),
                Message(
                    sender="Chris", message="That's awesome! I'm glad to hear that!"
                ),
            ]
        ).model_dump_json()
        + "\n"
        + FeedbackWithoutMisunderstanding(
            title="Clear Communication",
            body=(
                "Your message was clear and considerate. You successfully "
                "communicated your feelings without relying on unclear language. "
                "Keep up the good work!"
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate_strict(
        schema=FeedbackWithoutMisunderstanding,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _generate_feedback_unclear(conversation: ConversationData):
    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. The latest message from {user.name} was unclear and "
        f"could have been misinterpreted by {subject.name}. The conversation is "
        f"happening over text. Describe how {user.name} could have been more clear "
        "in their communication to avoid confusion. Respond with a JSON object with "
        "the key 'title' containing the title (less than 50 characters) of your "
        "feedback and the key 'body' containing the feedback (less than 100 "
        "words)."
        "Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I feel like a million bucks today!"),
                Message(
                    sender="Chris",
                    message="You must have had a great day! That's awesome!",
                ),
            ]
        ).model_dump_json()
        + "\n"
        + FeedbackWithoutMisunderstanding(
            title="Avoid Figurative Language",
            body=(
                "Your message relied on figurative language, which can be "
                "misinterpreted by autistic individuals. In this case, your message "
                "could be misinterpreted as a literal statement. Consider using more "
                "direct language to avoid confusion."
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    return await llm.generate_strict(
        schema=FeedbackWithoutMisunderstanding,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def _generate_feedback_misunderstanding(conversation: ConversationData):

    class FeedbackMisunderstandingResponse(BaseModel):
        title: Annotated[str, StringConstraints(max_length=50)]
        body: Annotated[str, StringConstraints(max_length=300)]
        instructions: str

    user, subject = conversation.info.user, conversation.info.subject
    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between {user.name} and {subject.name}, who is an "
        f"autistic individual. The latest message from {user.name} was unclear and "
        f"was misinterpreted by {subject.name}. The conversation is happening over "
        f"text. Describe how {user.name} could have been more clear in their "
        "communication to avoid confusion. Respond with a JSON object with the key "
        "'title' containing the title (less than 50 characters) of your feedback, "
        "the key 'body' containing the feedback (less than 100 words), and the "
        f"key 'instructions' explaining what {user.name} could do to clarify the "
        f"situation. The 'instructions' should not be a message, but a string that "
        f"outlines what {user.name} should do to clarify the misunderstanding."
        "Examples: \n"
        + Messages(
            root=[
                Message(sender="Ben", message="I feel like a million bucks today!"),
                Message(
                    sender="Chris",
                    message="Did you just win the lottery? That's great!",
                ),
            ]
        ).model_dump_json()
        + "\n"
        + FeedbackMisunderstandingResponse(
            title="Avoid Figurative Language",
            body=(
                "Your message relied on figurative language, which can be "
                "misinterpreted by autistic individuals. Consider using more "
                "direct language to avoid confusion."
            ),
            instructions=(
                "Your next message should clarify that you're not actually a "
                "millionaire, but you're feeling really good today. Be direct "
                "and avoid figurative language."
            ),
        ).model_dump_json()
    )

    prompt_data = conversation.messages[
        conversation.last_feedback_received :
    ].model_dump_json()

    feedback_base = await llm.generate_strict(
        schema=FeedbackMisunderstandingResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    follow_up = await _generate_message(
        user,
        conversation.info.scenario.user_scenario,
        conversation.messages,
        extra=feedback_base.instructions,
    )

    return FeedbackWithMisunderstanding(
        title=feedback_base.title,
        body=feedback_base.body,
        follow_up=follow_up,
    )


async def _generate_feedback(conversation: ConversationData) -> Feedback:
    analysis = await _analyze_messages_for_misunderstanding(conversation)

    if isinstance(analysis.root, FeedbackAnalysisClear):
        return Feedback(root=await _generate_feedback_clear(conversation))
    elif not analysis.root.misunderstanding:
        return Feedback(root=await _generate_feedback_unclear(conversation))
    else:
        return Feedback(root=await _generate_feedback_misunderstanding(conversation))


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


async def create_conversation(user: Persona) -> Conversation:
    conversation_info = await _create_conversation_info(user)

    id = len(_CONVERSATIONS)

    _CONVERSATIONS.append(
        ConversationData(
            id=str(id),
            info=conversation_info,
            state=ConversationNormal(
                state=FlowStateRef(root=NpFlowStateRef(id=NpFlowStateId.NORMAL))
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

    state_data = get_flow_state(conversation.state.state).root

    if isinstance(state_data, NpFlowState):
        options: list[MessageOption] = []
        for opt in state_data.options:
            response = await _generate_message(
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

        response = await _generate_message(
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
        response = await _generate_feedback(conversation)
        conversation.last_feedback_received = len(conversation.messages.root)

        if isinstance(response.root, FeedbackWithMisunderstanding):
            conversation.messages.root.append(
                Message(
                    sender=conversation.info.user.name,
                    message=response.root.follow_up,
                )
            )
            conversation.state = ConversationNormal(
                state=FlowStateRef(root=ApFlowStateRef(id=ApFlowStateId.NORMAL))
            )
        else:
            conversation.state = ConversationNormal(
                state=FlowStateRef(root=NpFlowStateRef(id=NpFlowStateId.NORMAL))
            )

        return FeedbackEvent(content=response)
