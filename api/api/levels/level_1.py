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
    WithCtxStates,
)

_IntroStateId = Literal[
    "user_greet",
    "agent_greet",
]


class _IntroData(BaseData[_IntroStateId]): ...


class _IntroStates(States[_IntroData]):
    @property
    def data_type(self):
        return _IntroData

    def init(self) -> _IntroData:
        return _IntroData(state="user_greet")

    def next(self, data) -> State:
        match data.state:
            case "user_greet":
                return UserState(
                    options=[
                        UserOption(
                            instructions="Begin the conversation and mention that you "
                            "noticed the person is doing something interesting, and "
                            "ask if they can tell you more about it. DO NOT ask any "
                            "specific questions yet.",
                            next=_IntroData(state="agent_greet"),
                        ),
                    ]
                )
            case "agent_greet":
                return AgentState(
                    instructions="Greet the person and say that you would be happy to "
                    "answer any questions. DO NOT answer with any specifics yet."
                    "ONLY invite the user to ask questions.",
                    next=None,
                )


_VagueQuestionStateId = Literal[
    "user_ask",
    "agent_answer_confused",
    "feedback",
]


class _VagueQuestionData(BaseData[_VagueQuestionStateId]): ...


class _VagueQuestionStates(States[_VagueQuestionData]):
    @property
    def data_type(self):
        return _VagueQuestionData

    def init(self) -> _VagueQuestionData:
        return _VagueQuestionData(state="user_ask")

    def next(self, data) -> State:
        match data.state:
            case "user_ask":
                return UserState(
                    options=[
                        UserOption(
                            instructions="Ask a question that is vague and open-ended. "
                            "Make sure your question has a subject matter, but it is "
                            "unclear how to answer it. The question could be "
                            "interpreted in multiple ways.",
                            next=_VagueQuestionData(
                                state="agent_answer_confused",
                            ),
                        ),
                        UserOption(
                            instructions="Ask a question that is vague and open-ended. "
                            "Make sure your question is on-topic, but there are many "
                            "ways for the other person to interpret it.",
                            next=_VagueQuestionData(
                                state="agent_answer_confused",
                            ),
                        ),
                    ]
                )
            case "agent_answer_confused":
                return AgentState(
                    instructions="You were just asked a vague question that was "
                    "unclear and too open-ended. You are confused and unsure how to "
                    "respond, leaving you feeling overwhelmed and lost. You can "
                    "only think of the many ways the question could be "
                    "interpreted, and you are unable to answer it. Examples: "
                    "\n'I'm confused what you mean by the components of software "
                    "development. Can you clarify?'"
                    "\n'My favorite part? A lot of things.'"
                    "\nIt depends on what you mean by 'the best.'",
                    next=_VagueQuestionData(state="feedback"),
                )
            case "feedback":
                return FeedbackState(
                    prompt="The latest question needs improvement as it is vague "
                    "or unclear. Questions should be clear and specific. Provide "
                    "examples on how the question was ambiguous.",
                    instructions="Clarify the vague question you just asked.",
                    next=None,
                )


_MidStateId = Literal[
    "user_ask",
    "agent_answer_indirect",
    "agent_answer_binary",
    "feedback",
]


class _IndirectQuestionStateId(BaseData[_MidStateId]): ...


