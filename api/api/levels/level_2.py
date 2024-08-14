from typing import Literal

from api.schemas.conversation import AgentMessage, BaseFeedback, UserMessage

from .seed import LevelConversationScenarioSeed
from .states import (
    AgentNaturalStates,
    AgentState,
    BaseData,
    ChainStates,
    FeedbackState,
    RepeatStates,
    State,
    States,
    UnionStates,
    UserNaturalStates,
    UserOption,
    UserState,
)

_IntroStateId = Literal["agent_greet", "user_greet"]


class _IntroData(BaseData[_IntroStateId]): ...


class _IntroStates(States[_IntroData]):
    @property
    def data_type(self):
        return _IntroData

    def init(self) -> _IntroData:
        return _IntroData(state="agent_greet")

    def next(self, data) -> State:
        match data.state:
            case "agent_greet":
                return AgentState(
                    instructions="I will start the conversation and mention that I "
                    "have heard the other person has worked with a client that I "
                    "would like to discuss. I will ask if this is true.",
                    next=_IntroData(state="user_greet"),
                )
            case "user_greet":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will greet the person and confirm that I "
                            "have indeed worked with the client they mentioned. I will "
                            "tell them that I am happy to answer any questions they "
                            "have about the client.",
                            next=None,
                        )
                    ]
                )


_AskStateId = Literal["agent_ask"]


class _AskData(BaseData[_AskStateId]): ...


class _AskStates(States[_AskData]):
    @property
    def data_type(self):
        return _AskData

    def init(self) -> _AskData:
        return _AskData(state="agent_ask")

    def next(self, data) -> State:
        match data.state:
            case "agent_ask":
                return AgentState(
                    instructions="I will ask a question about the client. I will focus "
                    "on asking questions about the client that are general and open-"
                    "ended, avoiding trivial details like dates, times, or locations.",
                    next=None,
                )


_VagueAnswerStateId = Literal["user_answer", "agent_react_vague", "feedback_vague"]


class _VagueAnswerData(BaseData[_VagueAnswerStateId]): ...


