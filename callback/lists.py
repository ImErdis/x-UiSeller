import re
from telegram import Update
from configuration import Config
from models.user import User, Roles
from utilities.menus import products_list, servers_list, users_list, referrals_list, subscriptions_list, prices_list

# Load configuration from 'configuration.yaml'
config = Config('configuration.yaml')

# Access the 'users' database from the configuration
users = config.get_db().users


async def list_items(update: Update, context, item_type):
    """General function to list items (users, servers, products)"""
    query = update.callback_query
    await query.answer()

    user = User.model_validate(users.find_one({'_id': query.from_user.id}))

    # Conditional check to validate access
    if item_type == 'subscription':
        if user.role not in [Roles.Admin, Roles.Member]:
            return
    else:
        if user.role != Roles.Admin:
            return

    # Extract the page number from the callback data
    match = re.findall(r"\{(.*?)}", query.data)
    page = int(match[0])

    # Get the correct text and list based on the item type
    if item_type == 'user':
        text = "🗒 لیست کاربران *کنونی* ربات به شرح زیر میباشد."
        reply_markup = users_list(page)
    elif item_type == 'server':
        text = "🗒 لیست سرور های *کنونی* ربات به شرح زیر میباشد."
        reply_markup = servers_list(page)
    elif item_type == 'product':
        text = "🗒 لیست محصول های *کنونی* ربات به شرح زیر میباشد."
        reply_markup = products_list(page)
    elif item_type == 'referral':
        text = "🗒 لیست رفرال های *کنونی* ربات به شرح زیر میباشد."
        reply_markup = referrals_list(page)
    elif item_type == 'subscription':
        text = "👥 لیست *اشتراک ها*ی شما."
        reply_markup = subscriptions_list(page, user)
    elif item_type == 'prices':
        text = "🗒 لیست *قیمت ها* به شرح زیر میباشد."
        reply_markup = prices_list(page)

    # Edit the message with the updated text and reply markup
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def list_users(update: Update, context):
    """Sends a message with a list of current users."""
    await list_items(update, context, 'user')


async def list_servers(update: Update, context):
    """Sends a message with a list of current servers."""
    await list_items(update, context, 'server')


async def list_products(update: Update, context):
    """Sends a message with a list of current products."""
    await list_items(update, context, 'product')


async def list_referrals(update: Update, context):
    """Sends a message with a list of current referrals."""
    await list_items(update, context, 'referral')


async def list_subscriptions(update: Update, context):
    """Sends a message with a list of current subscriptions."""
    await list_items(update, context, 'subscription')


async def list_prices(update: Update, context):
    """Sends a message with a list of current subscriptions."""
    await list_items(update, context, 'prices')
