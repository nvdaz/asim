from typing import Any

from bson import ObjectId
from pydantic_core import core_schema


class ObjectIdField:
    @classmethod
    def validate_object_id(cls, v: Any, handler) -> str:
        if isinstance(v, ObjectId):
            return str(v)

        s = handler(v)
        if ObjectId.is_valid(s):
            return s
        else:
            raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, _handler
    ) -> core_schema.CoreSchema:
        assert source_type is str
        return core_schema.no_info_wrap_validator_function(
            cls.validate_object_id,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
