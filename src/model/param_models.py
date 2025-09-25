from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, field_validator
from pydantic_core import from_json
from typing_extensions import Annotated


class FilterByInputs(BaseModel):
    field_name: str
    values: List[str]


def ensure_list(value: Any) -> List[FilterByInputs]:
    if not isinstance(value, list):
        try:
            parsed = from_json(value)
            if not isinstance(parsed, list):
                raise ValueError("filter_by_inputs must be a list of objects.")
            return parsed
        except JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for filter_by_inputs: {e}") from e
    return value


class StandardParams(BaseModel):
    """
    Example of a standard set of parameters

    filter_by_inputs:[{"field_name": "parent_id", "values": ["7"]}, {"field_name": "file_type", "values": ["pdf"]}]
    page:1
    page_size:20
    sort_order:asc
    sort_by:file_size
    from_date: "2021-01-01T00:00:00"
    to_date: "2021-01-31T23:59:59"
    """

    sort_by: Optional[str] = None
    sort_order: str = "desc"
    page: int
    page_size: int
    search: Optional[str] = None
    from_date: Optional[datetime] = Field(
        None, description="Start date for filtering, as a timestamp or ISO 8601 string."
    )
    to_date: Optional[datetime] = Field(
        None, description="End date for filtering, as a timestamp or ISO 8601 string."
    )
    filter_by_inputs: Optional[
        Annotated[List[FilterByInputs], BeforeValidator(ensure_list)]
    ] = []


class ImportParams(StandardParams):
    sort_by: Optional[Literal["file_name", "status", "uploaded_at"]] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(500, ge=1)


class TransactionsParams(StandardParams):
    sort_by: Optional[Literal["amount", "date", "title"]] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(500, ge=1)

    @field_validator("from_date", "to_date")
    def validate_dates(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
