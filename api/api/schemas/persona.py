from pydantic import BaseModel


class PersonaName(BaseModel):
    name: str


class BasePersona(BaseModel):
    name: str | None = None
    age: str
    occupation: str
    interests: list[str]


class Persona(BasePersona):
    description: str
