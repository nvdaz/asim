import secrets

from bson import ObjectId
from pydantic import BaseModel

from api.db import auth_tokens, magic_links
from api.db import users as users
from api.schemas.user import BaseUserData, User, UserData, user_from_data


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


async def create_magic_link(data: BaseUserData) -> str:
    secret = secrets.token_urlsafe(16)

    user = await users.create(data)

    link = magic_links.MagicLink(secret=secret, user_id=user.id)
    await magic_links.create(link)

    return link.secret


class AlreadyInitialized(Exception):
    pass


async def init_user(user_id: ObjectId, name: str) -> UserData:
    user = await users.get(user_id)

    if not user:
        raise ValueError("User not found")

    user.name = name

    return await users.update(user_id, user)
