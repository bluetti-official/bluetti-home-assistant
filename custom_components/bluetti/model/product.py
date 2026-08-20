from typing import Optional

from pydantic import BaseModel


class UserProduct(BaseModel):
    """"""
    sn: str
    stateList: list
    online: str
    model: Optional[str] = None
    name: Optional[str] = None
    isBindByCurUser: Optional[str] = None

