from api.schemas.conversation import (
    AgentMessage,
    ConversationScenario,
    Message,
    UserMessage,
    message_list_adapter,
)
from api.schemas.persona import Persona

from . import llm


async def generate_message(
    user_sent: bool,
    user: Persona,
    agent: Persona,
    messages: list[Message],
    scenario: ConversationScenario,
    instructions: str | None = None,
) -> str:
    scenario_perspective = (
        scenario.user_perspective if user_sent else scenario.agent_perspective
    )

    prelude = "\n".join(
        filter(
            None,
            [
                user.description if user_sent else agent.description,
                f"Scenario: {scenario_perspective}" if scenario_perspective else None,
                (
                    f"INSTRUCTIONS FOR YOUR MESSAGE: {instructions}"
                    if instructions
                    else None
                ),
            ],
        )
    )

    user_name = f"{user.name} (the user)" or "the user"

    sender_name = user_name if user_sent else agent.name
    recipient_name = agent.name if user_sent else user_name

    system_prompt = (
        f"{prelude}\nYou ({sender_name}) are chatting over text with {recipient_name}. "
        "Keep your messages under 60 words and appropriate for a text conversation. "
        "ALWAYS provide detailed information and DO NOT end the conversation. "
        "DO NOT try to start any external conversations or schedule any meetings. "
        "Respond with a JSON object containing the key 'message' with your message as "
        f"the value and the key 'is_user' with {str(user_sent).lower()} as the value, "
        "representing whether you are the user. Respond ONLY with your next message. "
        "Do not include previous messages in your response. STAY ON TOPIC and DO NOT "
        "mention your communication styles. DO NOT reference external information."
    )

    print(system_prompt)

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages) == 0
        else message_list_adapter.dump_json(messages[-8:]).decode()
    )

    response = await llm.generate(
        schema=UserMessage if user_sent else AgentMessage,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
