from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar('T')


class UnifyResponse(BaseModel, Generic[T]):
    """The Unify Server Response class"""

    msgId: str
    msgCode: int
    data: T | None = None

    # def __init__(self, msgId: str, msgCode: int):
    #     self.msgId = msgId
    #     self.msgCode = msgCode

    def is_ok(self) -> bool:
        """Returns true if the server response is success."""
        return self.msgCode == 0

    def has_data(self) -> bool:
        """Returns true if the server response is success and has response data."""
        return self.is_ok() and self.data is not None
