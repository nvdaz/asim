import os
import sys

import requests


def generate_one():
    try:
        body = [
            {
                "feedback_mode": "on-submit",
                "suggestion_generation": "content-inspired",
                "enabled_objectives": [
                    "non-literal-emoji",
                    "non-literal-figurative",
                    "yes-no-question",
                    "blunt",
                ],
                "gap": False,
            }
        ]

        response = requests.post(
            "https://production-427596434062.us-central1.run.app/auth/internal-create-magic-link",
            json=body,
            headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
        )

        return response.json()
    except Exception as e:
        print(f"Request failed: {e}")
        raise e


if __name__ == "__main__":
    assert len(sys.argv) >= 2
    for n in range(int(sys.argv[1])):
        print(f"https://autsim.pages.dev/auth/{generate_one()}")
