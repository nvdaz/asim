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
                    instructions=MessageInstructions(
                        description="I will start the conversation and mention that I "
                        "have heard the other person has worked with a client that I "
                        "would like to discuss. I will ask if this is true."
                    ),
                    next=_IntroData(state="user_greet"),
                )
            case "user_greet":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                description="I will greet the person and confirm that "
                                "I have indeed worked with the client they mentioned. "
                                "I will tell them that I am happy to answer any "
                                "questions they have about the client."
                            ),
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
                    instructions=MessageInstructions(
                        description="I will ask a question about the client. I will "
                        "focus on asking questions about the client that are general "
                        "and open-ended, avoiding trivial details like dates, times, "
                        "or locations.",
                    ),
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
                            instructions=MessageInstructions(
                                description="I will provide a vague answer that can be "
                                "interpreted in multiple ways. I know the answer "
                                "exactly but will only answer the question on a "
                                "surface level without providing any specific details.",
                                examples=[
                                    (
                                        (
                                            "What should I wear to the event? Will it "
                                            "be formal?"
                                        ),
                                        ("Something nice would work."),
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
                                            "relevant subjects. There will be "
                                            "something for everyone."
                                        ),
                                    ),
                                ],
                            ),
                            next=_VagueAnswerData(state="agent_react_vague"),
                        ),
                    ]
                )
            case "agent_react_vague":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will react to the vague answer by bluntly "
                        "expressing that their answer was not helpful and asking "
                        "for more specific details. My blunt tone may come across as "
                        "rude, but it is necessary to get the information I need.",
                        examples=[
                            (
                                ("You should wear something nice to the event."),
                                (
                                    "That's not really helpful. If you could specify "
                                    "a dress code like 'formal' or 'casual', I "
                                    "would appreciate that."
                                ),
                            ),
                            (
                                ("We have some great speakers lined up."),
                                (
                                    "That doesn’t tell me anything. Can you give me "
                                    "the names or more details about the speakers?"
                                ),
                            ),
                            (
                                (
                                    "There will be something to eat for everyone. "
                                    "There will be a variety of options."
                                ),
                                (
                                    "Can you provide more details? I have dietary "
                                    "restrictions, so I need to figure out if I should "
                                    "eat beforehand."
                                ),
                            ),
                        ],
                    ),
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
                    follow_up="The vague answer I provided was not helpful to {agent}. "
                    "I will clarify my answer and provide more specific details.",
                    examples=[
                        (
                            [
                                AgentMessage(
                                    message="What's the dress code for the event?"
                                ),
                                UserMessage(message="Something nice would work."),
                                AgentMessage(
                                    message="That's not really helpful. If you could "
                                    "specify a dress code like 'formal' or 'business "
                                    "casual', I would appreciate that."
                                ),
                            ],
                            Feedback(
                                title="📝 Be Clear and Specific",
                                body="Your response did not answer the question "
                                "clearly. {agent} wanted to know the dress code, "
                                "but your answer did not specifically address that. "
                                '"Nice" could mean different things depending on '
                                "the context, like formal or business casual. "
                                "Try to clarify your answer by elaborating on the "
                                "dress code and using a well-known dress code.",
                                follow_up="Sorry, the dress code is business casual. ",
                                explanation="This answer clarifies that the dress code "
                                "is business casual, which is a well-known dress code.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="Who will be speaking at the event?"
                                ),
                                UserMessage(
                                    message="That doesn’t tell me anything. Can you "
                                    "give me the names or more details about the "
                                    "speakers?",
                                ),
                                AgentMessage(message="Ok but who are they?"),
                            ],
                            Feedback(
                                title="📝 Be Clear and Specific",
                                body="You responded in a way that did not clearly "
                                "answer the question {agent} asked. {agent} wanted to "
                                "know who would be speaking at the event, but your "
                                "answer only specified that the speakers were "
                                "great. Mention who the speakers are instead of "
                                "to answer the question.",
                                follow_up="We will have the CEO of the company along "
                                "with a researcher who works at Google.",
                                explanation="This answer clarifies who the speakers "
                                "are rather than just saying that the speakers are "
                                "great.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="What type of food will be served?"
                                ),
                                UserMessage(
                                    message="There will be something to eat for "
                                    "everyone. There will be a variety of options."
                                ),
                                AgentMessage(
                                    message="Can you provide more details? I have "
                                    "dietary restrictions, so I need to figure out if "
                                    "I should eat beforehand."
                                ),
                            ],
                            Feedback(
                                title="📝 Be Clear and Specific",
                                body="Your response did not answer {agent}'s question. "
                                "{agent} wanted to know what type of food would be "
                                "served, but you only mentioned that you would find "
                                "something they would like. Provide more details by "
                                "describing the types of food that will be served.",
                                follow_up="We will be barbecuing hot dogs and "
                                "hamburgers. There will also be corn on the cob and "
                                "veggie burgers for vegetarians.",
                                explanation="This answer specifies exactly what "
                                "types of food will be served instead of vaguely "
                                "mentioning that they will find something they "
                                "would like.",
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
                            instructions=MessageInstructions(
                                description="I will answer the question using "
                                "figurative language that is not meant to be taken "
                                "literally. My answer will be creative and "
                                "imaginative, using language that is not "
                                "straightforward.",
                                examples=[
                                    (
                                        ("How do you feel about the new project?"),
                                        (
                                            "I think the new project is a breath of "
                                            "fresh air. A blank canvas waiting to be "
                                            "painted."
                                        ),
                                    ),
                                    (
                                        (
                                            "What do you think about the team's "
                                            "progress?"
                                        ),
                                        (
                                            "The team is progressing like a well-oiled "
                                            "machine. We're firing on all cylinders."
                                        ),
                                    ),
                                    (
                                        (
                                            "How would you describe the client's "
                                            "approach?"
                                        ),
                                        (
                                            "The client's approach is like a "
                                            "rollercoaster. It's full of ups and "
                                            "downs, "
                                            "but it's always exciting."
                                        ),
                                    ),
                                ],
                            ),
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                        UserOption(
                            instructions=MessageInstructions(
                                description="I will answer the question using a touch "
                                "of figurative language. My answer will be mostly "
                                "literal but will include a hint of figurative "
                                "language to make it more interesting.",
                                examples=[
                                    (
                                        ("How do you feel about the new project?"),
                                        (
                                            "I'm excited to start anew. I can't wait "
                                            "to dive in and see where it takes us."
                                        ),
                                    ),
                                    (
                                        (
                                            "What do you think about the team's "
                                            "progress?"
                                        ),
                                        (
                                            "The team is making great strides. We're "
                                            "moving forward at a steady pace."
                                        ),
                                    ),
                                    (
                                        (
                                            "How would you describe the client's "
                                            "approach?"
                                        ),
                                        (
                                            "The client's approach is unique. They "
                                            "tend to think outside the box and enjoy "
                                            "taking risks."
                                        ),
                                    ),
                                ],
                            ),
                            next=_FigurativeData(state="agent_react_figurative"),
                        ),
                    ]
                )
            case "agent_react_figurative":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will interpret the answer literally and respond "
                        "as if the figurative language was meant to be taken "
                        "seriously. I will ignore the creative and imaginative "
                        "language used in the answer and respond in a direct and "
                        "literal manner. I do not understand the message used "
                        "figurative language, so will respond as if it was literal."
                        "I will ask {user} to clarify what they meant if needed, "
                        "without acknowledging the figurative language.",
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
                                    "Why is the team on fire? We need to ensure "
                                    "everyone is safe and following proper procedures."
                                ),
                            ),
                            (
                                ("The client's approach is a breath of fresh air."),
                                (
                                    "Why would the client's approach be like fresh "
                                    "air? Can you explain what you mean by that?"
                                ),
                            ),
                        ],
                    ),
                    next=_FigurativeData(state="feedback_figurative"),
                )

            case "feedback_figurative":
                return FeedbackState(
                    prompt="The latest message needs improvement as it contains "
                    "figurative language, which can be misinterpreted by some "
                    "individuals. Provide feedback on how their message could have "
                    "been clearer and more direct. Explain how the figurative "
                    "language could be confusing and describe specifically how the "
                    "figurative language was misinterpreted as literal.",
                    follow_up="My previous answer using figurative language was "
                    "misinterpreted by {agent}. I will clarify the figurative "
                    "language I used and provide a more direct response.",
                    examples=[
                        (
                            [
                                AgentMessage(
                                    message="What do you think about the team's "
                                    "progress?"
                                ),
                                UserMessage(
                                    message="The team is making great strides. We're "
                                    "moving forward at a steady pace."
                                ),
                                AgentMessage(
                                    message="Why do you think the team is moving "
                                    "forward at a steady pace? We're not running a "
                                    "race; we're building a project."
                                ),
                            ],
                            Feedback(
                                title="🎭 Avoid Figurative Language",
                                body="You used a metaphor to describe the team's "
                                "progress as 'moving forward at a steady pace.' "
                                "{agent} misunderstood the metaphor and thought you "
                                "were talking about the team literally moving forward "
                                "at a steady pace, like in a race. Try to avoid "
                                "figurative language to prevent confusion.",
                                follow_up="Sorry, I meant that the team is making "
                                "great progress and working hard.",
                                explanation="This answer clarifies that the team is "
                                "making progress and working hard using direct "
                                "language.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="How would you describe the client's "
                                    "approach?"
                                ),
                                UserMessage(
                                    message="The client's approach is unique. They "
                                    "tend to think outside the box and enjoy taking "
                                    "risks."
                                ),
                                AgentMessage(
                                    message="What box are they thinking outside of? "
                                    "Do they have a thinking box in their office?"
                                ),
                            ],
                            Feedback(
                                title="🎭 Avoid Confusing Idioms",
                                body="You used the idiom 'think outside the box' to "
                                "describe the client's approach. {agent} misunderstood "
                                "the idiom and thought you were referencing an actual "
                                "box that the client thinks outside of. Try to avoid "
                                "idioms to prevent confusion.",
                                follow_up="Sorry, I meant that the client has an "
                                "innovative approach and is willing to take risks.",
                                explanation="This answer clarifies the meaning of the "
                                "idiom you used. It describes the client's approach "
                                "using direct language.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="What do you think about the new project?"
                                ),
                                UserMessage(
                                    message="I think the new project is like a blank "
                                    "canvas waiting to be painted."
                                ),
                                AgentMessage(
                                    message="Why would the project be like a blank "
                                    "canvas waiting to be painted? We are marketing "
                                    "gurus, not artists."
                                ),
                            ],
                            Feedback(
                                title="🌀 Avoid Confusing Similies",
                                body="You used a simile to describe the new project as "
                                "'a blank canvas waiting to be painted.' {agent} "
                                "misunderstood the simile, thinking you were talking "
                                "about an actual canvas and painting instead of the "
                                "project's potential, leading to confusion. Try to "
                                "avoid similes to prevent confusion.",
                                follow_up="Sorry, I meant that the new project is full "
                                "of possibilities and opportunities.",
                                explanation="This answer clarifies the meaning of the "
                                "simile you used. It describes the new project using "
                                "direct language.",
                            ),
                        ),
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
                            instructions=MessageInstructions(
                                description="I will answer the question using sarcasm "
                                "or irony to be humorous. I will use language that is "
                                "the opposite of what I mean to be funny. This is "
                                "important because {agent} loves sarcasm and has a "
                                "great sense of humor. If I do not use sarcasm, "
                                "{agent} will be disappointed and think I am boring "
                                "because they specifically asked for sarcasm.",
                                examples=[
                                    (
                                        ("Any advice on how to handle the client?"),
                                        (
                                            "Oh, they love it when you show up late. "
                                            "It shows them you're in control."
                                        ),
                                    ),
                                    (
                                        (
                                            "What do you think about the team's "
                                            "communication?"
                                        ),
                                        (
                                            "Just keep doing what you're doing. It's "
                                            "working wonders."
                                        ),
                                    ),
                                    (
                                        ("Do you think we should change our approach?"),
                                        (
                                            "Oh, definitely. Change is always a good "
                                            "thing. It's not like the current approach "
                                            "is working or anything."
                                        ),
                                    ),
                                ],
                            ),
                            next=_SarcasticData(state="agent_react_sarcastic"),
                        ),
                    ]
                )
            case "agent_react_sarcastic":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will interpret the message literally. I know "
                        "{user} never uses sarcasm and always means exactly what they "
                        "say. I will respond addressing the literal meaning of the "
                        "message.",
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
                                    "But it isn't working wonders. I was hoping for "
                                    "some constructive feedback on how to improve our "
                                    "team communication."
                                ),
                            ),
                            (
                                (
                                    "Artificial intelligence is just a fad. We are "
                                    "still looking for any practical applications. "
                                    "It's not like it's the future or anything."
                                ),
                                (
                                    "I disagree. AI is the future and has many "
                                    "practical applications. I was thinking of using "
                                    "it for the next project."
                                ),
                            ),
                        ],
                    ),
                    next=_SarcasticData(state="feedback_sarcastic"),
                )
            case "feedback_sarcastic":
                return FeedbackState(
                    prompt="The latest message needs improvement as it uses "
                    "sarcasm, which can be misinterpreted by some individuals. "
                    "Provide feedback on how their message could have been clearer "
                    "and more direct. Explain how the sarcasm could be confusing.",
                    follow_up="My previous answer used sarcasm that was misinterpreted "
                    "by {agent}. I will apologize for using using sarcasm, which was "
                    "confusing and clarify what I meant with a more direct response.",
                    examples=[
                        (
                            [
                                AgentMessage(
                                    message="Any advice on how to handle the client?"
                                ),
                                UserMessage(
                                    message="The bosses love it when you show up late."
                                ),
                                AgentMessage(
                                    message="That's strange. Why would they love that? "
                                    "It's unprofessional and disrespectful."
                                ),
                            ],
                            Feedback(
                                title="🃏 Avoid Sarcasm",
                                body="Your response was sarcastic as you mentioned "
                                "that the bosses love it when you show up late, which "
                                "is the opposite of the truth. {agent} thought you "
                                "were being serious and responded accordingly. Try to "
                                "avoid sarcasm to prevent confusion.",
                                follow_up="Sorry, I was being sarcastic. The bosses "
                                "don't actually love it when you show up late. "
                                "Punctuality is extremely important.",
                                explanation="This answer clarifies the confusion "
                                "caused by your sarcastic response. It directly "
                                "explains the importance of punctuality.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="What do you think about the team's "
                                    "communication?"
                                ),
                                UserMessage(
                                    message="Just keep doing what you're doing. It's "
                                    "working wonders."
                                ),
                                AgentMessage(
                                    message="But it isn't working wonders. I was "
                                    "hoping for some constructive feedback on how to "
                                    "improve our team communication."
                                ),
                            ],
                            Feedback(
                                title="🃏 Avoid Sarcasm",
                                body="You used sarcasm in your response by saying that "
                                "the current approach is working wonders, when in "
                                "reality, it isn't. {agent} thought you were being "
                                "serious and was confused by your response. Try to "
                                "avoid sarcasm to prevent misunderstandings.",
                                follow_up="Sorry, my previous response was sarcastic. "
                                "I think we should consider changing our approach to "
                                "improve team communication.",
                                explanation="This answer clarifies the confusion "
                                "caused by your sarcastic response. It directly "
                                "explains that you think the team's communication "
                                "needs improvement.",
                            ),
                        ),
                        (
                            [
                                AgentMessage(
                                    message="Do you think we should integrate AI into "
                                    "our workflow?"
                                ),
                                UserMessage(
                                    message="Artificial intelligence is just a fad. We "
                                    "are still looking for any practical applications "
                                    "It's not like it's the future or anything."
                                ),
                                AgentMessage(
                                    message="I disagree. AI has many practical "
                                    "applications. That's why I was thinking of using "
                                    "it in our workflow for the next project."
                                ),
                            ],
                            Feedback(
                                title="🃏 Avoid Sarcasm",
                                body="You sarcastically suggested that AI is a fad, "
                                "while you actually believe it has many practical "
                                "applications. {agent} thought you were being serious "
                                "and was confused by your response. They interpreted "
                                "your sarcasm as a genuine opinion instead of an "
                                "ironic one. Try to avoid sarcasm to prevent "
                                "misunderstandings.",
                                follow_up="Sorry, I was being sarcastic. I think AI "
                                "has many practical applications and has a lot of "
                                "potential for the future. Using it in your workflow "
                                "is a great idea.",
                                explanation="This response clarifies the confusion "
                                "caused by your sarcastic response. It directly "
                                "explains your opinion on using AI in {agent}'s "
                                "workflow.",
                            ),
                        ),
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
                            instructions=MessageInstructions(
                                description="I will provide a clear answer. My "
                                "response will be straightforward and address the "
                                "question directly.",
                            ),
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
                    instructions=MessageInstructions(
                        description="I will say that I have no more questions about "
                        "the client. I will thank the person for their time and say "
                        "goodbye."
                    ),
                    next=_EndData(state="user_goodbye"),
                )
            case "user_goodbye":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                description="I will say goodbye and end the "
                                "conversation."
                            ),
                            next=None,
                        ),
                    ]
                )


