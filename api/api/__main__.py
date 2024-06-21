import asyncio
import random

import pandas as pd

from .extract import extract_user_info
from .flows import generate_next
from .persona import generate_subject_persona, generate_user_persona
from .scenario import generate_scenario

random.seed(0)


async def main():
    df = pd.read_csv("./userConversations.csv", header=0)

    df.dropna(subset=["prompt_sender"], inplace=True)
    df.dropna(subset=["prompt_str"], inplace=True)
    df.dropna(subset=["response_str"], inplace=True)

    users = {}

    for _, row in df.iterrows():
        user = row["prompt_sender"]
        if user not in users:
            users[user] = []
        users[user].append((row["prompt_str"], row["response_str"]))

    user = users["0053c352-d227-40b9-989c-78ec216d3a21"]
    user = user[0:400]

    user_info = await extract_user_info(user)

    user_scenario, subject_scenario, goal = await generate_scenario(user_info)

    user_name = "Kyle"

    print(user_info)
    print(user_scenario, subject_scenario)
    print("\n" * 3)

    subject_info, subject_persona = await generate_subject_persona(subject_scenario)
    user_persona = await generate_user_persona(user_info, user_name)

    user_scenario = user_scenario.replace("{{USER}}", user_name)
    user_scenario = user_scenario.replace("{{SUBJECT}}", subject_info["name"])

    subject_scenario = subject_scenario.replace("{{USER}}", user_name)
    subject_scenario = subject_scenario.replace("{{SUBJECT}}", subject_info["name"])

    print(subject_persona)
    print("\n")
    print(user_persona)

    conversation_history = "[start of conversation]"

    print("\n" * 5 + " --- START OF CONVERSATION --- " + "\n")

    print(f"[Scenario: {user_scenario}]\n")

    state = "np_normal"

    while True:
        ty, responses = await generate_next(
            state,
            user_info,
            user_persona,
            user_scenario,
            subject_info,
            subject_persona,
            subject_scenario,
            conversation_history,
        )

        if ty == "np":
            for i, response in enumerate(responses):
                print(f"\033[90m{i + 1}. {response['response']}\033[0m")

            choice = input("\033[90mChoice: ")
            print("\033[0m")

            response = responses[int(choice) - 1]

            conversation_history += f"\n{user_name}: <{response['response']}>"
            print(f"{user_name}: {response['response']}")
            state = response["next"]
        elif ty == "ap":
            if len(responses) > 1:
                print(
                    f"\033[90m[ap selected 1 response out of {len(responses)}]\033[0m"
                )
            response = random.choice(responses)

            conversation_history += (
                f"\n{subject_info['name']}: <{response['response']}>"
            )
            print(f"{subject_info['name']}: {response['response']}")
            state = response["next"]
        elif ty == "feedback":
            assert len(responses) == 1
            response = responses[0]

            print(f"Feedback: {response['response']}")
            state = response["next"]
        else:
            raise ValueError(f"Encountered invalid type: {ty}")


asyncio.run(main())
