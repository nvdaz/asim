import random
from abc import ABC, abstractmethod
from typing import (
    Annotated,
    Any,
    Callable,
    Generic,
    Literal,
    TypeVar,
)

from pydantic import BaseModel, Field, SerializeAsAny

from api.schemas.conversation import (
    BaseData,
    BaseFeedback,
    Message,
)

StateId = TypeVar("StateId")


Data = TypeVar("Data", bound=BaseData)


class UserOption(BaseModel, Generic[Data]):
    instructions: str
    examples: list[tuple[str, str] | str] | None = None
    next: Data | None


class UserState(BaseModel, Generic[Data]):
    type: Literal["user"] = "user"
    options: list[UserOption[Data]]


class AgentState(BaseModel, Generic[Data]):
    type: Literal["agent"] = "agent"
    instructions: str
    examples: list[tuple[str, str] | str] | None = None
    next: Data | None


class FeedbackState(BaseModel, Generic[Data]):
    type: Literal["feedback"] = "feedback"
    prompt: str
    instructions: str
    examples: list[tuple[list[Message], BaseFeedback]]
    next: Data | None


State = Annotated[UserState | AgentState | FeedbackState, Field(discriminator="type")]

InData = TypeVar("InData", bound=BaseData)
OutData = TypeVar("OutData", bound=BaseData)


def wrap_state_next(
    state: State, wrap: Callable[[InData | None], OutData | None]
) -> State:
    match state:
        case UserState(options=opts):
            return UserState(
                options=[
                    UserOption(
                        instructions=option.instructions,
                        examples=option.examples,
                        next=wrap(option.next),
                    )
                    for option in opts
                ]
            )
        case AgentState(instructions=instructions, examples=examples, next=next):
            return AgentState(
                instructions=instructions,
                examples=examples,
                next=wrap(next),
            )
        case FeedbackState(
            prompt=prompt, instructions=instructions, examples=examples, next=next
        ):
            return FeedbackState(
                prompt=prompt,
                instructions=instructions,
                examples=examples,
                next=wrap(next),
            )
        case _:
            raise ValueError(f"Could not wrap unknown state type: {state}")


class States(ABC, Generic[Data]):
    @property
    @abstractmethod
    def data_type(self) -> type[Data]: ...

    @abstractmethod
    def init(self) -> Data: ...

    @abstractmethod
    def next(self, data: Data) -> State: ...


StateTransitionFn = Callable[[Data], State]


class ChainStateData(BaseData[int]):
    inner_data: SerializeAsAny[BaseData]


class ChainStates(States[ChainStateData]):
    @property
    def data_type(self):
        return ChainStateData

    def __init__(self, *states: States[Any]):
        assert states, "At least one state is required"
        self.states = states

    def init(self) -> ChainStateData:
        return ChainStateData(state=0, inner_data=self.states[0].init())

    def next(self, data: ChainStateData) -> State:
        state = self.states[data.state]
        inner_data: BaseData[Any] | dict = data.inner_data
        # this may be parsed as a dict from JSON since it's nested.
        if isinstance(inner_data, dict):
            inner_data = self.states[data.state].data_type(**inner_data)
        next_data = state.next(inner_data)

        state = self.states[data.state]

        def wrap_next(wrap_data: BaseData | None) -> ChainStateData | None:
            next_state = data.state + 1
            if wrap_data is None:
                if next_state < len(self.states):
                    return ChainStateData(
                        state=next_state,
                        inner_data=self.states[next_state].init(),
                    )
                else:
                    return None
            else:
                return ChainStateData(
                    state=data.state,
                    inner_data=wrap_data,
                )

        return wrap_state_next(next_data, wrap_next)


class RepeatStateData(BaseData[int], Generic[Data]):
    inner_data: SerializeAsAny[Data]


class RepeatStates(Generic[Data], States[RepeatStateData]):
    @property
    def data_type(self):
        return RepeatStateData

    def __init__(self, state: States[Data], count: int):
        assert count > 0, "count must be positive"
        self.state = state
        self.count = count

    def init(self) -> RepeatStateData:
        return RepeatStateData(state=0, inner_data=self.state.init())

    def next(self, data: RepeatStateData) -> State:
        inner_data: Data | dict = data.inner_data
        # this may be parsed as a dict from JSON since it's nested.
        if isinstance(inner_data, BaseModel):
            inner_data = self.state.data_type(**inner_data.model_dump())
        if isinstance(inner_data, dict):
            inner_data = self.state.data_type(**inner_data)

        assert isinstance(inner_data, self.state.data_type)

        next_data = self.state.next(inner_data)

        def wrap_next(wrap_data: Data | None) -> RepeatStateData | None:
            next_state = data.state + 1
            if wrap_data is None:
                if next_state < self.count:
                    return RepeatStateData(
                        state=next_state,
                        inner_data=self.state.init(),
                    )
            else:
                return RepeatStateData(
                    state=data.state,
                    inner_data=wrap_data,
                )

        return wrap_state_next(next_data, wrap_next)


class UnionStatesData(BaseData[int]):
    inner_data: SerializeAsAny[BaseData]


