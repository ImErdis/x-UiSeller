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


async def connect_url(update: Update, context):
    """
    Respond with connection URLs based on the user's subscriptions.
    """

    # Process the user's query and retrieve user data
    query = update.callback_query
    user = process_user(query.from_user, context)

    # Extract the subscriptions ID from the query data
    subscription_id_match = re.findall(r"\{(.*?)}", query.data)
    if not subscription_id_match:
        return await query.answer('Invalid data format. Please contact administrator')

    # Decode the subscriptions ID and fetch the active subscriptions for the user
    subscription_id = uuid.UUID(bytes=base64.b64decode(subscription_id_match[0].encode() + b'=='))
    filter_criteria = {
        'user_id': user.id,
        '_id': subscription_id,
        'active': True
    }
    subscription_data = subscriptions_db.find_one(filter_criteria)

    # Ensure the subscriptions exists
    if not subscription_data:
        return await query.answer('این اشتراک وجود ندارد/غرفعال است')

    # Inform the user about the ongoing process
    await query.answer('درحال ساخت لینک ها')

    # Convert the database subscriptions data to the Subscription model
    subscription = Subscription.model_validate(subscription_data)

    # Prepare the response message with the subscriptions links
    text = f'🔗 لینک های *اتصال*: \n\n{subscription.get_links_message()}'

    # Set up inline keyboard buttons for the user response
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the prepared message to the user
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
