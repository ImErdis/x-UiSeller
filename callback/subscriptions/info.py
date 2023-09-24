import base64
import datetime
import re
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, helpers

from configuration import Config
from models.subscription import Subscription
from utilities.subscription_utilites import create_keyboard
from utilities.user_handlers import process_user

config = Config()
subscriptions_db = config.get_db().subscriptions


async def info(update: Update, context):
    """Sends a message with Contact information."""

    # Process user data and retrieve query 
    query = update.callback_query
    user = process_user(query.from_user, context)

    # Extract the subscription ID from the callback data
    subscription_id_match = re.findall(r"\{(.*?)}", query.data)
    if not subscription_id_match:
        return await query.answer('Invalid data format. Please contact administrator')

    # Decode the subscription ID and get subscription data from the database
    subscription_id = uuid.UUID(bytes=base64.b64decode(subscription_id_match[0].encode() + b'=='))
    subscription_data = subscriptions_db.find_one({'user_id': user.id, '_id': subscription_id})

    if not subscription_data:
        return await query.answer('این اشتراک وجود ندارد/غرفعال است')

    await query.answer()

    # Convert database data to the Subscription model
    subscription = Subscription.model_validate(subscription_data)

    # Calculate remaining traffic and days
    remaining_traffic = round(subscription.traffic - subscription.usage, 2)
    remaining_seconds = (subscription.expiry_time - datetime.datetime.now()).seconds

    # Compose the message
    text = (
        f"✏️ مشخصات *اشتراک*\\.\n\n"
        f"- 📮 *نام*: _{helpers.escape_markdown(subscription.name, version=2)}_\n"
        f"- 🔑 *آیدی*: `{subscription.mongo_id}`\n\n"
        f"🌐 لینک *اشتراک*:\n"
        f"`{config.subscription_domain}/subscription?uuid={subscription.mongo_id}`"
    )

    reply_markup = InlineKeyboardMarkup(create_keyboard(remaining_traffic, remaining_seconds, subscription))

    # Send the message with inline keyboard
    await query.edit_message_text(text.replace("-", "\\-"), reply_markup=reply_markup, parse_mode='MarkdownV2')
