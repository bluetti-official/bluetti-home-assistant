from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class UserProduct(BaseModel):
    """"""
    sn: str
