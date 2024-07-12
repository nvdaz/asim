import secrets
from uuid import UUID

from bson import ObjectId
from pydantic import BaseModel

from api.db import auth_tokens, magic_links
from api.db import users as users
from api.schemas.persona import Persona
from api.schemas.user import BaseUserInit, User, UserInit

from .user_info import generate_user_info


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


async def login_user(secret: str) -> LoginResult:
    link = await magic_links.get(secret)

    if not link:
        raise InvalidMagicLink()

    user = await users.get(link.user_id)

    token = await _create_auth_token(user.root.id)

    return LoginResult(user=user, token=token)


async def create_magic_link(qa_id: UUID) -> str:
    secret = secrets.token_urlsafe(16)

    user = await users.get_by_qa_id(qa_id)

    if not user:
        persona = await generate_user_info(qa_id)
        user = await users.create(users.BaseUserUninit(qa_id=qa_id, persona=persona))

    link = magic_links.MagicLink(secret=secret, user_id=user.root.id)
    await magic_links.create(link)
    return link.secret


class AlreadyInitialized(Exception):
    pass


async def init_user(user_id: ObjectId, name: str) -> User:
    user_uninit = await users.get(user_id)
    if isinstance(user_uninit.root, UserInit):
        raise AlreadyInitialized()

    user_init = BaseUserInit(
        qa_id=user_uninit.root.qa_id,
        name=name,
        persona=Persona(
            name=name,
            age=user_uninit.root.persona.age,
            occupation=user_uninit.root.persona.occupation,
            interests=user_uninit.root.persona.interests,
            description=user_uninit.root.persona.description.replace("{{NAME}}", name),
        ),
    )

    return await users.update(user_id, user_init)
