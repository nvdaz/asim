import sys

import requests

TYPE = "playground"
LEVEL = 0
AUTH_TOKEN = "f0JjMY7l7DenxaehOvfvvA"

r = requests.post(
    "http://localhost:8000/conversations/",
    json={"type": TYPE, "level": LEVEL},
    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
).json()

if TYPE == "level":
    print(f"Scenario: {r['info']['scenario']['user_perspective']}")

id = r["id"]
sn = r["agent"]

option = None

while True:
    if option is None:
        option_dict = {"option": "none"}
    elif isinstance(option, int):
        option_dict = {"option": "index", "index": option}
    elif isinstance(option, str):
        option_dict = {"option": "custom", "message": option}
    else:
        raise ValueError(f"Unknown option type: {option}")

    r = requests.post(
        f"http://localhost:8000/conversations/{id}/next",
        json=option_dict,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    ).json()
    option = None

    if r["type"] == "np":
        for i, option in enumerate(r["options"]):
            print(f"{i + 1}. {option}")
        option_str = input("Option: ")

        for _ in range(len(r["options"]) + 1):
            sys.stdout.write("\033[F")
            sys.stdout.write("\033[K")

        try:
            option = int(option_str) - 1
            print(f"You: {r['options'][option]}")
        except ValueError:
            option = option_str
            print(f"You: {option}")

    elif r["type"] == "ap":
        print(f"{sn}: {r['content']}")
    elif r["type"] == "feedback":
        print(f"!{r['content']['title']}!: {r['content']['body']}")
        if r["content"]["follow_up"] is not None:
            print(f"You: {r['content']['follow_up']}")
            option = 0
    else:
        raise ValueError(f"Unknown state type: {r['type']}")
