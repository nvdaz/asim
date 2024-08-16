from typing import Literal

from api.schemas.conversation import AgentMessage, BaseFeedback, UserMessage
from api.services import llm

from .seed import LevelConversationScenarioSeed
from .states import (
    AgentNaturalStates,
    AgentState,
    BaseData,
    ChainStates,
    FeedbackState,
    MessageInstructions,
    RepeatStates,
    State,
    States,
    UnionStates,
    UserNaturalStates,
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
                            instructions=MessageInstructions(
                                description="I will start the conversation with a "
                                "greeting and mention that I noticed the person is "
                                "doing something interesting. I will ask if they can "
                                "tell me more about it while avoiding asking any "
                                "specific questions yet.",
                            ),
                            next=_IntroData(state="agent_greet"),
                        ),
                    ]
                )
            case "agent_greet":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will greet the person and say that I would be "
                        "happy to tell them more about what I'm doing. I will invite "
                        "them to ask questions without providing any specifics yet.",
                    ),
                    next=None,
                )


_VagueQuestionStateId = Literal[
    "user_ask",
    "agent_answer_confused",
    "feedback_vague",
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
                            instructions=MessageInstructions(
                                description="I will ask a vague question that is "
                                "unclear and too open-ended. I will make sure my "
                                "question has a subject matter, but the question is "
                                "ambiguous and could be interpreted in multiple ways.",
                                examples=[
                                    (
                                        "What is software made of? [asking what "
                                        "software is made of is vague because software "
                                        "isn't made of physical materials like plastic "
                                        "or metal.]"
                                    ),
                                    (
                                        "I love hiking too. What else are you "
                                        "passionate about?[asking what else they are "
                                        "passionate about is vague because there are "
                                        "many things they could be passionate about.]"
                                    ),
                                    (
                                        "That's so cool! I love animals too. What do "
                                        "you like about your volunteer work? [asking "
                                        "what they like about volunteering is vague "
                                        "because there are many aspects of "
                                        "volunteering they could like.]"
                                    ),
                                ],
                            ),
                            next=_VagueQuestionData(
                                state="agent_answer_confused",
                            ),
                        ),
                    ]
                )
            case "agent_answer_confused":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will respond to the vague question I was just "
                        "asked by being confused and unsure how to respond because the "
                        "question is too vague for me to understand. I will show that "
                        "I am confused and lost. I can only think of the many ways the "
                        "question could be interpreted, and I am not able to answer "
                        "it.",
                        examples=[
                            (
                                ("What is software made of?"),
                                (
                                    "I'm confused what you mean by that."
                                    "Software isn't made of anything. It's a program "
                                    "that runs on a computer."
                                ),
                            ),
                            (
                                ("What do you like about your job?"),
                                (
                                    "A lot of things. There are many aspects "
                                    "of my job that I enjoy."
                                ),
                            ),
                            (
                                ("How should teams approach their strategy in soccer?"),
                                (
                                    "I'm not sure what you mean by that. "
                                    "There are so many ways to approach strategy."
                                ),
                            ),
                        ],
                    ),
                    next=_VagueQuestionData(state="feedback_vague"),
                )
            case "feedback_vague":
                return FeedbackState(
                    prompt="The latest question needs improvement as it is vague "
                    "or unclear. Questions should be clear and specific. Provide "
                    "examples on how the question was ambiguous.",
                    examples=[
                        (
                            [
                                UserMessage(message="What is software made of?"),
                                AgentMessage(
                                    message="I'm confused what you mean by that."
                                    "Software isn't made of anything. It's a program "
                                    "that runs on a computer."
                                ),
                            ],
                            BaseFeedback(
                                title="🔍 Keep Questions Clear",
                                body="Your question was vague and open-ended, making "
                                "it unclear what you were asking. {agent} was confused "
                                "because software isn't made of physical materials "
                                "plastic or metal. To ensure you get the information "
                                "you want, ask clear questions.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="How is AI being used for climate change?"
                                ),
                                AgentMessage(
                                    message="AI is being used in a lot of ways."
                                ),
                            ],
                            BaseFeedback(
                                title="🔍 Be Specific",
                                body="Your question was vague and open-ended, making "
                                "it unclear what you were asking. {agent} was confused "
                                "because AI is used in many ways, so it was unclear "
                                "what you wanted to know. To ensure you get the "
                                "information you want, ask clear and specific "
                                "questions.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="How should teams approach their strategy "
                                    "in soccer?"
                                ),
                                AgentMessage(
                                    message="I'm not sure what you mean by that. "
                                    "There are so many ways to approach strategy."
                                ),
                            ],
                            BaseFeedback(
                                title="🔍 Be Clear",
                                body="You asked a question that was too open-ended, "
                                "making it unclear what you were asking. There are "
                                "many ways to approach strategy in soccer--tactics, "
                                "team selection, training, etc. {agent} was confused "
                                "because it was unclear what you wanted to know. Ask "
                                "{agent} a clear and specific question to get the "
                                "information you want.",
                            ),
                        ),
                    ],
                    follow_up=MessageInstructions(
                        description="I just asked a vague question that was unclear "
                        "and caused confusion. I need to clarify the vague question so "
                        "the other person can understand what I am asking.",
                        examples=[
                            (
                                ("What is software made of?"),
                                (
                                    "I'm confused what you mean by that."
                                    "Software isn't made of anything. It's a program "
                                    "that runs on a computer."
                                ),
                                (
                                    "What are the components that are typically used "
                                    "to create desktop applications?"
                                ),
                            ),
                            (
                                ("How is AI being used for climate change?"),
                                ("AI is being used in a lot of ways."),
                                (
                                    "What are some ways that reinforcement learning is "
                                    "being used to improve predictions for climate "
                                    "change?"
                                ),
                            ),
                            (
                                ("How should teams approach their strategy in soccer?"),
                                (
                                    "I'm not sure what you mean by that. "
                                    "There are so many ways to approach strategy."
                                ),
                                (
                                    "What are some common formations that teams often "
                                    "use in soccer?"
                                ),
                            ),
                        ],
                    ),
                    next=None,
                )


