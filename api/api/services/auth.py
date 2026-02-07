import secrets

from bson import ObjectId
from pydantic import BaseModel

from api.db import auth_tokens, magic_links
from api.db import users as users
from api.schemas import user
from api.schemas.user import (
    BaseUserData,
    User,
    UserData,
    UserPersonalizationOptions,
    user_from_data,
)
from api.services import chat_service


class LoginResult(BaseModel):
    token: str
    user: User


async def _create_auth_token(user_id: ObjectId) -> str:
    secret = secrets.token_urlsafe(16)
    token = auth_tokens.AuthToken(secret=secret, user_id=user_id)
    await auth_tokens.create(token)
    return token.secret


class InvalidMagicLink(Exception):
    pass


class NeedsSetup(Exception):
    pass


async def login_user(secret: str) -> LoginResult:
    link = await magic_links.get(secret)

    if not link:
        raise InvalidMagicLink()

    if not link.user_id:
        raise Exception("Magic link not initialized")

    user = await users.get(link.user_id)

    if not user:
        raise InvalidMagicLink()

    token = await _create_auth_token(user.id)

    return LoginResult(user=user_from_data(user), token=token)


async def create_magic_link(
    init_chats: list[user.Options], cohort_id: ObjectId | None = None
) -> str:
    secret = secrets.token_urlsafe(16)

    user = await users.create(BaseUserData(init_chats=init_chats, cohort=cohort_id))

    link = magic_links.MagicLink(secret=secret, user_id=user.id)
    await magic_links.create(link)

    return link.secret


class AlreadyInitialized(Exception):
    pass


async def init_user(
    user_id: ObjectId, personalization: UserPersonalizationOptions
) -> UserData:
    user = await users.get(user_id)

    if not user:
        raise ValueError("User not found")

    user.name = personalization.name
    user.personalization = personalization

    user = await users.update(user_id, user)

    for options in user.init_chats:
        await chat_service.create_chat(user, options)

    return user
