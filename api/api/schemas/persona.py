from pydantic import BaseModel


class PersonaName(BaseModel):
    name: str


class BasePersonaUninit(BaseModel):
    age: str
    occupation: str
    interests: list[str]


class PersonaUninit(BasePersonaUninit):
    description: str


class BasePersona(BaseModel):
    name: str
    age: str
    occupation: str
    interests: list[str]


class Persona(BasePersona):
    description: str
