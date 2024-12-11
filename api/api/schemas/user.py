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


class LocationOptions(BaseModel):
    city: str
    country: str


class PlanVacationScenarioOptions(BaseModel):
    vacation_destination: str
    vacation_explanation: str


class UserPersonalizationOptions(BaseModel):
    name: str
    age: str
    gender: str
    location: LocationOptions
    company: str
    occupation: str
    interests: str
    scenario: PlanVacationScenarioOptions
    personality: list[str]


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