class _IndirectQuestionStates(States[_IndirectQuestionStateId]):
    @property
    def data_type(self):
        return _IndirectQuestionStateId

    def init(self) -> _IndirectQuestionStateId:
        return _IndirectQuestionStateId(state="user_ask")

    def next(self, data) -> State:
        match data.state:
            case "user_ask":
                return UserState(
                    options=[
                        UserOption(
                            instructions="Your next message implies a question "
                            "indirectly, using socially conventional language to be "
                            "more polite, such as asking about a related experience. "
                            "Avoid direct questions and do not state your curiosity "
                            "explicitly.",
                            next=_IndirectQuestionStateId(
                                state="agent_answer_indirect"
                            ),
                        ),
                        UserOption(
                            instructions="Your next message asks a question phrased as "
                            "indirect speech "
                            "to be more polite. You use a suggestion in a statement "
                            "form like 'I'd love to learn more about...' to imply a "
                            "request without directly asking for it. DO NOT ask a "
                            "direct question.",
                            next=_IndirectQuestionStateId(
                                state="agent_answer_indirect"
                            ),
                        ),
                        UserOption(
                            instructions="Your next message asks a question phrased as "
                            "indirect speech to be more polite. You use a yes-or-no "
                            "question like 'Do you know... to imply a request without "
                            "directly asking for it.",
                            next=_IndirectQuestionStateId(state="agent_answer_binary"),
                        ),
                    ]
                )
            case "agent_answer_indirect":
                return AgentState(
                    instructions="You were just given an indirect suggestion. Instead "
                    "of interpreting it as a direct request, you acknowledge the "
                    "suggestion and respond by showing interest or agreement "
                    "without directly providing the requested information "
                    "despite being capable of doing so. DO NOT answer the "
                    "indirect suggestion. Examples: 'I'd love to learn "
                    "more about that!' -> 'Yeah, it's really interesting!'",
                    next=_IndirectQuestionStateId(state="feedback"),
                )
            case "agent_answer_binary":
                return AgentState(
                    instructions="You were just asked a yes-or-no question. You "
                    "interpret the question literally and respond acknowledging "
                    "that you know the information. DO NOT provide the requested "
                    "information.",
                    next=_IndirectQuestionStateId(state="feedback"),
                )
            case "feedback":
                return FeedbackState(
                    prompt="The user used an indirect suggestion instead of a "
                    "direct question, causing the other person to respond with "
                    "an acknowledgment or agreement instead of providing the "
                    "requested information. The user should ask direct questions "
                    "when they want a direct response. Explain how the question "
                    "was indirect.",
                    instructions="Ask a direct question instead of an indirect one.",
                    next=None,
                )


_DirectQuestionId = Literal["user_ask"]


class _DirectQuestionData(BaseData[_DirectQuestionId]): ...


class _DirectQuestionStates(States[_DirectQuestionData]):
    @property
    def data_type(self):
        return _DirectQuestionData

    def init(self) -> _DirectQuestionData:
        return _DirectQuestionData(state="user_ask")

    def next(self, data) -> State:
        assert data.state == "user_ask"
        return UserState(
            options=[
                UserOption(
                    instructions="Ask a question that is clear and specific. Make sure "
                    "your question is straightforward and has a clear subject matter.",
                    next=None,
                )
            ]
        )


_AnswerStateId = Literal["agent_answer"]


class _AnswerData(BaseData[_AnswerStateId]): ...


class _AnswerStates(States[_AnswerData]):
    @property
    def data_type(self):
        return _AnswerData

    def init(self) -> _AnswerData:
        return _AnswerData(state="agent_answer")

    def next(self, data) -> State:
        assert data.state == "agent_answer"
        return AgentState(
            instructions="Answer the question and continue to field questions.",
            next=None,
        )


_EndStateId = Literal["user_goodbye"]


class _EndData(BaseData[_EndStateId]): ...


class _EndStates(States[_EndData]):
    @property
    def data_type(self):
        return _EndData

    def init(self) -> _EndData:
        return _EndData(state="user_goodbye")

    def next(self, data) -> State:
        assert data.state == "user_goodbye"
        return UserState(
            options=[
                UserOption(
                    instructions="Say that you are excited to join. Say goodbye and "
                    "end the conversation.",
                    next=None,
                )
            ]
        )


STATES = ChainStates(
    _IntroStates(),
    WithCtxStates(
        RepeatStates(
            ChainStates(
                UnionStates(
                    _VagueQuestionStates(),
                    _IndirectQuestionStates(),
                    base=_DirectQuestionStates(),
                ),
                _AnswerStates(),
            ),
            5,
        ),
        user_ctx="Ask questions to learn more about the activity.",
    ),
    WithCtxStates(
        ChainStates(
            UnionStates(
                _IndirectQuestionStates(),
                base=_DirectQuestionStates(),
            ),
            WithCtxStates(
                _AnswerStates(), agent_ctx="Tell the user they are welcome to join."
            ),
        ),
        user_ctx="Do not ask for more information. Ask to join the activity.",
    ),
    _EndStates(),
)

SCENARIO_SEED = LevelConversationScenarioSeed(
    user_perspective=(
        "You find a person online and want to join their group activity."
    ),
    agent_perspective=(
        "A person reaches out to you online and wants to join your group activity."
    ),
    user_goal=("Learn more about what the person is doing and join them."),
    is_user_initiated=True,
    adapt=True,
)
