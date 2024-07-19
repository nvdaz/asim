import os
from typing import Annotated, Literal
from uuid import UUID

from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.db import auth_tokens, users
from api.schemas.user import UserData

_INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

auth_scheme = HTTPBearer()


async def get_current_user_id(
    authorization: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)]
) -> ObjectId:
    token = await auth_tokens.get(authorization.credentials)

    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token.user_id


CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user(
    authorization: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)]
) -> UserData:
    token = await auth_tokens.get(authorization.credentials)

    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = token.user_id

    user = await users.get(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Current user not found")

    return user


CurrentUser = Annotated[UserData, Depends(get_current_user)]


async def get_internal_auth(
    authorization: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)]
) -> Literal[True]:
    if not authorization.credentials:
        raise HTTPException(status_code=401, detail="API key not found")

    if _INTERNAL_API_KEY is None:
        raise HTTPException(status_code=500, detail="Internal API key not set")

    if authorization.credentials != _INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


CurrentInternalAuth = Annotated[Literal[True], Depends(get_internal_auth)]