class _VagueAnswerStates(States[_VagueAnswerData]):
    @property
    def data_type(self):
        return _VagueAnswerData

    def init(self) -> _VagueAnswerData:
        return _VagueAnswerData(state="user_answer")

    def next(self, data) -> State:
        match data.state:
            case "user_answer":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will provide a vague answer that can be "
                            "interpreted in multiple ways. I know the answer exactly "
                            "and everything is already finalized, but I will be vague "
                            "without mentioning it.",
                            examples=[
                                (
                                    (
                                        "Do you think there will be challenges "
                                        "with the proposal? If so, what expertise is "
                                        "needed to overcome them?"
                                    ),
                                    (
                                        "There are some parts that could be "
                                        "challenging, but if you have the right "
                                        "skills, you can overcome them."
                                    ),
                                ),
                                (
                                    ("Who will be speaking at the event?"),
                                    ("We have some great speakers lined up."),
                                ),
                                (
                                    (
                                        "What are the main topics that will be "
                                        "covered at the conference?"
                                    ),
                                    (
                                        "We will be discussing a variety of "
                                        "relevant subjects. There will be something "
                                        "for everyone."
                                    ),
                                ),
                            ],
                            next=_VagueAnswerData(state="agent_react_vague"),
                        ),
                    ]
                )
            case "agent_react_vague":
                return AgentState(
                    instructions="I will react to the vague answer by expressing "
                    "confusion and frustration. I will fumble with my words and "
                    "describe how the vague answer is making it difficult for me to "
                    "understand the response.",
                    examples=[
                        # TODO: ...
                    ],
                    next=_VagueAnswerData(state="feedback_vague"),
                )
            case "feedback_vague":
                return FeedbackState(
                    prompt=(
                        "The latest answer needs improvement as it is vague or "
                        "unclear. Vague responses can be frustrating for others, "
                        "making it difficult for them to understand and follow up. "
                        "Provide feedback on how the answer could have been "
                        "clearer and more specific to help others understand the "
                        "response better. Explain why the answer was vague."
                    ),
                    instructions="I will clarify what I meant with the vague answer I "
                    "previously provided.",
                    examples=[
                        (
                            [
                                AgentMessage(
                                    message="Do you think there will be challenges "
                                    "with the proposal? If so, what expertise is "
                                    "needed to overcome them?"
                                ),
                                UserMessage(
                                    message="There are some parts that could be "
                                    "challenging, but if you have the right skills, "
                                    "you can overcome them."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Be Clear and Specific",
                                body="Your response was not specific enough, making it "
                                "difficult for {agent} to understand what you meant. "
                                "Answer the question clearly and provide specific "
                                "details to help {agent} understand your sperspective.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="Who will be speaking at the event?"
                                ),
                                UserMessage(
                                    message="We have some great speakers lined up."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Be Clear and Specific",
                                body="You were too vague in your response. {agent} "
                                "wanted to know who would be speaking at the event, "
                                "but your answer did not specifically address that. "
                                "Try to provide clear responses to {agent}'s "
                                "questions.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="What are the main topics that will be "
                                    "covered at the conference?"
                                ),
                                UserMessage(
                                    message="We will be discussing a variety of "
                                    "relevant subjects. There will be something for "
                                    "everyone."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Be Clear and Specific",
                                body="Your response was too vague and did not provide "
                                "specific details. {agent} wanted to know the main "
                                "topics that would be covered at the conference, but "
                                "your answer did not address that. Be more specific in "
                                "your responses to {agent}'s questions.",
                            ),
                        ),
                    ],
                    next=None,
                )


_FigurativeStateId = Literal[
    "user_answer",
    "agent_react_figurative",
    "feedback_figurative",
]


class _FigurativeData(BaseData[_FigurativeStateId]): ...


class _FigurativeStates(States[_FigurativeData]):
    @property
    def data_type(self):
        return _FigurativeData

    def init(self) -> _FigurativeData:
        return _FigurativeData(state="user_answer")

    def next(self, data) -> State:
        match data.state:
            case "user_answer":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will answer the question using figurative "
                            "language that is not meant to be taken literally. My "
                            "answer will be creative and imaginative, using language "
                            "that is not straightforward.",
                            examples=[
                                (
                                    ("How do you feel about the new project?"),
                                    (
                                        "I think the new project is a breath of fresh "
                                        "air. A blank canvas waiting to be painted."
                                    ),
                                ),
                                (
                                    ("What do you think about the team's progress?"),
                                    (
                                        "The team is progressing like a well-oiled "
                                        "machine. We're firing on all cylinders."
                                    ),
                                ),
                                (
                                    ("How would you describe the client's approach?"),
                                    (
                                        "The client's approach is like a "
                                        "rollercoaster. It's full of ups and downs, "
                                        "but it's always exciting."
                                    ),
                                ),
                            ],
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                        UserOption(
                            instructions="I will answer the question using a touch of "
                            "figurative language. My answer will be mostly literal "
                            "but will include a hint of figurative language to make it "
                            "more interesting.",
                            examples=[
                                (
                                    ("How do you feel about the new project?"),
                                    (
                                        "I'm excited to start anew. I can't wait to "
                                        "dive in and see where it takes us."
                                    ),
                                ),
                                (
                                    ("What do you think about the team's progress?"),
                                    (
                                        "The team is making great strides. We're "
                                        "moving forward at a steady pace."
                                    ),
                                ),
                                (
                                    ("How would you describe the client's approach?"),
                                    (
                                        "The client's approach is unique. They tend to "
                                        "think outside the box and enjoy taking risks."
                                    ),
                                ),
                            ],
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                    ]
                )
            case "agent_react_figurative":
                return AgentState(
                    instructions="I will misinterpret the figurative language used in "
                    "the answer and respond in a literal and direct manner. I fail to "
                    "understand the figurative nature of the language and respond as "
                    "if the answer was meant to be taken literally.",
                    examples=[
                        (
                            ("Let's hit the ground running with this project."),
                            (
                                "What does running have to do with the project? "
                                "We need to focus on the tasks at hand."
                            ),
                        ),
                        (
                            ("The team is on fire with their progress."),
                            (
                                "Why is the team on fire? We need to ensure everyone "
                                "is safe and following proper procedures."
                            ),
                        ),
                        (
                            ("The client's approach is a breath of fresh air."),
                            (
                                "Why would the client's approach be like fresh air? "
                                "We need to focus on the project's goals."
                            ),
                        ),
                    ],
                    next=_FigurativeData(state="feedback_figurative"),
                )

            case "feedback_figurative":
                return FeedbackState(
                    prompt="The latest message needs improvement as it contains "
                    "figurative language, which can be misinterpreted by some "
                    "individuals. Provide feedback on how their message could have "
                    "been clearer and more direct. Explain how the figurative "
                    "language could be confusing.",
                    instructions="I will clarify the figurative language I used in my "
                    "previous answer.",
                    examples=[
                        # TODO: ...
                    ],
                    next=None,
                )


_SarcasticStateId = Literal[
    "user_answer", "agent_react_sarcastic", "feedback_sarcastic"
]


class _SarcasticData(BaseData[_SarcasticStateId]): ...


