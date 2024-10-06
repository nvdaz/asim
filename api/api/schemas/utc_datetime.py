from datetime import datetime, timezone
from typing import Annotated

from pydantic_core import core_schema


class _UTCDatetimeField(datetime):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.datetime_schema()
        )

    @classmethod
    def validate(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


UTCDatetime = Annotated[datetime, _UTCDatetimeField]
