from enum import Enum

from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from configuration import Config
from models.server import Server

config = Config()

servers_db = config.get_db().servers


class Status(Enum):
    Test = 'test'
    Shop = 'shop'
    Both = 'both'


class Product(BaseModel):
    mongo_id: ObjectId = Field(default_factory=ObjectId, alias="_id", description="The MongoDB Object ID")
    status: Status = Status.Shop
    name: str = Field(..., description="Name of the product")
    servers: List[ObjectId] = Field(..., description="List of server IDs associated with the product")
    price_multiplier: float = Field(default=1.0, description="Multiplier for product pricing")
    stock: int = Field(..., description="Quantity of the product in stock")
    price_plan: ObjectId = Field(default_factory=lambda: config.get_db().prices.find_one({'name': 'Default'})['_id'], description="The price plan ID")

    @property
    def traffic_plans(self) -> List:
        """Fetch the traffic plans from the price plan document."""
        return config.get_db().prices.find_one({'_id': self.price_plan})['plans']

    @property
    def in_stock(self) -> bool:
        """Check if the product is in stock."""
        return bool(self.stock > 0)

    def change_status(self, role: str) -> bool:
        """Change the product's status if it's a valid status."""
        try:
            self.status = Status(role)
            return True
        except ValueError:
            return False

    @property
    def servers_documents(self) -> List[Server]:
        """Fetch the server documents based on the product's servers attribute."""
        # Use the MongoDB query to fetch the server documents by their IDs.
        servers_cursor = servers_db.find({"_id": {"$in": self.servers}})
        # Convert the cursor to a list of dictionaries (documents).
        return list(servers_cursor)

    def model_dump(self, **kwargs) -> dict:
        """Get a dict representation with the role as an Enum."""
        output = super().model_dump(by_alias=True, **kwargs)
        output['status'] = self.status.value
        return output

    class Config:
        arbitrary_types_allowed = True
