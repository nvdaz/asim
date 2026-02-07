from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from api.schemas import user
from api.schemas.objectid import PyObjectId

from .client import db


class BaseCohort(BaseModel):
    name: str
    secret: str
    init_chats: list[user.Options]

    model_config = ConfigDict(populate_by_name=True)


class Cohort(BaseCohort):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


cohorts = db.cohorts


async def create(cohort: BaseCohort) -> Cohort:
    await cohorts.insert_one(cohort.model_dump())


async def get(secret: str):
    cohort = await cohorts.find_one({"secret": secret})
    return Cohort(**cohort) if cohort else None
