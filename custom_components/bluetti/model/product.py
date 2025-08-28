from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

@dataclass
class UserProduct(BaseModel):
    """"""
    sn: str
    name: str
    stateList: list

