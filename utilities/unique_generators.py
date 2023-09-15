import random
import string
import uuid

from bson import ObjectId, Binary
from configuration import Config

config = Config()
subscriptions_db = config.get_db().subscriptions


def generate_unique_uuid(collection):
    """
    Generate a unique ObjectId that doesn't exist in the provided MongoDB collection.

    Args:
    - collection (pymongo.collection.Collection): The MongoDB collection to check against.

    Returns:
    - bson.ObjectId: A unique ObjectId.
    """
    while True:
        new_id = uuid.uuid4()
        if not collection.find_one({'_id': new_id}):
            return new_id


def generate_unique_email(server_id: ObjectId) -> str:
    """
    Generate a unique email address with a local-part of 10 characters.

    Returns:
    - str: A unique email address.
    """
    # Characters we'll use to generate the email
    characters = string.ascii_letters + string.digits

    while True:
        local_part = ''.join(random.choice(characters) for _ in range(10))
        if not subscriptions_db.find_one({f'servers.{server_id}': local_part}):
            return local_part
