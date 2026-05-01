from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool
    status: int
    message: str
    data: Optional[T] = None

class ErrorDetail(BaseModel):
    code: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    status: int
    message: str
    error: ErrorDetail
