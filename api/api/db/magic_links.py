from pydantic import BaseModel, ConfigDict

from api.schemas.objectid import PyObjectId

from .client import db


class MagicLink(BaseModel):
    secret: str
    user_id: PyObjectId | None

    model_config = ConfigDict(populate_by_name=True)


magic_links = db.magic_links


async def create(magic_link: MagicLink):
    await magic_links.insert_one(magic_link.model_dump())


async def get(secret: str):
    magic_link = await magic_links.find_one({"secret": secret})
    return MagicLink(**magic_link) if magic_link else None
