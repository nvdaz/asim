from pydantic import BaseModel


class PersonaName(BaseModel):
    name: str


class UserBasePersona(BaseModel):
    name: str | None = None
    age: str
    occupation: str
    interests: list[str]


class UserPersona(UserBasePersona):
    description: str


class AgentBasePersona(BaseModel):
    name: str
    age: str
    occupation: str
    interests: list[str]


class AgentPersona(AgentBasePersona):
    description: str


BasePersona = UserBasePersona | AgentBasePersona
Persona = UserPersona | AgentPersona
