from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field

from .objectid import PyObjectId


class Options(BaseModel):
    feedback_mode: Literal["on-suggestion", "on-submit"] = "on-submit"
    suggestion_generation: Literal["content-inspired", "random"]


default_options = Options(
    feedback_mode="on-suggestion", suggestion_generation="content-inspired"
)


class UserPersonalizationOptions(BaseModel):
    name: str
    pronouns: str
    education_level: str
    undergraduate_major: str
    topic: str


class BaseUserData(BaseModel):
    name: str | None = None
    options: Options = default_options
    personalization: UserPersonalizationOptions | None = None


class UserData(BaseUserData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class User(BaseUserData):
    id: PyObjectId


def user_from_data(data: UserData) -> User:
    return User(
        id=data.id,
        name=data.name,
        options=data.options,
    )