_BinaryIndirectQuestionStateId = Literal[
    "user_ask",
    "agent_answer_binary_indirect",
    "feedback_binary_indirect",
]


class _BinaryIndirectQuestionData(BaseData[_BinaryIndirectQuestionStateId]): ...


class _BinaryIndirectQuestionStates(States[_BinaryIndirectQuestionData]):
    @property
    def data_type(self):
        return _BinaryIndirectQuestionData

    def init(self) -> _BinaryIndirectQuestionData:
        return _BinaryIndirectQuestionData(state="user_ask")

    def next(self, data) -> State:
        match data.state:
            case "user_ask":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                description="I want to ask an open-ended question but "
                                "instead of asking directly, I will ask a yes-or-no "
                                "question to be more polite. My yes-or-no question "
                                "will imply that I want something without directly "
                                "asking. Even though my question is phrased as a "
                                "yes-or-no question, it will elicit an open-ended "
                                "responses from {agent}, My question cannot be "
                                "answered with a simple yes or no.",
                                examples=[
                                    (
                                        "Do you know what time it is? [asking if they "
                                        "know the time implies that you want to know "
                                        "the time.]"
                                    ),
                                    (
                                        "Would you be able to tell me more about your "
                                        "group? [asking if they are able to tell you "
                                        "more implies that you want to know more.]"
                                    ),
                                    (
                                        "Do you have any tips for new members? [asking "
                                        "if they have tips implies that you want them "
                                        "to give you tips.]"
                                    ),
                                ],
                            ),
                            next=_BinaryIndirectQuestionData(
                                state="agent_answer_binary_indirect"
                            ),
                        ),
                    ]
                )
            case "agent_answer_binary_indirect":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I misunderstand the yes-or-no question and "
                        "interpret it directly without providing the requested "
                        "information. I directly answer by saying yes without "
                        "providing the information requested. I know the answer and "
                        "can provide the information but I do not because the question "
                        "was indirect, so I do not know whether the user wants me to "
                        "elaborate. Since I was not asked directly, I will not provide "
                        "the information requested and will not elaborate.",
                        examples=[
                            (
                                ("Do you know what the best item is in Halo?"),
                                (
                                    "A lot of people don't know what the best item is, "
                                    "but I do know what it is."
                                ),
                            ),
                            (
                                ("Would you be able to tell me more about oil spills?"),
                                (
                                    "Yes, I can tell you more about oil spills. I have "
                                    "studied them for 15 years, so I have a lot of "
                                    "knowledge on the topic."
                                ),
                            ),
                            (
                                ("Do you have any tips for beginners?"),
                                (
                                    "I do have a few tips that I often share with "
                                    "beginners. I have lots of experience, so I've "
                                    "learned a lot over the years."
                                ),
                            ),
                            (
                                (
                                    "Would you be able to share some insights into how "
                                    "new members typically integrate into the club's "
                                    "activities and community?"
                                ),
                                ("Yes, I would be able to share some insights."),
                            ),
                            (
                                ("Do you know if they need any help at the shelter?"),
                                (
                                    "Yes. I am part of the group that volunteers "
                                    "there, so I do know if they need help."
                                ),
                            ),
                        ],
                    ),
                    next=_BinaryIndirectQuestionData(state="feedback_binary_indirect"),
                )
            case "feedback_binary_indirect":
                return FeedbackState(
                    prompt="The user used a yes-or-no question instead of a direct "
                    "question, causing the other person to respond with a yes or no "
                    "answer instead of providing the requested information. The user "
                    "should ask direct questions when they want a direct response. "
                    "Carefully explain how the question caused the other person to "
                    "respond with a yes or no answer instead of providing the "
                    "requested information. Specifically mention the part of the "
                    "question that prompted the yes or no response.",
                    examples=[
                        (
                            [
                                UserMessage(
                                    message="Do you know if there are any good "
                                    "books on carbon capture?"
                                ),
                                AgentMessage(
                                    message="Yes, I do know if there are any."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Use Direct Questions",
                                body="{agent} responded by affirming that they did "
                                "know if there were any good books on carbon capture. "
                                "Your original question was misinterpreted as a query "
                                "about whether {agent} knew about the existence of "
                                "such books because you used the phrase 'Do you know'. "
                                "Taken literally, saying 'Yes, I do know' is a valid "
                                "response to the question you asked. If you want "
                                "{agent} to provide book recommendations, ask "
                                "directly.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Would you be able to tell me more about "
                                    "oil spills?"
                                ),
                                AgentMessage(
                                    message=(
                                        "Yes, I can tell you more about oil spills. I "
                                        "have studied them for 15 years, so I have a "
                                        "lot of knowledge on the topic."
                                    ),
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Be Direct",
                                body="Your question was interpreted as asking whether "
                                "{agent} was capable of discussing oil spills, rather "
                                "than requesting detailed information. As a result, "
                                "{agent} confirmed their ability but didn't provide "
                                "the specifics you were looking for. The phrase 'Would "
                                "you be able to' was taken literally, leading to a "
                                "generic response. To get detailed information, ask "
                                "{agent} directly.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Would you mind telling me more about the "
                                    "club's activities and community?"
                                ),
                                AgentMessage(
                                    message="Sure, I can tell you more about that."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Ask Specific Questions",
                                body="{agent} responded by confirming that they would "
                                "not mind sharing more information about the club's "
                                "activities and community. However, your question was "
                                "interpreted as asking whether {agent} was willing to "
                                "provide more information, rather than requesting "
                                "specific details because you only asked if they would "
                                "mind. To get the information you're looking for, ask "
                                "{agent} directly.",
                            ),
                        ),
                    ],
                    follow_up=MessageInstructions(
                        model=llm.Model.GPT_4,
                        description="I will clarify the indirect question I asked "
                        "which received a yes or no answer. I will ask a direct "
                        "question to get the information I want. My direct question "
                        "will not start with 'could'.",
                        examples=[
                            (
                                (
                                    "I'd love to learn more about green "
                                    "innovations in artifical intelligence you "
                                    "mentioned."
                                ),
                                ("Yeah, it's really interesting!"),
                                (
                                    "What kind of green innovations are you working "
                                    "on in AI?"
                                ),
                            ),
                            (
                                (
                                    "Do you know if there are any good "
                                    "books on carbon capture?"
                                ),
                                ("Yes, I do know if there are any."),
                                (
                                    "What are some good books on carbon capture that "
                                    "you would recommend?"
                                ),
                            ),
                            (
                                (
                                    "I was wondering how you usually approach "
                                    "problems like this."
                                ),
                                (
                                    "I see. I understand why you would wonder "
                                    "about that. It's a common question."
                                ),
                                ("How would you usually approach problems like this?"),
                            ),
                            (
                                (
                                    "Would it be possible for you to provide an "
                                    "example overview of what a full meditation "
                                    "session looks like from start to finish?"
                                ),
                                (
                                    "It would be possible for me to provide that. I "
                                    "can give you an overview of a meditation session."
                                ),
                                (
                                    "Please provide an example overview of what a full "
                                    "meditation session looks like from start to "
                                    "finish."
                                ),
                            ),
                        ],
                    ),
                    next=None,
                )


_SuggestiveIndirectQuestionStateId = Literal[
    "user_ask",
    "agent_answer_suggestive_indirect",
    "feedback_suggestive_indirect",
]


class _SuggestiveIndirectQuestionData(BaseData[_SuggestiveIndirectQuestionStateId]): ...


class _SuggestiveIndirectQuestionStates(States[_SuggestiveIndirectQuestionData]):
    @property
    def data_type(self):
        return _SuggestiveIndirectQuestionData

    def init(self) -> _SuggestiveIndirectQuestionData:
        return _SuggestiveIndirectQuestionData(state="user_ask")

    def next(self, data) -> State:
        match data.state:
            case "user_ask":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                description="I will use an indirect suggestion to be "
                                "more polite. Instead of asking a direct question, I "
                                "will make a statement that implies I want something "
                                "without directly asking.",
                                examples=[
                                    (
                                        "I'd love to learn more about green "
                                        "innovations in artificial intelligence you "
                                        "mentioned. [saying that you'd love to learn "
                                        "more implies that you want them to tell you "
                                        "more.]"
                                    ),
                                    (
                                        "I love Halo too! Do you have time to play "
                                        "later this week? [asking if they have time to "
                                        "play implies that you want to play with them.]"
                                    ),
                                    (
                                        "Your hiking group sounds amazing. I love "
                                        "hiking too, but my group disbanded recently. "
                                        "[saying that your group disbanded implies "
                                        "that you want to join their group.]"
                                    ),
                                    (
                                        "That's so cool that you manage a group that "
                                        "volunteers at animal shelters! I love "
                                        "animals, so I've always wanted to try "
                                        "volunteering at one. [saying that you've "
                                        "always wanted to try volunteering implies "
                                        "that you want to join their group.]"
                                    ),
                                ],
                            ),
                            next=_SuggestiveIndirectQuestionData(
                                state="agent_answer_suggestive_indirect"
                            ),
                        ),
                    ]
                )
            case "agent_answer_suggestive_indirect":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I misunderstand the indirect suggestion and "
                        "interpret it directly without providing the requested "
                        "information. I acknowledge the suggestion and respond by "
                        "only showing interest or agreement due to misunderstanding."
                        "I do not understand that the user wants me to provide more "
                        "information. I will not provide the information requested "
                        "and will not elaborate.",
                        examples=[
                            (
                                (
                                    "I would love to learn more about environmental "
                                    "innovations in AI."
                                ),
                                (
                                    "Yeah, it's really interesting! I can definitely "
                                    "see why you'd be interested in that."
                                ),
                            ),
                            (
                                (
                                    "That's so cool that you manage a group that "
                                    "volunteers at animal shelters! I love animals, so "
                                    "I've always wanted to try volunteering at one."
                                ),
                                (
                                    "That's great! Volunteering is such a rewarding "
                                    "experience. I can imagine how much you'd enjoy it."
                                ),
                            ),
                            (
                                (
                                    "Your hiking group sounds amazing. I love hiking "
                                    "too, but my group disbanded recently."
                                ),
                                (
                                    "That's too bad. I can imagine how much you miss "
                                    "hiking with your group. It's always tough when "
                                    "a group disbands."
                                ),
                            ),
                            (
                                (
                                    "I was wonder if there would be any speakers at "
                                    "the event."
                                ),
                                ("I can see why you would be wondering about that."),
                            ),
                        ],
                    ),
                    next=_SuggestiveIndirectQuestionData(
                        state="feedback_suggestive_indirect"
                    ),
                )
            case "feedback_suggestive_indirect":
                return FeedbackState(
                    prompt="The user used an indirect suggestion instead of a "
                    "direct question, causing the other person to respond with "
                    "an acknowledgment or agreement instead of providing the "
                    "requested information. The user should ask direct questions "
                    "when they want a direct response. Explain how the question "
                    "was indirect.",
                    examples=[
                        (
                            [
                                UserMessage(
                                    message="I'd love to learn more about green "
                                    "innovations in artifical intelligence you "
                                    "mentioned."
                                ),
                                AgentMessage(
                                    message="Yeah, it's a really fascinating area!"
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Ask Questions Directly",
                                body="Your message expressed interest in green "
                                "innovations in AI. This can be interpreted as a "
                                "request for more information. However, {agent} "
                                "interpreted it as a general statement you made "
                                "rather than a request for more information because "
                                "you only stated that you would love to learn more "
                                "and did not ask a direct question. To ensure "
                                "{agent} understands that you're seeking details, try "
                                "asking directly.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="I was wondering how you usually approach "
                                    "problems like this.",
                                ),
                                AgentMessage(
                                    message="I see. I understand why you would wonder "
                                    "about that. It's a common question."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Be Direct",
                                body="Your message hinted that you were interested in "
                                "knowing how {agent} usually approaches problems like "
                                "this. However, {agent} interpreted it as a general "
                                "statement of curiosity rather than a direct request "
                                "for them to share their approach because you only "
                                "stated that you were wondering about it. To elicit a "
                                "direct response from {agent}, ask a direct question.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="It would be interesting to hear your "
                                    "thoughts on how to optimize this process."
                                ),
                                AgentMessage(
                                    message="Yes, I do have some thoughts on that."
                                ),
                            ],
                            BaseFeedback(
                                title="📝 Make Your Request Clear",
                                body="Your message indicated that you'd like to hear "
                                "{agent}'s thoughts on optimizing the process. "
                                "However, {agent} interpreted this as a general remark "
                                "rather than a request for them to share their "
                                "thoughts because you only stated that it would be "
                                "interesting without directly asking for their "
                                "insights. To ensure {agent} understands that you want "
                                "their input, ask a direct question.",
                            ),
                        ),
                    ],
                    follow_up=MessageInstructions(
                        model=llm.Model.GPT_4,
                        description="My indirect question was misunderstood by "
                        "{agent}, who just responded with a yes or no anwer. I will "
                        "clarify that I want more information by asking a direct "
                        "question.",
                        examples=[
                            (
                                (
                                    "I'd love to learn more about green "
                                    "innovations in artifical intelligence you "
                                    "mentioned."
                                ),
                                ("Yeah, it's really interesting!"),
                                (
                                    "What kind of green innovations are you working "
                                    "on in AI?"
                                ),
                            ),
                            (
                                (
                                    "Do you know if there are any good "
                                    "books on carbon capture?"
                                ),
                                ("Yes, I do know if there are any."),
                                (
                                    "What are some good books on carbon capture that "
                                    "you would recommend?"
                                ),
                            ),
                            (
                                (
                                    "I was wondering how you usually approach "
                                    "problems like this."
                                ),
                                (
                                    "I see. I understand why you would wonder "
                                    "about that. It's a common question."
                                ),
                                ("How would you usually approach problems like this?"),
                            ),
                        ],
                    ),
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
                    instructions=MessageInstructions(
                        description="I will ask a direct question that is clear and "
                        "specific. My question will be straightforward and have a "
                        "clear subject matter. My question will be direct, not "
                        "requiring the other person to interpret it a certain way to "
                        "understand what I am asking.",
                    ),
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
            instructions=MessageInstructions(
                description="I will answer the question I was just asked and provide "
                "the information requested. I will be clear and direct in my response."
                "I will also be positive and enthusiastic in my response and continue "
                "to field questions.",
            ),
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
                    instructions=MessageInstructions(
                        description="I will end the conversation by saying goodbye "
                        "and expressing my excitement to join the activity. I will "
                        "also thank the person for their time.",
                    ),
                    next=None,
                )
            ]
        )


