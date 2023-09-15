from bson import ObjectId
from pydantic import BaseModel, Field
from configuration import Config

config = Config()


class Referral(BaseModel):
    mongo_id: ObjectId = Field(default_factory=ObjectId, alias="_id", description="The MongoDB Object ID")
    name: str = Field(..., description="Name of the referral link")

    @property
    def amount(self):
        return config.get_db().users.count_documents({'referrer.id': self.mongo_id})

    @property
    def link(self) -> str:
        bot_username = config.get_username()
        return f'https://t.me/{bot_username}?start=refs{self.mongo_id}'

    class Config:
        arbitrary_types_allowed = True
