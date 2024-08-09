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

_IntroStateId = Literal["user_greet"]


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
                            "noticed a mess and need to inform the other person about "
                            "it.",
                            next=None,
                        ),
                    ]
                )


_FrustratedStateId = Literal["agent_frustrated"]


class _FrustratedData(BaseData[_FrustratedStateId]): ...


class _FrustratedStates(States[_FrustratedData]):
    @property
    def data_type(self):
        return _FrustratedData

    def init(self) -> _FrustratedData:
        return _FrustratedData(state="agent_frustrated")

    def next(self, data) -> State:
        match data.state:
            case "agent_frustrated":
                return AgentState(
                    instructions="You are upset about the situation and express your "
                    "frustration bluntly. Your message should be direct and "
                    "urgent, potentially leading the other person to feel you are "
                    "upset with them.",
                    next=None,
                )


_UserReactConfrontationalStateId = Literal[
    "user_react",
    "agent_react_dismissive",
    "agent_react_confrontational",
    "feedback_dismissive",
    "feedback_confrontational",
]


class _UserReactConfrontationalData(BaseData[_UserReactConfrontationalStateId]): ...


class _UserReactConfrontationalStates(States[_UserReactConfrontationalData]):
    @property
    def data_type(self):
        return _UserReactConfrontationalData

    def init(self) -> _UserReactConfrontationalData:
        return _UserReactConfrontationalData(state="user_react")

    def next(self, data) -> State:
        match data.state:
            case "user_react":
                return UserState(
                    options=[
                        UserOption(
                            instructions="You just received a frustrated message and "
                            "respond with a dismissive message since you believe the "
                            "other person is being rude to you.",
                            next=_UserReactConfrontationalData(
                                state="agent_react_dismissive"
                            ),
                        ),
                        UserOption(
                            instructions="You just received a frustrated message and "
                            "are confused why the other person is upset with you. You "
                            "ask why they are upset with you since it's not your fault "
                            "in an accusatory tone.",
                            next=_UserReactConfrontationalData(
                                state="agent_react_confrontational"
                            ),
                        ),
                    ]
                )
            case "agent_react_dismissive":
                return AgentState(
                    instructions="You are upset with the situation and feel the other "
                    "person is being dismissive. You respond with a blunt message.",
                    next=_UserReactConfrontationalData(state="feedback_dismissive"),
                )
            case "agent_react_confrontational":
                return AgentState(
                    instructions="You are upset with the situation and feel the other "
                    "person is being confrontational towards you. You respond with a "
                    "blunt message.",
                    next=_UserReactConfrontationalData(
                        state="feedback_confrontational"
                    ),
                )
            case "feedback_dismissive":
                return FeedbackState(
                    prompt="The latest message was dismissive and rude. The user needs "
                    "to be more empathetic and understanding in their response. "
                    "Provide feedback on how the user could have been more "
                    "understanding and empathetic in their response.",
                    instructions="Apologize for being dismissive.",
                    next=None,
                )
            case "feedback_confrontational":
                return FeedbackState(
                    prompt="The latest message was confrontational and aggressive. "
                    "The user overreacted to a blunt message and needs to use "
                    "neutral language instead. Provide feedback on how the user "
                    "could have been more empathetic and understanding in their "
                    "response.",
                    instructions="Apologize for being confrontational.",
                    next=None,
                )


_UserReactInterpretSarcasmStateId = Literal[
    "user_react", "agent_react_sarcastic", "feedback_sarcastic"
]


class _UserReactInterpretSarcasmData(BaseData[_UserReactInterpretSarcasmStateId]): ...


class _UserReactInterpretSarcasmStates(States[_UserReactInterpretSarcasmData]):
    @property
    def data_type(self):
        return _UserReactInterpretSarcasmData

    def init(self) -> _UserReactInterpretSarcasmData:
        return _UserReactInterpretSarcasmData(state="user_react")

    def next(self, data) -> State:
        match data.state:
            case "user_react":
                return UserState(
                    options=[
                        UserOption(
                            instructions="You just received a blunt message that you "
                            "interpret as sarcastic, thinking the other person is "
                            "being rude.",
                            next=_UserReactInterpretSarcasmData(
                                state="agent_react_sarcastic"
                            ),
                        ),
                    ]
                )
            case "agent_react_sarcastic":
                return AgentState(
                    instructions="You are upset with the situation and feel the other "
                    "person does not understand that you are not being sarcastic.",
                    next=_UserReactInterpretSarcasmData(state="feedback_sarcastic"),
                )
            case "feedback_sarcastic":
                return FeedbackState(
                    prompt="The latest message was interpreted as sarcastic and "
                    "dismissed. The user needs to be more empathetic and understanding "
                    "in their response. Provide feedback on how the user could have "
                    "responded more appropriately.",
                    instructions="Apologize for incorrectly interpreting the message.",
                    next=None,
                )


_UserReactEmpatheticStateId = Literal["user_react"]


class _UserReactEmpatheticData(BaseData[_UserReactEmpatheticStateId]): ...


class _UserReactEmpatheticStates(States[_UserReactEmpatheticData]):
    @property
    def data_type(self):
        return _UserReactEmpatheticData

    def init(self) -> _UserReactEmpatheticData:
        return _UserReactEmpatheticData(state="user_react")

    def next(self, data) -> State:
        return UserState(
            options=[
                UserOption(
                    instructions="Respond to the message you received. You realize the "
                    "frustration is not directed at you.",
                    next=None,
                ),
            ]
        )


STATES = ChainStates(
    _IntroStates(),
    RepeatStates(
        ChainStates(
            _FrustratedStates(),
            UnionStates(
                _UserReactConfrontationalStates(),
                _UserReactInterpretSarcasmStates(),
                base=_UserReactEmpatheticStates(),
            ),
        ),
        5,
    ),
)

SCENARIO_SEED = LevelConversationScenarioSeed(
    user_perspective=(
        "There is a mess caused by things out of your control, so you "
        "reach out to someone to inform them about it."
    ),
    agent_perspective=(
        "You receive a message from someone you know about a mess, leaving "
        "you feeling frustrated about the situation."
    ),
    user_goal=("Inform the person about the mess."),
    is_user_initiated=True,
    adapt=True,
)
