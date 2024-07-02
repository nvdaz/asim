import sys

import requests

LEVEL = 1

r = requests.post("http://localhost:8000/conversations/", json={"level": LEVEL}).json()

id = r["id"]
sn = r["subject_name"]

option = None

while True:
    r = requests.post(
        f"http://localhost:8000/conversations/{id}/next", params={"option": option}
    ).json()
    option = None

    if r["type"] == "np":
        for i, option in enumerate(r["options"]):
            print(f"{i + 1}. {option}")
        option = int(input("Option: ")) - 1
        for _ in range(len(r["options"]) + 1):
            sys.stdout.write("\033[F")
            sys.stdout.write("\033[K")
        print(f"You: {r['options'][option]}")
    elif r["type"] == "ap":
        print(f"{sn}: {r['content']}")
    elif r["type"] == "feedback":
        print(f"!{r['content']['title']}!: {r['content']['body']}")
        if r["content"]["follow_up"] is not None:
            print(f"You: {r['content']['follow_up']}")
    else:
        raise ValueError(f"Unknown state type: {r['type']}")
