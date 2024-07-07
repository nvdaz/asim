from pydantic import BaseModel

from .client import db


class MagicLink(BaseModel):
    secret: str
    user_id: str


magic_links = db.magic_links


async def create(magic_link: MagicLink):
    await magic_links.insert_one(magic_link.model_dump())


async def get(secret: str):
    magic_link = await magic_links.find_one({"secret": secret})
    return MagicLink(**magic_link) if magic_link else None
