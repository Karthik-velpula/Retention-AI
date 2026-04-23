from pydantic import BaseModel


class AssistantQueryRequest(BaseModel):
    query: str


class AssistantQueryResponse(BaseModel):
    answer: str
