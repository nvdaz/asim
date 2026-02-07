from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth.deps import CurrentInternalAuth, CurrentUser, CurrentUserID
from api.schemas.chat import Options
from api.schemas.user import User, UserPersonalizationOptions, user_from_data
from api.services.auth import (
    AlreadyInitialized,
    InvalidMagicLink,
    LoginResult,
    create_magic_link,
    init_user,
    login_user,
)
from api.services.cohort import InvalidCohortToken, create_cohort, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginOptions(BaseModel):
    magic_link: str


@router.post("/exchange", responses={401: {"description": "Invalid magic link"}})
async def exchange(options: LoginOptions) -> LoginResult:
    try:
        return await login_user(options.magic_link)
    except InvalidMagicLink as e:
        raise HTTPException(status_code=401, detail="Invalid magic link") from e


@router.post("/register", responses={400: {"description": "User already initialized"}})
async def setup(
    current_user_id: CurrentUserID, options: UserPersonalizationOptions
) -> User:
    try:
        user = await init_user(current_user_id, options)
        return user_from_data(user)
    except AlreadyInitialized as e:
        raise HTTPException(status_code=400, detail="User already initialized") from e


@router.get("/me")
async def me(current_user: CurrentUser) -> User:
    return user_from_data(current_user)


@router.post("/internal-create-magic-link")
async def internal_create_magic_link(
    _: CurrentInternalAuth, init_chats: list[Options]
) -> str:
    return await create_magic_link(init_chats)


class CreateCohortOptions(BaseModel):
    name: str
    init_chats: list[Options]


@router.post("/internal-create-cohort")
async def internal_create_cohort(
    _: CurrentInternalAuth, options: CreateCohortOptions
) -> str:
    cohort = await create_cohort(options.name, options.init_chats)
    return cohort.secret


class RedeemInviteOptions(BaseModel):
    cohort_secret: str


@router.post("/redeem-invite")
async def redeem_invite(options: RedeemInviteOptions) -> LoginOptions:
    try:
        magic = await create_user(options.cohort_secret)
        return LoginOptions(magic_link=magic)
    except InvalidCohortToken as e:
        raise HTTPException(status_code=400, detail="Invalid cohort token") from e