class UnionStates(States[UnionStatesData]):
    @property
    def data_type(self):
        return UnionStatesData

    def __init__(self, *states: States[Any], base: States[Any]):
        assert states, "At least one state is required"
        self.states = states
        self.base_state = base

        base_data = base.init()
        assert all(
            init_state.init().state == base_data.state for init_state in states
        ), "All states must have the same init data"
        self._init_state: str = base_data.state

    def init(self) -> UnionStatesData:
        return UnionStatesData(state=-1, inner_data=self.states[0].init())

    def next(self, data: UnionStatesData) -> State:
        def wrap_next_with_index(
            state_index: int,
        ) -> Callable[[BaseData | None], UnionStatesData | None]:
            def wrap_next(
                wrap_data: BaseData | None,
            ) -> UnionStatesData | None:
                if wrap_data:
                    return UnionStatesData(
                        state=state_index,
                        inner_data=wrap_data,
                    )
                else:
                    return None

            return wrap_next

        if data.state == -1:
            inner_data: BaseData[Any] | dict = data.inner_data
            # this may be parsed as a dict from JSON since it's nested.
            if isinstance(inner_data, BaseModel):
                inner_data = self.base_state.data_type(**inner_data.model_dump())
            if isinstance(inner_data, dict):
                inner_data = self.base_state.data_type(**inner_data)
            base_state = self.base_state.next(inner_data)
            all_states = [states.next(states.init()) for states in self.states]

            if not all(
                isinstance(state, UserState) for state in all_states
            ) or not isinstance(base_state, UserState):
                raise ValueError("All states must be user states")

            wrapped_base = wrap_state_next(base_state, wrap_next_with_index(0))
            wrapped_all = [
                wrap_state_next(state, wrap_next_with_index(i + 1))
                for i, state in enumerate(all_states)
            ]

            assert isinstance(wrapped_base, UserState)

            base_options = wrapped_base.options
            other_options = [
                option
                for state in wrapped_all
                if isinstance(state, UserState)
                for option in state.options
            ]

            options = base_options + random.sample(other_options, 3 - len(base_options))

            return UserState(options=options)
        else:
            state = self.states[data.state - 1] if data.state > 0 else self.base_state
            inner_data: BaseData[Any] | dict = data.inner_data
            # this may be parsed as a dict from JSON since it's nested.
            if isinstance(inner_data, BaseModel):
                inner_data = state.data_type(**inner_data.model_dump())
            if isinstance(inner_data, dict):
                inner_data = state.data_type(**inner_data)
            next_data = state.next(inner_data)

            return wrap_state_next(next_data, wrap_next_with_index(data.state))


class WithCtxStates(Generic[Data], States[Data]):
    def __init__(
        self,
        states: States[Data],
        user_ctx: str | None = None,
        agent_ctx: str | None = None,
    ):
        self.states = states
        self.user_ctx = user_ctx
        self.agent_ctx = agent_ctx

    @property
    def data_type(self):
        return self.states.data_type

    def init(self) -> Data:
        return self.states.init()

    def next(self, data: Data) -> State:
        state = self.states.next(data)
        if isinstance(state, UserState) and self.user_ctx:
            return UserState(
                options=[
                    UserOption(
                        instructions=f"{option.instructions} {self.user_ctx}",
                        examples=option.examples,
                        next=option.next,
                    )
                    for option in state.options
                ]
            )
        elif isinstance(state, AgentState) and self.agent_ctx:
            return AgentState(
                instructions=f"{state.instructions} {self.agent_ctx}",
                examples=state.examples,
                next=state.next,
            )
        else:
            return state


_UserNaturalProgressionId = Literal["user_natural"]


class _UserNaturalData(BaseData[_UserNaturalProgressionId]): ...


class UserNaturalStates(States[_UserNaturalData]):
    @property
    def data_type(self):
        return _UserNaturalData

    def init(self) -> _UserNaturalData:
        return _UserNaturalData(state="user_natural")

    def next(self, data) -> State:
        return UserState(
            options=[
                UserOption(
                    instructions="I will continue the conversation naturally. "
                    "I will be clear and direct in my responses and respond "
                    "positively.",
                    next=None,
                ),
                UserOption(
                    instructions="I will continue the conversation naturally. "
                    "I will be clear and direct in my responses and respond "
                    "enthusiastically.",
                    next=None,
                ),
                UserOption(
                    instructions="I will continue the conversation naturally. "
                    "I will be clear and direct in my responses and respond "
                    "moderately.",
                    next=None,
                ),
            ]
        )


_AgentNaturalProgressionId = Literal["agent_natural"]


class _AgentNaturalData(BaseData[_AgentNaturalProgressionId]): ...


class AgentNaturalStates(States[_AgentNaturalData]):
    @property
    def data_type(self):
        return _AgentNaturalData

    def init(self) -> _AgentNaturalData:
        return _AgentNaturalData(state="agent_natural")

    def next(self, data) -> State:
        return AgentState(
            instructions="I will continue the conversation naturally.",
            next=None,
        )
