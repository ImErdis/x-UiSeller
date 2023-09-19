import base64
import datetime
import re
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, helpers
from configuration import Config
from models.subscription import Subscription
from models.user import Roles
from utilities.user_handlers import process_user

config = Config()
subscriptions_db = config.get_db().subscriptions


async def control(update: Update, context):
    """Sends a message with Contact information."""

    # Process user data and retrieve query
    query = update.callback_query
    user = process_user(query.from_user, context)

    if user.role != Roles.Admin:
        return

    match = re.findall(r"\{(.*?)}", query.data)
    user = int(match[0])

    await query.answer()

    reply_markup = InlineKeyboardMarkup(create_keyboard(remaining_traffic, remaining_days, subscription))

    # Send the message with inline keyboard
    await query.edit_message_text(text.replace("-", "\\-"), reply_markup=reply_markup, parse_mode='MarkdownV2')
