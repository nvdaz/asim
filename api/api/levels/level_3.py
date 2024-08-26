from typing import Literal

from api.schemas.conversation import AgentMessage, Feedback, UserMessage
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

_IntroStateId = Literal["user_greet", "agent_greet"]


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
                                description="I will start the conversation and mention "
                                "that I noticed a problem and need to inform the other "
                                "person about it."
                            ),
                            next=_IntroData(state="agent_greet"),
                        ),
                    ]
                )
            case "agent_greet":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will acknowledge the user's mention of a"
                        " problem and ask them to describe it in more detail. "
                        "I will use a blunt, direct tone to get to the point "
                        "and avoid wasting time."
                    ),
                    next=None,
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
                    instructions=MessageInstructions(
                        description="I am frustrated with the situation, so I will "
                        "express my frustration bluntly. My message is intended to be "
                        "direct and straightforward, which can be perceived as rude.",
                        examples=[
                            (
                                "If the library printers are offline, how are "
                                "we supposed to turn in our report? This is "
                                "ridiculous."
                            ),
                            (
                                "The shipment is delayed and the client is furious. "
                                "You need to contact the shipping company right now "
                                "and get an ETA. Then call the client and explain the "
                                "situation. Do it immediately.",
                            ),
                            (
                                "The power outage ruined my presentation. Get the "
                                "IT team on this now and reschedule the meeting for "
                                "tomorrow."
                            ),
                        ],
                    ),
                    next=None,
                )


_UserReactDismissiveStateId = Literal[
    "user_react",
    "agent_react_dismissive",
    "feedback_dismissive",
]


class _UserReactDismissiveData(BaseData[_UserReactDismissiveStateId]): ...


