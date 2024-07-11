from csv import DictReader
from itertools import groupby
from uuid import UUID

users = {}

with open("./userConversations.csv") as csv_file:
    csv_reader = DictReader(csv_file)

    users = {
        user: list(map(lambda row: (row["message"], row["response"]), messages))
        for user, messages in groupby(csv_reader, lambda row: row["user_id"])
    }


def get_messages(qa_id: UUID):
    return users.get(str(qa_id), [])

def is_qa_id_valid(qa_id: UUID):
    return str(qa_id) in users
