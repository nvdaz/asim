from typing import Literal

from api.schemas.conversation import AgentMessage, Feedback, UserMessage

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
                                "question is ambiguous and could be interpreted in "
                                "multiple ways.",
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
                    "examples on how the question was ambiguous. DO NOT provide "
                    "specific examples of how to clarify the question yet.",
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
                            Feedback(
                                title="🔍 Clarify Questions",
                                body='When you asked {agent}, "What is software made '
                                'of?", they were not sure what you meant because the '
                                "question was quite broad and could be interpreted in "
                                "different ways. You could have been asking about the "
                                "the programming languages or tools used to build "
                                "software, the components that make up software, the "
                                "software development process, or something else. "
                                "{agent} was unable to respond effectively because "
                                "your question was too vague. To avoid this confusion, "
                                "clearly specify what you want to know.",
                                follow_up="What programming languages are commonly "
                                "used to build software?",
                                explanation="This version of the question is more "
                                "specific and clear. It directly asks about a specific "
                                "aspect of software--the programming language--so "
                                "{agent} will know exactly the information you're "
                                "looking for.",
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
                            Feedback(
                                title="🔍 Be Specific",
                                body="Your question was vague and open-ended, making "
                                "it unclear what you were asking. {agent} was confused "
                                "because AI is used in many ways, so it was unclear "
                                "what you wanted to know. To ensure you get the "
                                "information you want, ask clear and specific "
                                "questions.",
                                follow_up="What are some ways that reinforcement "
                                "learning is being used to improve predictions for "
                                "climate change?",
                                explanation="This helps you ask questions that get you "
                                "the answers you’re looking for by being clear about "
                                "what you want to know.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="How should soccer teams approach their "
                                    "strategy in soccer when facing tough opposition?"
                                ),
                                AgentMessage(
                                    message="I'm not sure how to answer that. There "
                                    "are many ways aspects to strategy."
                                ),
                            ],
                            Feedback(
                                title="🔍 Clarify Your Question",
                                body="You asked a question that was broad and lacked "
                                "specificity, making it unclear what you were asking."
                                "{agent} was unsure how to respond because it was not "
                                "clear which aspect of soccer strategy you were "
                                "interested in. You may have been asking about "
                                "tactics, team selection, training, or something else. "
                                "To get {agent} to provide the information you want, "
                                "ask a clear and specific question.",
                                follow_up="What formation do you think is most "
                                "effective against a strong opponent?",
                                explanation="This new question narrows down the topic "
                                "of soccer strategy to focus on team formation, "
                                "providing {agent} with a clear direction for their "
                                "response.",
                            ),
                        ),
                    ],
                    follow_up="I just asked a vague question that was unclear and "
                    "caused confusion. I need to clarify the vague question, so the "
                    "other person can understand what I am asking.",
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
                                "will either ask if the agent knows something or if "
                                "they are willing to do something. Even though my "
                                "question is phrased as a yes-or-no question, it will "
                                "imply that I want more information or action. My "
                                "question cannot be answered with a simple yes or no.",
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
                    prompt="The user used a yes-or-no question which could be "
                    "interpreted as either a yes or no question or as a request for "
                    "information. The other person responded with a yes or no answer, "
                    "which may not have provided the information the user was looking "
                    "for. The user should ask direct questions when they want a direct "
                    "response. Carefully explain how the question could be interpreted "
                    "either as a yes or no question or as a request for information.",
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
                            Feedback(
                                title="📝 Use Direct Questions",
                                body="{agent} confirmed that they knew if there were "
                                "any good books on carbon capture but did not provide "
                                "any specific recommendations. You used the phrase "
                                "'Do you know', which can be interpreted as either "
                                "asking if {agent} is aware of the existence of such "
                                "books or if they have any recommendations. The "
                                "question was ambiguous, leading {agent} to only "
                                "confirm their knowledge without providing any "
                                "specific information. To encourage {agent} to share "
                                "book recommendations, ask a direct question.",
                                follow_up="What are some good books on carbon capture "
                                "that you would recommend?",
                                explanation="This version of the question directly "
                                "asks {agent} to share their recommendations, making "
                                "it clear that you want specific book suggestions and "
                                "not just confirmation that they know of such books.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Would you be able to tell me more about "
                                    "the environmental impact of oil spills on coral "
                                    "reefs?"
                                ),
                                AgentMessage(
                                    message=(
                                        "Yes, I can tell you more about their impact "
                                        "on the environment. I have studied them for "
                                        "15 years, so I have a lot of knowledge on the "
                                        "topic."
                                    ),
                                ),
                            ],
                            Feedback(
                                title="📝 Be Direct",
                                body="You asked {agent} if they would be able to tell "
                                "you more about the environmental impact of oil "
                                "spills on coral reefs. Because you used the phrase "
                                "'Would you be able to', the question could be "
                                "interpreted as asking if {agent} is capable of "
                                "discussing oil spills or if they are willing to "
                                "provide more information. {agent} confirmed their "
                                "ability but didn't provide the specifics you were "
                                "looking for. The phrase 'Would you be able to' was "
                                "taken literally, leading to them only confirming "
                                "their knowledge without providing specific details. "
                                "If you want detailed information, ask {agent} "
                                "directly.",
                                follow_up="How do oil spills affect coral reefs?",
                                explanation="This version of the question directly "
                                "asks {agent} to share their knowledge, making it "
                                "clear that you're seeking detailed information and "
                                "not just confirmation of their ability to discuss "
                                "the topic.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Would you mind telling me more about the "
                                    "club's activities?"
                                ),
                                AgentMessage(
                                    message="Sure, I can tell you more about that."
                                ),
                            ],
                            Feedback(
                                title="📝 Ask Direct Questions",
                                body="You asked {agent} if they would mind telling you "
                                "more about the club's activities. This question could "
                                "be interpreted as asking if {agent} is willing to "
                                "provide more information or if they are capable of "
                                "doing so depending on how the phrase 'Would you mind' "
                                "is interpreted. {agent} interpreted it literally, "
                                "leading to them only confirming their willingness to "
                                "share information without providing specific details. "
                                "Try asking {agent} a direct question if you want "
                                "specific information.",
                                follow_up="What are some activities that new members "
                                "can participate in to get involved with the club?",
                                explanation="This version of the question directly "
                                "asks {agent} to share information about the club's "
                                "activities, making it clear that you're seeking "
                                "specific details and not just confirmation that they "
                                "are willing to provide information.",
                            ),
                        ),
                    ],
                    follow_up="I will clarify the indirect question I asked "
                    "which received a yes or no answer. I will ask a direct "
                    "question to get the information I want. My direct question "
                    "will not start with 'could'.",
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
                    prompt="The user used an indirect suggestion to imply they "
                    "wanted more information. This indirect suggestion could be "
                    "interpreted either literally as a statement of interest or "
                    "as a request for more information. The other person responded "
                    "with an acknowledgment or agreement instead of providing the "
                    "requested information. If the user wants a direct response, "
                    "they should ask direct questions. Carefully explain how the "
                    "indirect suggestion was misunderstood.",
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
                            Feedback(
                                title="📝 Ask Questions Directly",
                                body="You expressed interest in green innovations in "
                                "AI by saying you'd love to learn more. This could be "
                                "interpreted as a statement of interest that doesn't "
                                "require a response or as a request for more "
                                "information. {agent} interpreted it as a statement "
                                "of interest rather than a request for more "
                                "information. If you want {agent} to provide more "
                                "details, ask a direct question.",
                                follow_up="What are some green innovations in AI that "
                                "you find most exciting?",
                                explanation="This version of the question directly "
                                "asks {agent} to share their thoughts on green "
                                "innovations in AI, making it clear that you want "
                                "specific information about the topic.",
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
                            Feedback(
                                title="📝 Be Direct",
                                body="Your message stated that you were wondering "
                                "how {agent} usually approaches problems like this, "
                                "hinting that you wanted more information. However, "
                                "{agent} interpreted it as a statement of curiosity "
                                "rather than a direct request for them to share their "
                                "approach because you only stated that you were "
                                "wondering about it, not that you wanted them to "
                                "share their approach. If you want a direct response, "
                                "ask a direct question.",
                                follow_up="How would you usually approach problems "
                                "like this?",
                                explanation="This version of the question directly "
                                "asks {agent} to share their approach, making it clear "
                                "that you want them to provide specific information "
                                "about their problem-solving process, not just "
                                "acknowledge your curiosity.",
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
                            Feedback(
                                title="📝 Make Your Request Clear",
                                body="Telling {agent} that it would be interesting to "
                                "hear their thoughts on optimizing the process could "
                                "either be interpreted as a statement of interest "
                                "or as a request for them to share their insights. "
                                "{agent} interpreted it as a statement of interest "
                                "and responded positively without providing the "
                                "information you were looking for. If you want {agent} "
                                "to share their insights, ask a direct question.",
                                follow_up="What are your thoughts on optimizing this "
                                "process?",
                                explanation="This version of the question directly "
                                "asks {agent} to share their insights, making it clear "
                                "that you're seeking specific information about how "
                                "to optimize the process.",
                            ),
                        ),
                    ],
                    follow_up="My indirect question was misunderstood by "
                    "{agent}, who just responded with a yes or no anwer. I will "
                    "clarify that I want more information by asking a direct "
                    "question.",
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
