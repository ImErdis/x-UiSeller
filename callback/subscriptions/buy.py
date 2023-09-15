import base64
import re
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from configuration import Config
from models.subscription import Subscription
from utilities.user_handlers import process_user

# Initialize configurations and database connection
config = Config('configuration.yaml')
subscriptions_db = config.get_db().subscriptions