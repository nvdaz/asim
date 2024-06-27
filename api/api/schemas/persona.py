from pydantic import BaseModel


class BasePersona(BaseModel):
    name: str
    age: str
    occupation: str
    interests: list[str]


class Persona(BasePersona):
    description: str
