import secrets

import api.db.cohort as cohort_db
from api.db.cohort import BaseCohort
from api.schemas import user
from api.services.auth import create_magic_link


async def create_cohort(name: str, init_chats: list[user.Options]):
    secret = secrets.token_urlsafe(16)
    cohort = BaseCohort(name=name, secret=secret, init_chats=init_chats)
    await cohort_db.create(cohort)
    return cohort


async def get(token: str):
    return await cohort_db.get(token)


class InvalidCohortToken(Exception):
    pass


async def create_user(cohort_token: str):
    cohort = await get(cohort_token)

    if not cohort:
        raise InvalidCohortToken()

    return await create_magic_link(cohort.init_chats, cohort.id)