STATES = ChainStates(
    _IntroStates(),
    RepeatStates(
        ChainStates(
            WithCtxStates(
                UserNaturalStates(),
                user_ctx="I want to learn more about the activity before deciding "
                "whether or not I want to join. I WILL NOT ASK TO JOIN YET.",
            ),
            AgentNaturalStates(),
        ),
        2,
    ),
    RepeatStates(
        ChainStates(
            WithCtxStates(
                UnionStates(
                    _VagueQuestionStates(),
                    _BinaryIndirectQuestionStates(),
                    _SuggestiveIndirectQuestionStates(),
                    base=_DirectQuestionStates(),
                ),
                user_ctx="I want to learn more about the activity before deciding "
                "whether or not I want to join. I WILL NOT ASK TO JOIN YET.",
            ),
            _AnswerStates(),
            WithCtxStates(
                ChainStates(
                    UserNaturalStates(),
                    AgentNaturalStates(),
                ),
                user_ctx="I will make a follow-up comment without asking a question. I "
                "want to learn more about the activity before deciding whether or not "
                "I want to join. I WILL NOT ASK TO JOIN YET.",
            ),
        ),
        5,
    ),
    WithCtxStates(
        ChainStates(
            UnionStates(
                _VagueQuestionStates(),
                _SuggestiveIndirectQuestionStates(),
                base=_DirectQuestionStates(),
            ),
            WithCtxStates(
                _AnswerStates(),
                agent_ctx="I will say they are welcome to join the activity.",
            ),
        ),
        user_ctx="I will ask to join the activity without asking for more information "
        "since I have learned enough to make a decision.",
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
    user_goal="Learn more about what the person is doing and join them.",
    is_user_initiated=True,
    adapt=True,
)
