from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

@dataclass
class UserProduct(BaseModel):
    """"""
    sn: str
    stateList: list
    online: str
    name: Optional[str] = None

