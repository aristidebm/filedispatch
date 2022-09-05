from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, constr
from aiohttp_pydantic.injectors import Group

from src.utils import ProtocolEnum, StatusEnum, OrderingEnum


class WriteOnlyLogEntry(BaseModel):
    filename: constr(max_length=255)
    source: constr(max_length=255)
    destination: constr(max_length=255)
    extension: constr(max_length=20)
    processor: constr(max_length=255)
    protocol: ProtocolEnum
    status: StatusEnum
    size: Optional[str] = None
    byte_size: Optional[int] = None
    reason: Optional[str] = None


class ReadOnlyLogEntry(WriteOnlyLogEntry):
    id: UUID = Field(..., description="Log ID")
    created: datetime = Field(..., description="Date when the log is created")


class QueryDict(Group):

    status: Optional[StatusEnum] = Field(None, description="Filter logs by status")

    destination: Optional[str] = Field(
        None, description="Filter logs by file destination"
    )

    byte_size: Optional[Decimal] = Field(
        None, description="Filter logs by size equals to"
    )

    byte_size__lte: Optional[Decimal] = Field(
        None, description="Filter logs by size less than or equal"
    )

    byte_size__gte: Optional[Decimal] = Field(
        None, description="Filter logs by size greater than or equal"
    )

    extension: Optional[str] = Field(None, description="Filter logs by file extension")

    processor: Optional[str] = Field(
        None, description="Filter logs by processor used to send the file"
    )

    created: Optional[datetime] = Field(
        None, description="Filter logs by creation date equals to"
    )

    created__lte: Optional[datetime] = Field(
        None, description="Filter logs by creation date less than or equal"
    )

    created__gte: Optional[datetime] = Field(
        None, description="Filter logs by creation date greater than or equal"
    )

    ordering: OrderingEnum = Field(
        None,
        description="Ordering Field, prefix the field name with minus(-) to order in DESC",
    )


# class AnyModel(BaseModel):
#     __root__ = Any


class Error(BaseModel):
    detail: Any
