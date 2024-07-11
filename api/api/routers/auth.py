from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth.deps import CurrentUser, CurrentUserID
from api.schemas.user import User
from api.services.auth import (
    AlreadyInitialized,
    InvalidMagicLink,
    InvalidUser,
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
    try:
        return await login_user(options.magic_link)
    except InvalidMagicLink as e:
        raise HTTPException(status_code=401, detail="Invalid magic link") from e


class SetupOptions(BaseModel):
    name: str


@router.post("/setup", responses={400: {"description": "User already initialized"}})
async def setup(current_user_id: CurrentUserID, options: SetupOptions) -> User:
    try:
        return await init_user(current_user_id, options.name)
    except AlreadyInitialized as e:
        raise HTTPException(status_code=400, detail="User already initialized") from e


@router.get("/me")
async def me(current_user: CurrentUser) -> User:
    return current_user


@router.post(
    "/internal-create-magic-link", responses={400: {"description": "Invalid user id"}}
)
async def internal_create_magic_link(qa_id: UUID) -> str:
    try:
        return await create_magic_link(qa_id)
    except InvalidUser as e:
        raise HTTPException(status_code=400, detail="Invalid user id") from e
