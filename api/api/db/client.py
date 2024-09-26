import os

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "autsim")


client = AsyncIOMotorClient(MONGO_URI, uuidRepresentation="standard")

db = client[DATABASE_NAME]
