from typing import Literal

from .seed import LevelConversationScenarioSeed
from .states import (
    AgentState,
    BaseData,
    ChainStates,
    FeedbackState,
    RepeatStates,
    State,
    States,
    UnionStates,
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
                    instructions="Begin the conversation and mention that you have "
                    "heard the other person has worked with a client that you would "
                    "like to discuss. Ask if this is true.",
                    next=_IntroData(state="user_greet"),
                )
            case "user_greet":
                return UserState(
                    options=[
                        UserOption(
                            instructions="Greet the person and confirm that you have "
                            "worked with the client they mentioned. Tell them that you "
                            "are happy to answer any questions they have about the "
                            "client.",
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
                    instructions="Ask a question that is clear and specific. DO NOT "
                    "ASK ABOUT TRIVIAL DETAILS like date, time, or location.",
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
                            instructions="Provide a vague and non-specific answer. "
                            "Make sure your response is ambiguous and can be "
                            "interpreted in multiple ways. You KNOW EXACTLY what the "
                            "answer is and everything is already finalized, but you "
                            "are being intentionally vague they are also being vague. "
                            "DO NOT mention that you are not being clear. YOU KNOW THE "
                            "ANSWER EXACTLY BUT YOU ARE BEING VAGUE WITHOUT MENTIONING "
                            "IT.",
                            next=_VagueAnswerData(state="agent_react_vague"),
                        ),
                        UserOption(
                            instructions="Provide a vague and unclear answer. Make "
                            "sure your response is highly ambiguous and difficult to "
                            "understand.You KNOW EXACTLY what the answer is and "
                            "everything is already finalized, but you are being "
                            "intentionally vague they are also being vague. DO NOT "
                            "mention that you are not being clear. YOU KNOW THE ANSWER "
                            "EXACTLY BUT YOU ARE BEING VAGUE WITHOUT MENTIONING IT.",
                            next=_VagueAnswerData(state="agent_react_vague"),
                        ),
                    ]
                )
            case "agent_react_vague":
                return AgentState(
                    instructions="You just received a vague and unclear answer that is "
                    "highly ambiguous. You are confused and unsure how to proceed, "
                    "feeling frustrated by the lack of clarity. Reflect on how the "
                    "vague wording makes it difficult to understand the response.",
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
                    instructions="Clarify the vague answer you provided.",
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
                            instructions="Answer the question using figurative "
                            "language. You use language that is not literal and does "
                            "not mean exactly what it says. Your message is intended "
                            "to be interpreted in a non-literal way. Example: 'Let's "
                            "hit the books.'",
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                        UserOption(
                            instructions="Answer the question using mostly literal, "
                            "but include a hint of figurative language. The message is "
                            "mostly straightforward, but there is also a figurative "
                            "element that could be misinterpreted. Example: 'It's so "
                            "hot, it feels like 1000 degrees outside.'",
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                    ]
                )
            case "agent_react_figurative":
                return AgentState(
                    instructions="Respond to the message in a way that misunderstands "
                    "the figurative language used. Your response should be literal "
                    "and direct, only addressing the literal meaning of the "
                    "message without considering the figurative nature. Example: "
                    "'Let's hit the books.' -> 'I don't have any books to hit.'",
                    next=_FigurativeData(state="feedback_figurative"),
                )

            case "feedback_figurative":
                return FeedbackState(
                    prompt="The latest message needs improvement as it contains "
                    "figurative language, which can be misinterpreted by autistic "
                    "individuals. Provide feedback on how their message could have "
                    "been clearer and more direct. Explain how the figurative "
                    "language could be confusing.",
                    instructions="Clarify the figurative language you used.",
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
                            instructions="Answer the question using sarcasm or irony. "
                            "You use language that is the opposite of what you mean to "
                            "be humorous. Example: 'They love it when you show up "
                            "late.'",
                            next=_SarcasticData(state="agent_react_sarcastic"),
                        ),
                    ]
                )
            case "agent_react_sarcastic":
                return AgentState(
                    instructions="Interpret the message literally, ignoring the "
                    "sarcasm used. ONLY address the literal meaning of the message "
                    "without considering the figurative nature. DO NOT mention that "
                    "you know the user is being sarcastic. Example: 'They love it "
                    "when you show up late.' -> 'Why would they love that?'",
                    next=_SarcasticData(state="feedback_sarcastic"),
                )
            case "feedback_sarcastic":
                return FeedbackState(
                    prompt="The latest message needs improvement as it uses "
                    "sarcasm, which can be misinterpreted by autistic individuals. "
                    "Provide feedback on how their message could have been clearer "
                    "and more direct. Explain how the sarcasm could be confusing.",
                    instructions="Clarify the sarcastic language you used.",
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
                            instructions="Provide a clear and specific answer. Make "
                            "sure your response is straightforward and addresses the "
                            "question directly.",
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
                    instructions="Say that you have no more questions about the "
                    "client. Thank the person for their time and say goodbye.",
                    next=_EndData(state="user_goodbye"),
                )
            case "user_goodbye":
                return UserState(
                    options=[
                        UserOption(
                            instructions="Say goodbye and end the conversation.",
                            next=None,
                        ),
                    ]
                )


STATES = ChainStates(
    _IntroStates(),
    RepeatStates(
        ChainStates(
            _AskStates(),
            UnionStates(
                _VagueAnswerStates(),
                _FigurativeStates(),
                _SarcasticStates(),
                base=_DirectAnswerStates(),
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
