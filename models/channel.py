from bson import ObjectId
from pydantic import BaseModel, Field


class Channel(BaseModel):
    mongo_id: ObjectId = Field(default_factory=ObjectId, alias="_id", description="The MongoDB Object ID")
    id: int = Field(..., description="ID of the channel")
    enforce_join: bool = Field(..., description="Whether users should join")
