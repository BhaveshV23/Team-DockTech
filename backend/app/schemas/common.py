"""Common Pydantic schemas for DockTech V1 API."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