class _SarcasticStates(States[_SarcasticData]):
    @property
    def data_type(self):
        return _SarcasticData

    def init(self) -> _SarcasticData:
        return _SarcasticData(state="user_answer")

    def next(self, data) -> State:
        match data.state:
            case "user_answer":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will answer the question using sarcasm or "
                            "irony to be humorous. I will use language that is the "
                            "opposite of what I mean to be funny. This is important "
                            "because the other person loves sarcasm and has a great "
                            "sense of humor.",
                            examples=[
                                (
                                    ("Any advice on how to handle the client?"),
                                    (
                                        "Oh, they love it when you show up late. "
                                        "It shows them you're in control."
                                    ),
                                ),
                                (
                                    ("How can we improve the team's communication?"),
                                    (
                                        "Just keep doing what you're doing. It's "
                                        "working wonders."
                                    ),
                                ),
                                (
                                    ("Do you think we should change our approach?"),
                                    (
                                        "Oh, definitely. Change is always a good "
                                        "thing. It's not like the current approach is "
                                        "working or anything."
                                    ),
                                ),
                            ],
                            next=_SarcasticData(state="agent_react_sarcastic"),
                        ),
                    ]
                )
            case "agent_react_sarcastic":
                return AgentState(
                    instructions="I will interpret the message literally, ignoring any "
                    "sarcasm used. I will only address the literal meaning of the "
                    "message without considering that it might be sarcastic. I will "
                    "respond as if the message was meant to be taken seriously, not "
                    "mentioning that I know the user is being sarcastic.",
                    examples=[
                        (
                            ("The bosses love it when you show up late."),
                            (
                                "That's strange. Why would they love that? It's "
                                "unprofessional and disrespectful."
                            ),
                        ),
                        (
                            (
                                "Just keep doing what you're doing. It's working "
                                "wonders."
                            ),
                            (
                                "I'm glad to hear that. I'll make sure to continue "
                                "with the current approach."
                            ),
                        ),
                        (
                            (
                                "Artificial intelligence is just a fad. We are still "
                                "looking for any practical applications. It's not like "
                                "it's the future or anything."
                            ),
                            (
                                "I disagree. AI is the future and has many practical "
                                "applications. I was thinking of using it for the next "
                                "project."
                            ),
                        ),
                    ],
                    next=_SarcasticData(state="feedback_sarcastic"),
                )
            case "feedback_sarcastic":
                return FeedbackState(
                    prompt="The latest message needs improvement as it uses "
                    "sarcasm, which can be misinterpreted by some individuals. "
                    "Provide feedback on how their message could have been clearer "
                    "and more direct. Explain how the sarcasm could be confusing.",
                    instructions="I will clarify the sarcastic language I used in my "
                    "previous answer.",
                    examples=[
                        # TODO: ...
                    ],
                    next=None,
                )


_DirectAnswerStateId = Literal["user_answer"]


class _DirectAnswerData(BaseData[_DirectAnswerStateId]): ...


class _DirectAnswerStates(States[_DirectAnswerData]):
    @property
    def data_type(self):
        return _DirectAnswerData

    def init(self) -> _DirectAnswerData:
        return _DirectAnswerData(state="user_answer")

    def next(self, data) -> State:
        match data.state:
            case "user_answer":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will provide a clear answer. My response "
                            "will be straightforward and address the question "
                            "directly.",
                            next=None,
                        ),
                    ]
                )


_EndStateId = Literal["agent_goodbye", "user_goodbye"]


class _EndData(BaseData[_EndStateId]): ...


class _EndStates(States[_EndData]):
    @property
    def data_type(self):
        return _EndData

    def init(self) -> _EndData:
        return _EndData(state="agent_goodbye")

    def next(self, data) -> State:
        match data.state:
            case "agent_goodbye":
                return AgentState(
                    instructions="I will say that I have no more questions about the "
                    "client. I will thank the person for their time and say goodbye.",
                    next=_EndData(state="user_goodbye"),
                )
            case "user_goodbye":
                return UserState(
                    options=[
                        UserOption(
                            instructions="I will say goodbye and end the conversation.",
                            next=None,
                        ),
                    ]
                )


STATES = ChainStates(
    _IntroStates(),
    RepeatStates(
        ChainStates(
            AgentNaturalStates(),
            UserNaturalStates(),
        ),
        2,
    ),
    RepeatStates(
        ChainStates(
            _AskStates(),
            UnionStates(
                _VagueAnswerStates(),
                _FigurativeStates(),
                _SarcasticStates(),
                base=_DirectAnswerStates(),
            ),
            ChainStates(
                AgentNaturalStates(),
                UserNaturalStates(),
            ),
        ),
        5,
    ),
    _EndStates(),
)

SCENARIO_SEED = LevelConversationScenarioSeed(
    user_perspective=(
        "A colleague reaches out to you to discuss a client who you have "
        "worked with before and asks for your advice [pick a name for the "
        "client]."
    ),
    agent_perspective=(
        "You reach out to a colleague to discuss a client who they have "
        "worked with before and ask for their advice."
    ),
    user_goal=(
        "Discuss the client with your colleague and provide them with "
        "helpful advice."
    ),
    is_user_initiated=False,
    adapt=True,
)