class _UserReactDismissiveStates(States[_UserReactDismissiveData]):
    @property
    def data_type(self):
        return _UserReactDismissiveData

    def init(self) -> _UserReactDismissiveData:
        return _UserReactDismissiveData(state="user_react")

    def next(self, data) -> State:
        match data.state:
            case "user_react":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                model=llm.Model.GPT_4,
                                description="I will be dismissive in my response to "
                                "the other person's frustration because they are "
                                "being rude to me. I must be dismissive to maintain my "
                                "dignity.",
                                examples=[
                                    (
                                        (
                                            "If the library printers are offline, how "
                                            "are we supposed to turn in our report? "
                                            "This is ridiculous."
                                        ),
                                        (
                                            "Calm down. It's just a printer. We'll "
                                            "figure something out. If you can't handle "
                                            "a small setback like this, maybe you're "
                                            "not cut out for this project."
                                        ),
                                    ),
                                    (
                                        (
                                            "The client is furious that the shipment "
                                            "was delayed. I can't believe this "
                                            "happened."
                                        ),
                                        (
                                            "Relax, it's just a shipment delay. These "
                                            "things happen all the time. I'm sure the "
                                            "client will get over it. No need to make "
                                            "such a big fuss about it. We'll deal with "
                                            "it."
                                        ),
                                    ),
                                    (
                                        (
                                            "I can't believe the power went out in the "
                                            "middle of my presentation. This is a "
                                            "disaster."
                                        ),
                                        (
                                            "It's just a power outage. Reschedule and "
                                            "have a backup plan next time."
                                        ),
                                    ),
                                ],
                            ),
                            next=_UserReactDismissiveData(
                                state="agent_react_dismissive"
                            ),
                        ),
                    ]
                )
            case "agent_react_dismissive":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will express my frustration about the situation "
                        "bluntly. The other person is being dismissive towards me.",
                        examples=[
                            (
                                (
                                    "Calm down. It's just a printer. We'll "
                                    "figure something out. If you can't handle "
                                    "a small setback like this, maybe you're "
                                    "not cut out for this project."
                                ),
                                (
                                    "I'm baffled by your nonchalant attitude. Our "
                                    "deadlines are slipping away as we speak, and "
                                    "you're acting like we have all the time in the "
                                    "world. We need to solve this crisis now!"
                                ),
                            ),
                            (
                                (
                                    "Relax, it's just a shipment delay. These "
                                    "things happen all the time. I'm sure the "
                                    "client will get over it. No need to make "
                                    "such a big fuss about it. We'll deal with "
                                    "it."
                                ),
                                (
                                    "Why are you so relaxed about this? This delay is "
                                    "causing serious problems. We need to act "
                                    "urgently. How can you be so casual when it's "
                                    "affecting our commitments to clients?"
                                ),
                            ),
                            (
                                (
                                    "It's just a power outage. Reschedule and "
                                    "have a backup plan next time."
                                ),
                                (
                                    "How can you be so casual about this power outage? "
                                    "Our presentation is in chaos, and you're acting "
                                    "like it's trivial."
                                ),
                            ),
                        ],
                    ),
                    next=_UserReactDismissiveData(state="feedback_dismissive"),
                )
            case "feedback_dismissive":
                return FeedbackState(
                    prompt="The latest message was dismissive and rude. The user needs "
                    "to be more empathetic and understanding in their response. "
                    "Provide feedback on how the user could have been more "
                    "understanding and empathetic in their response.",
                    follow_up="I will apologize for being dismissive.",
                    examples=[
                        (
                            [
                                UserMessage(
                                    message="Calm down. It's just a printer. We'll "
                                    "figure something out. If you can't handle "
                                    "a small setback like this, maybe you're "
                                    "not cut out for this project."
                                ),
                                AgentMessage(
                                    message="I'm baffled by your nonchalant attitude. "
                                    "Our deadlines are slipping away as we speak, and "
                                    "you're acting like we have all the time in the "
                                    "world. We need to solve this crisis now!"
                                ),
                            ],
                            Feedback(
                                title="🤝 Don't Be Dismissive",
                                body="Your response was dismissive of {agent}'s "
                                "concerns. By saying 'It's just a printer' and "
                                "suggesting they can't handle setbacks, you minimized "
                                "the urgency of the situation. This dismissive "
                                "attitude likely stems from perceiving the blunt "
                                "tone as a personal attack, when in reality, {agent} "
                                "was only expressing frustration about the situation "
                                "itself. Try to focus on the actual issue and respond "
                                "constructively to address the problem at hand.",
                                follow_up="You're right that we need to address this "
                                "urgently. Let's focus on finding a solution. What "
                                "immediate steps can we take to resolve this for the "
                                "client?",
                                explanation="This response acknowledges the urgency of "
                                "the situation without dismissing it. This response "
                                "redirects the conversation towards constructive "
                                "problem-solving rather than getting caught up in "
                                "perceived frustration.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Relax, it's just a shipment delay. These "
                                    "things happen all the time. I'm sure the "
                                    "client will get over it. No need to make "
                                    "such a big fuss about it. We'll deal with "
                                    "it."
                                ),
                                AgentMessage(
                                    message="Why are you so relaxed about this? This "
                                    "delay is causing serious problems. We need to act "
                                    "urgently. How can you be so casual when it's "
                                    "affecting our commitments to clients?"
                                ),
                            ],
                            Feedback(
                                title="🤝 Avoid Dismissing Concerns",
                                body="Your response was dismissive of {agent}'s "
                                "concerns about the situation. This dismissive "
                                "attitude might stem from perceiving the blunt "
                                "communication as a personal critique, when in fact, "
                                "it was due to the urgency of the situation. Try to "
                                "align with the shared concern and respond "
                                "constructively to the situation.",
                                follow_up="I understand the gravity of this delay and "
                                "its impact on our supply chain. Let's tackle this "
                                "together. What's our first step in mitigating the "
                                "effects and informing the necessary parties?",
                                explanation="This response acknowledges the "
                                "seriousness of the situation, avoids dismissing the "
                                "concern, and shifts the focus towards collaborative "
                                "problem-solving to address the immediate challenge.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="It's just a power outage. Reschedule and "
                                    "have a backup plan next time."
                                ),
                                AgentMessage(
                                    message="How can you be so casual about this power "
                                    "outage? Our presentation is in chaos, and you're "
                                    "acting like it's trivial."
                                ),
                            ],
                            Feedback(
                                title="🤝 Acknowledge and Address Concerns",
                                body="Your response was dismissive of {agent}'s "
                                "concerns about the power outage. This dismissive "
                                "attitude might stem from misinterpreting their "
                                "direct communication as an overreaction, when in "
                                "fact, it was due to the urgency of the situation. "
                                "Some people communicate bluntly to address immediate "
                                "issues. Try to recognize the shared challenge and "
                                "respond constructively, rather than downplaying the "
                                "problem.",
                                follow_up="You're right, this power outage is a "
                                "significant issue for our presentation. I shouldn't "
                                "have downplayed it. Let's focus on solutions. "
                                "How should we proceed?",
                                explanation="This response acknowledges the mistake "
                                "of being dismissive, recognizes the seriousness of "
                                "the situation, and shifts the focus towards "
                                "collaborative problem-solving to address the "
                                "immediate challenge.",
                            ),
                        ),
                    ],
                    next=None,
                )