STATES = ChainStates(
    _IntroStates(),
    RepeatStates(
        WithCtxStates(
            ChainStates(
                AgentNaturalStates(),
                UserNaturalStates(),
            ),
            user_ctx="I will answer any questions about the client now.",
            agent_ctx="I will ask any questions I have about the client now.",
        ),
        2,
    ),
    RepeatStates(
        ChainStates(
            WithCtxStates(
                _AskStates(),
                agent_ctx="I want to learn more about the client and receive "
                "more information.",
            ),
            UnionStates(
                _VagueAnswerStates(),
                _FigurativeStates(),
                _SarcasticStates(),
                base=_DirectAnswerStates(),
            ),
            WithCtxStates(
                ChainStates(
                    AgentNaturalStates(),
                    UserNaturalStates(),
                ),
                agent_ctx="I will make a follow-up comment without asking a "
                "new question. I want to learn more about the client and "
                "receive more information. I WILL NOT END THE CONVERSATION.",
            ),
        ),
        5,
    ),
    _EndStates(),
)

SCENARIO_SEED = LevelConversationScenarioSeed(
    user_perspective=(
        "A colleague reaches out to you to discuss a specific client who you have "
        "worked with before and asks for your advice [pick a name for the client]."
    ),
    agent_perspective=(
        "You reach out to a colleague to discuss a client who they have worked with "
        "before and ask for their advice."
    ),
    user_goal=(
        "Discuss the client with your colleague and provide them with helpful advice."
    ),
    is_user_initiated=False,
    adapt=True,
)
