from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.auth.deps import CurrentUser, CurrentUserID
from api.schemas.user import User
from api.services.auth import (
    InvalidMagicLink,
    LoginResult,
    create_magic_link,
    login_user,
    setup_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginOptions(BaseModel):
    magic_link: str


@router.post("/exchange", responses={401: {"description": "Invalid magic link"}})
async def exchange(options: LoginOptions) -> LoginResult:
    try:
        return await login_user(options.magic_link)
    except InvalidMagicLink:
        return JSONResponse(status_code=401, content={"message": "Invalid magic link"})


class SetupOptions(BaseModel):
    name: str


@router.post("/setup")
async def setup(current_user_id: CurrentUserID, options: SetupOptions) -> User:
    return await setup_user(current_user_id, options.name)


@router.get("/me")
async def me(current_user: CurrentUser) -> User:
    return current_user


@router.post("/internal-create-magic-link")
async def internal_create_magic_link(user_id: str) -> str:
    return await create_magic_link(user_id)
