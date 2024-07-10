import secrets
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, RootModel
from pydantic.fields import Field
from typing_extensions import Annotated

from api.db import auth_tokens, magic_links
from api.db import users as users
from api.schemas.user import User


class LoginResultReturningUser(BaseModel):
    new_user: Literal[False] = False
    token: str
    user: User


class LoginResultNewUser(BaseModel):
    new_user: Literal[True] = True
    token: str
    user_id: str


class LoginResult(RootModel):
    root: Annotated[
        LoginResultReturningUser | LoginResultNewUser, Field(discriminator="new_user")
    ]


async def _create_auth_token(user_id: str) -> str:
    secret = secrets.token_urlsafe(16)
    token = auth_tokens.AuthToken(secret=secret, user_id=user_id)
    await auth_tokens.create(token)
    return token.secret


class InvalidMagicLink(Exception):
    pass


async def login_user(secret: str) -> LoginResult:
    link = await magic_links.get(secret)

    if not link:
        raise InvalidMagicLink()

    token = await _create_auth_token(link.user_id)

    user = await users.get(UUID(link.user_id))

    if not user:
        return LoginResultNewUser(user_id=link.user_id, token=token)

    return LoginResultReturningUser(user=user, token=token)


async def create_magic_link(user_id: str) -> str:
    secret = secrets.token_urlsafe(16)
    link = magic_links.MagicLink(secret=secret, user_id=user_id)
    await magic_links.create(link)
    return link.secret


async def setup_user(user_id: UUID, name: str) -> User:
    user = users.User(user_id=user_id, name=name)
    await users.upsert(user)
    return user
