from uuid import UUID

from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing_extensions import Annotated

from api.db import auth_tokens, users
from api.schemas.user import User

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
) -> User:
    token = await auth_tokens.get(authorization.credentials)

    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = token.user_id

    user = await users.get(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Current user not found")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
