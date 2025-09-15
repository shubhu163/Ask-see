from typing import Optional
from pydantic import BaseModel


class IngestItem(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = "user"
    title: Optional[str] = ""


class AskPayload(BaseModel):
    question: str
    k: int = 4