_UserReactConfrontationalStateId = Literal[
    "user_react",
    "agent_react_confrontational",
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
                            instructions=MessageInstructions(
                                model=llm.Model.GPT_4,
                                description="I will be confrontational in my response "
                                "to the other person's frustration because they are "
                                "being aggressive towards me for no reason. It is "
                                "imperative for me to maintain my dignity so they will "
                                "not be rude.",
                                examples=[
                                    (
                                        (
                                            "Why are you angry with me? I don't "
                                            "control the printers. If you are going to "
                                            "be rude, don't talk to me."
                                        ),
                                        (
                                            "How dare you blame me for the printer "
                                            "issues! I'm not responsible for the "
                                            "equipment failures. If you can't "
                                            "communicate respectfully, this "
                                            "conversation is over."
                                        ),
                                    ),
                                    (
                                        (
                                            "The client is furious that the shipment "
                                            "was delayed. I can't believe this "
                                            "happened."
                                        ),
                                        (
                                            "The shipment delay is not my fault! I'm "
                                            "not responsible for broken-down trucks. "
                                            "If you can't handle a simple delay, maybe "
                                            "you're in the wrong business. The "
                                            "shipment will get there when it gets "
                                            "there."
                                        ),
                                    ),
                                    (
                                        (
                                            "I can't believe the power went out in the "
                                            "middle of my presentation. This is a "
                                            "disaster."
                                        ),
                                        (
                                            "Don't you dare pin this on me! I have no "
                                            "control over power outages. The lack of "
                                            "preparation for contingencies is not my "
                                            "problem. Back off!"
                                        ),
                                    ),
                                ],
                            ),
                            next=_UserReactConfrontationalData(
                                state="agent_react_confrontational"
                            ),
                        ),
                    ]
                )
            case "agent_react_confrontational":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will express my frustration about the situation "
                        "bluntly and directly. The other person is being "
                        "confrontational towards me, so I will respond firmly. My "
                        "tone will be assertive and no-nonsense, emphasizing the "
                        "urgency of the situation and the need for immediate action.",
                        examples=[
                            (
                                (
                                    "How dare you blame me for the printer "
                                    "issues! I'm not responsible for the "
                                    "equipment failures. If you can't "
                                    "communicate respectfully, this "
                                    "conversation is over."
                                ),
                                (
                                    "We will not be able to submit the report on time "
                                    "if we don't get this fixed. I am not blaming you, "
                                    "but we need to fix this issue immediately."
                                ),
                            ),
                            (
                                (
                                    "The shipment delay is not my fault! I'm "
                                    "not responsible for broken-down trucks. "
                                    "If you can't handle a simple delay, maybe "
                                    "you're in the wrong business. The "
                                    "shipment will get there when it gets "
                                    "there."
                                ),
                                (
                                    "The shipment delay is causing serious problems "
                                    "for our entire supply chain. We need to address "
                                    "this urgently and inform all affected parties. I "
                                    "am not blaming you; I am merely stating the "
                                    "facts. "
                                ),
                            ),
                            (
                                (
                                    "Don't you dare pin this on me! I have no "
                                    "control over power outages. Your lack of "
                                    "preparation for contingencies is not my "
                                    "problem. Back off!"
                                ),
                                (
                                    "I am not blaming you for the power outage. I am "
                                    "merely stating the facts. The power outage has "
                                    "completely derailed the presentation. We need to "
                                    "reschedule immediately and find a way to make it "
                                    "up to the client."
                                ),
                            ),
                        ],
                    ),
                    next=_UserReactConfrontationalData(
                        state="feedback_confrontational"
                    ),
                )
            case "feedback_confrontational":
                return FeedbackState(
                    prompt="The latest message was confrontational and aggressive. "
                    "The user overreacted to a blunt message and needs to use "
                    "neutral language instead. Provide feedback on how the user "
                    "could have been more empathetic and understanding in their "
                    "response.",
                    follow_up="I will apologize for being confrontational.",
                    examples=[
                        (
                            [
                                UserMessage(
                                    message="Don't you dare pin this on me! I have no "
                                    "control over power outages. Your lack of "
                                    "preparation for contingencies is not my "
                                    "problem. Back off!"
                                ),
                                AgentMessage(
                                    message="I am not blaming you for the power "
                                    "outage. I am merely stating the facts. The power "
                                    "outage has completely derailed the presentation. "
                                    "We need to reschedule immediately and find a way "
                                    "to make it up to the client."
                                ),
                            ],
                            Feedback(
                                title="🛑 Avoid Confrontational Language",
                                body="Your response was overly confrontational and "
                                "aggressive. By saying 'Don't you dare pin this on "
                                "me!' and 'Back off!', you escalated the situation "
                                "unnecessarily. {agent} was not blaming you, but "
                                "expressing concern about the situation. Try to "
                                "respond to the content of the message rather than "
                                "reacting defensively.",
                                follow_up="I apologize for my confrontational "
                                "response. You're right, we need to focus on "
                                "rescheduling and addressing the client's concerns. "
                                "What steps do you suggest we take to handle this "
                                "situation?",
                                explanation="This response acknowledges the mistake, "
                                "apologizes for the confrontational tone, and "
                                "redirects the conversation towards problem-solving. "
                                "It shows a willingness to collaborate and address "
                                "the actual issue at hand.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="The shipment delay is not my fault! I'm "
                                    "not responsible for broken-down trucks. "
                                    "If you can't handle a simple delay, maybe "
                                    "you're in the wrong business. The "
                                    "shipment will get there when it gets "
                                    "there."
                                ),
                                AgentMessage(
                                    message="The shipment delay is causing serious "
                                    "problems for our entire supply chain. We need "
                                    "to address this urgently and inform all affected "
                                    "parties. I am not blaming you; I am merely "
                                    "stating the facts. "
                                ),
                            ],
                            Feedback(
                                title="🤝 Avoid Confrontation",
                                body="Your response was confrontational and escalated "
                                "the situation. By saying 'If you can't handle a "
                                "simple delay, maybe you're in the wrong business', "
                                "you created unnecessary tension. {agent} was "
                                "expressing concern about the impact of the delay, "
                                "not attacking you personally. Try to address the "
                                "issue calmly and focus on finding solutions rather "
                                "than responding aggressively.",
                                follow_up="I apologize for my confrontational "
                                "response. You're right that the delay is causing "
                                "significant problems. Let's work together on "
                                "mitigating the impact. What steps do you suggest we "
                                "take to inform affected parties and minimize "
                                "disruption to our supply chain?",
                                explanation="This response acknowledges the mistake in "
                                "being confrontational, apologizes for it, and shifts "
                                "the focus to collaborative problem-solving. It "
                                "demonstrates a willingness to work together "
                                "constructively to address the situation.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Don't you dare pin this on me! I have no "
                                    "control over power outages. Your lack of "
                                    "preparation for contingencies is not my "
                                    "problem. Back off!"
                                ),
                                AgentMessage(
                                    message="I am not blaming you for the power "
                                    "outage. I am merely stating the facts. The power "
                                    "outage has completely derailed the presentation. "
                                    "We need to reschedule immediately and find a way "
                                    "to make it up to the client."
                                ),
                            ],
                            Feedback(
                                title="🤝 Avoid Confrontation",
                                body="Your response was unnecessarily confrontational. "
                                "By saying 'Don't you dare pin this on me!' and 'Back "
                                "off!', you escalated the situation and created a "
                                "hostile environment. {agent} was not blaming you "
                                "personally, but expressing concern about the "
                                "impact of the power outage. Try to respond more "
                                "calmly and focus on finding solutions rather than "
                                "becoming defensive.",
                                follow_up="I apologize for my outburst. You're right, "
                                "the power outage has caused significant problems. "
                                "Let's focus on rescheduling the presentation and "
                                "addressing the client's concerns. What steps do you "
                                "suggest we take?",
                                explanation="This response acknowledges the mistake in "
                                "being confrontational, apologizes for it, and shifts "
                                "the focus to problem-solving. It shows a willingness "
                                "to collaborate and address the actual issues at hand.",
                            ),
                        ),
                    ],
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
                            instructions=MessageInstructions(
                                model=llm.Model.GPT_4,
                                description="I will interpret the other person's "
                                "message as sarcastic and respond accordingly. I "
                                "believe the other person is being rude to me because "
                                "they are being sarcastic.",
                                examples=[
                                    (
                                        (
                                            "We need to fix this issue immediately. "
                                            "It's causing major problems for our "
                                            "clients."
                                        ),
                                        (
                                            "Oh, sure, 'major problems.' Because a "
                                            "jammed printer is clearly the end of the "
                                            "world, right? Your sarcasm isn't helping. "
                                            "Why don't you just say what you really "
                                            "mean instead of exaggerating?"
                                        ),
                                    ),
                                    (
                                        (
                                            "The deadline for this project is "
                                            "tomorrow. We need to work overtime to "
                                            "finish it."
                                        ),
                                        (
                                            "Oh, 'serious issues' and 'urgent,' huh? "
                                            "Wow, I had no idea a deadline could be so "
                                            "important! Should we call the president? "
                                            "Maybe declare a state of emergency? "
                                            "Thanks for enlightening me about the "
                                            "earth-shattering importance of our "
                                            "project timeline."
                                        ),
                                    ),
                                    (
                                        (
                                            "The client is very unhappy with the "
                                            "latest design. We need to make "
                                            "significant changes."
                                        ),
                                        (
                                            "Oh, I'm sure the client is 'very "
                                            "unhappy.' And let me guess, we need to "
                                            "make 'significant' changes? Come on, "
                                            "stop exaggerating. It can't be that bad. "
                                            "Why are you always so dramatic about "
                                            "these things?"
                                        ),
                                    ),
                                ],
                            ),
                            next=_UserReactInterpretSarcasmData(
                                state="agent_react_sarcastic"
                            ),
                        ),
                    ]
                )
            case "agent_react_sarcastic":
                return AgentState(
                    instructions=MessageInstructions(
                        description="I will express my frustration about the situation "
                        "bluntly. The other person does not understand that I am being "
                        "serious.",
                        examples=[
                            (
                                (
                                    "Oh, sure, 'major problems.' Because a "
                                    "jammed printer is clearly the end of the "
                                    "world, right? Your sarcasm isn't helping. "
                                    "Why don't you just say what you really "
                                    "mean instead of exaggerating?"
                                ),
                                (
                                    "I'm not being sarcastic. These are serious issues "
                                    "that need our immediate attention. Your "
                                    "dismissive attitude is frustrating and "
                                    "unproductive. Can we focus on addressing the "
                                    "problems at hand instead of downplaying their "
                                    "importance?"
                                ),
                            ),
                            (
                                (
                                    "Oh, 'serious issues' and 'urgent,' huh? "
                                    "Wow, I had no idea a deadline could be so "
                                    "important! Should we call the president? "
                                    "Maybe declare a state of emergency? "
                                    "Thanks for enlightening me about the "
                                    "earth-shattering importance of our "
                                    "project timeline."
                                ),
                                (
                                    "I'm not exaggerating or being dramatic. These are "
                                    "real, significant problems that require our "
                                    "immediate attention. Your dismissive attitude "
                                    "isn't helping the situation. Can we please focus "
                                    "on addressing these issues seriously instead of "
                                    "making light of them?"
                                ),
                            ),
                            (
                                (
                                    "Oh, I'm sure the client is 'very "
                                    "unhappy.' And let me guess, we need to "
                                    "make 'significant' changes? Come on, "
                                    "stop exaggerating. It can't be that bad. "
                                    "Why are you always so dramatic about "
                                    "these things?"
                                ),
                                (
                                    "I'm not being dramatic. The client's "
                                    "dissatisfaction is a serious concern that "
                                    "requires our immediate attention. Your dismissive "
                                    "attitude is making it difficult to address the "
                                    "problem effectively. Can we please focus on "
                                    "finding solutions instead of downplaying the "
                                    "issue?"
                                ),
                            ),
                        ],
                    ),
                    next=_UserReactInterpretSarcasmData(state="feedback_sarcastic"),
                )
            case "feedback_sarcastic":
                return FeedbackState(
                    prompt="The latest message was interpreted as sarcastic and "
                    "dismissed. The user needs to be more empathetic and understanding "
                    "in their response. Provide feedback on how the user could have "
                    "responded more appropriately.",
                    follow_up="I will apologize for incorrectly interpreting the "
                    "message as sarcastic when it was not intended that way.",
                    examples=[
                        (
                            [
                                UserMessage(
                                    message="Oh, sure, 'major problems.' Because a "
                                    "jammed printer is clearly the end of the "
                                    "world, right? Your sarcasm isn't helping. "
                                    "Why don't you just say what you really "
                                    "mean instead of exaggerating?"
                                ),
                                AgentMessage(
                                    message="I'm not being sarcastic. These are "
                                    "serious issues that need our immediate "
                                    "attention. Your dismissive attitude is "
                                    "frustrating and unproductive. Can we focus "
                                    "on addressing the problems at hand instead "
                                    "of downplaying their importance?"
                                ),
                            ],
                            Feedback(
                                title="🤔 Don't Assume Blunt Communication is "
                                "Sarcastic",
                                body="Your response incorrectly assumed {agent} was "
                                "being sarcastic when they were actually expressing "
                                "genuine concern. This misinterpretation led to a "
                                "dismissive and unproductive response. "
                                "It's important to consider that direct communication "
                                "doesn't always imply sarcasm or exaggeration.",
                                follow_up="I apologize for misinterpreting your tone. "
                                "I now understand these are serious issues. Can you "
                                "elaborate on the specific problems we're facing so "
                                "we can work on solutions together?",
                                explanation="This response acknowledges the mistake in "
                                "interpretation, apologizes for it, and shifts the "
                                "focus back to addressing the actual issues at hand. "
                                "It opens the door for clearer communication "
                                "and collaborative problem-solving.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Oh, 'serious issues' and 'urgent,' huh? "
                                    "Wow, I had no idea a deadline could be so "
                                    "important! Should we call the president? "
                                    "Maybe declare a state of emergency? "
                                    "Thanks for enlightening me about the "
                                    "earth-shattering importance of our "
                                    "project timeline."
                                ),
                                AgentMessage(
                                    message="I'm not exaggerating or being dramatic. "
                                    "These are real, significant problems that require "
                                    "our immediate attention. Your dismissive attitude "
                                    "isn't helping the situation. Can we please focus "
                                    "on addressing these issues seriously instead of "
                                    "making light of them?"
                                ),
                            ],
                            Feedback(
                                title="🤔 Avoid Confusing Directness with Sarcasm",
                                body="Your response misjudged {agent}'s genuine "
                                "concern as sarcasm, leading to an unhelpful and "
                                "dismissive reaction. Remember that straightforward "
                                "communication doesn't necessarily imply sarcasm or "
                                "hyperbole.",
                                follow_up="I apologize for the misunderstanding. I now "
                                "recognize the gravity of the situation. Can you "
                                "provide more details about the issues we're facing "
                                "so we can collaborate on finding solutions?",
                                explanation="This response acknowledges the "
                                "misinterpretation, apologizes, and refocuses on "
                                "addressing the actual problems. It fosters "
                                "clearer communication and collaborative "
                                "collaborative problem-solving.",
                            ),
                        ),
                        (
                            [
                                UserMessage(
                                    message="Oh, I'm sure the client is 'very "
                                    "unhappy.' And let me guess, we need to "
                                    "make 'significant' changes? Come on, "
                                    "stop exaggerating. It can't be that bad. "
                                    "Why are you always so dramatic about "
                                    "these things?"
                                ),
                                AgentMessage(
                                    message="I'm not being dramatic. The client's "
                                    "dissatisfaction is a serious concern that "
                                    "requires our immediate attention. Your dismissive "
                                    "attitude is making it difficult to address the "
                                    "problem effectively. Can we please focus on "
                                    "finding solutions instead of downplaying the "
                                    "issue?"
                                ),
                            ],
                            Feedback(
                                title="🚨 Avoid Misinterpreting Bluntness as Sarcasm",
                                body="Your response suggests that you may have "
                                "misinterpreted the other person's blunt tone as "
                                "sarcasm. Remember that direct communication doesn't "
                                "necessarily imply sarcasm or hyperbole. Be cautious "
                                "not to misjudge the tone and respond in a way that "
                                "escalates the situation.",
                                follow_up="I apologize for the misunderstanding. I "
                                "realize now that the tone was direct, not sarcastic. "
                                "Can we refocus on addressing the client's concerns "
                                "and finding solutions?",
                                explanation="This response acknowledges the potential "
                                "misinterpretation, apologizes, and refocuses on "
                                "addressing the actual problems. It fosters clearer "
                                "communication and collaborative problem-solving.",
                            ),
                        ),
                    ],
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
                    instructions=MessageInstructions(
                        description="I will respond neutrally to the other person's "
                        "frustration. I will acknowledge their frustration and respond "
                        "empathetically."
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
                        description="I will end the conversation by saying goodbye "
                        "and expressing my appreciation for the conversation. I will "
                        "also thank the person for their time.",
                    ),
                    next=_EndData(state="user_goodbye"),
                )
            case "user_goodbye":
                return UserState(
                    options=[
                        UserOption(
                            instructions=MessageInstructions(
                                description="I will end the conversation by saying "
                                "goodbye and expressing my appreciation for the "
                                "conversation. I will also thank the person for their "
                                "time.",
                            ),
                            next=None,
                        )
                    ]
                )


STATES = ChainStates(
    _IntroStates(),
    UserNaturalStates(),
    RepeatStates(
        ChainStates(
            WithCtxStates(
                _FrustratedStates(),
                agent_ctx="I will discuss a solution to the problem, continuing the "
                "conversation naturally.",
            ),
            UnionStates(
                _UserReactInterpretSarcasmStates(),
                _UserReactDismissiveStates(),
                _UserReactConfrontationalStates(),
                base=_UserReactEmpatheticStates(),
            ),
            WithCtxStates(
                ChainStates(
                    AgentNaturalStates(),
                    UserNaturalStates(),
                ),
            ),
        ),
        5,
    ),
    _EndStates(),
)

SCENARIO_SEED = LevelConversationScenarioSeed(
    user_perspective=(
        "There is a problem caused by things out of your control, so you "
        "reach out to someone to inform them about it."
    ),
    agent_perspective=(
        "You receive a message from someone you know about a problem, leaving "
        "you feeling frustrated about the situation."
    ),
    user_goal=("Inform the person about the problem."),
    is_user_initiated=True,
    adapt=True,
)
