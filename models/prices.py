from bson import ObjectId
from pydantic import BaseModel, Field
from configuration import Config

config = Config()


class Prices(BaseModel):
    mongo_id: ObjectId = Field(default_factory=ObjectId, alias="_id", description="The MongoDB Object ID")
    name: str = Field(..., description="Name of the prices list")
    plans: list = Field(default_factory=list, description="Plans of the prices list")

    def commit_changes(self):
        data = self.model_dump(by_alias=True)
        del data['_id']
        config.get_db().prices.update_one({'name': self.name}, {'$set': data}, upsert=True)

    class Config:
        arbitrary_types_allowed = True
