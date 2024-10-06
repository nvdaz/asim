import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth.deps import CurrentInternalAuth, CurrentUser, CurrentUserID
from api.schemas.user import User, user_from_data
from api.services.auth import (
    AlreadyInitialized,
    InvalidMagicLink,
    LoginResult,
    create_magic_link,
    init_user,
    login_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginOptions(BaseModel):
    magic_link: str


@router.post("/exchange", responses={401: {"description": "Invalid magic link"}})
async def exchange(options: LoginOptions) -> LoginResult:
    await asyncio.sleep(5)
    try:
        return await login_user(options.magic_link)
    except InvalidMagicLink as e:
        raise HTTPException(status_code=401, detail="Invalid magic link") from e


class SetupOptions(BaseModel):
    name: str


@router.post("/setup", responses={400: {"description": "User already initialized"}})
async def setup(current_user_id: CurrentUserID, options: SetupOptions) -> User:
    try:
        user = await init_user(current_user_id, options.name)
        return user_from_data(user)
    except AlreadyInitialized as e:
        raise HTTPException(status_code=400, detail="User already initialized") from e


@router.get("/me")
async def me(current_user: CurrentUser) -> User:
    return user_from_data(current_user)


@router.post("/internal-create-magic-link")
async def internal_create_magic_link(_: CurrentInternalAuth, qa_id: UUID) -> str:
    return await create_magic_link(qa_id)
