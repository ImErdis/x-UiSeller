from enum import Enum
from typing import List
from uuid import UUID

import pymongo
from bson import ObjectId, Binary
from pydantic import BaseModel, Field
from configuration import Config
from models.subscription import Subscription

config = Config()


class Roles(Enum):
    """Enumeration of user roles."""
    Member = 'Member'
    Admin = 'Admin'


class User(BaseModel):
    """Model for representing a user."""

    id: int = Field(alias="_id", description="The MongoDB ID")
    role: Roles = Roles.Member  # Directly use the Roles Enum for type-checking
    referrer: dict = {}
    balance: int = 0
    purchase_amount: int = 0
    purchase_history: list = Field(default_factory=list)  # Avoid mutable default arguments

    @property
    def referral_link(self):
        bot_username = config.get_username()
        return f'https://t.me/{bot_username}?start=refu{self.id}'

    @property
    def referral_amount(self):
        return config.get_db().users.count_documents({'referrer.id': self.id})

    @property
    def subscriptions(self):
        sorted_subscriptions = config.get_db().subscriptions.find({'user_id': self.id}).sort('active',
                                                                                             pymongo.DESCENDING)
        return [Subscription.model_validate(data) for data in sorted_subscriptions]

    def change_role(self, role: str) -> bool:
        """Change the user's role if it's a valid role."""
        try:
            self.role = Roles(role)  # This will raise a ValueError if the role is not in the Roles Enum
            return True
        except ValueError:
            return False

    def add_balance(self, amount: int) -> int:
        """Add balance to user's current balance."""
        self.balance += amount
        return self.balance

    def model_dump(self, **kwargs) -> dict:
        """Get a dict representation with the role as an Enum."""
        output = super().model_dump(by_alias=True, **kwargs)
        output['role'] = self.role.value
        return output

    class Config:
        arbitrary_types_allowed = True
