import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, helpers, Update
from configuration import Config
from models.product import Status, Product
from models.server import Server
from models.subscription import Subscription
from utilities.user_handlers import process_user

config = Config()
products_db = config.get_db().products
subscriptions_db = config.get_db().subscriptions


def create_keyboard(remaining_traffic, remaining_days, subscription):
    """Generate inline keyboard for the given subscription."""
    return [
        [InlineKeyboardButton(header, callback_data='notabutton') for header in
         ['⚡️ حجم باقی‌مانده', '⏳ زمان باقی‌مانده']],
        [InlineKeyboardButton(value, callback_data='notabutton') for value in
         [f'{remaining_traffic} گیگابایت', f'{remaining_days} روز']],
        [InlineKeyboardButton('🔗 لینک اتصال',
                              callback_data=f'connect_url-subscriptions{{{subscription.uuid_decoded}}}')],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]


async def get_test(update: Update, context):
    """Respond with contact information for testing purposes."""

    query = update.callback_query
    user = process_user(query.from_user, context)

    # Check for existing subscriptions
    if user.subscriptions:
        return await query.answer('شما قبلا از سرویس ما استفاده کرده اید!')

    # Find an available test product
    product_data = products_db.find_one({'status': {'$in': [Status.Both.value, Status.Test.value]}})
    if not product_data:
        return await query.answer('اشتراک تست موجود نمیباشد!')

    await query.answer('درحال ساخت اشتراک')

    # Validate the product data and create a new test subscription
    product = Product.model_validate(product_data)
    expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=config.test_time)
    subscription = Subscription(
        product=product.mongo_id,
        expiry_time=expiry_time,
        traffic=config.test_traffic,
        name=f'{query.from_user.full_name} Test',
        user_id=user.id
    )

    # Add the servers to the subscription and initiate it
    subscription.add_servers([Server.model_validate(server) for server in product.servers_documents])
    subscription.initiate_on_servers()
    subscriptions_db.insert_one(subscription.model_dump(by_alias=True))

    # Calculate remaining traffic and days
    remaining_traffic = round(subscription.traffic - subscription.usage, 2)
    remaining_days = (subscription.expiry_time - datetime.datetime.now()).days

    # Compose the message
    text = (
        f"✏️ مشخصات *اشتراک*\\.\n\n"
        f"- 📮 *نام*: _{helpers.escape_markdown(subscription.name, version=2)}_\n"
        f"- 🔑 *آیدی*: `{subscription.mongo_id}`\n\n"
        f"🌐 لینک *اشتراک*:\n"
        f"`{config.subscription_domain}/subscription?uuid={subscription.mongo_id}\n\n"
    )
    text += f'🔗 لینک های *اتصال*: \n\n{subscription.get_links_message()}'

    reply_markup = InlineKeyboardMarkup(create_keyboard(remaining_traffic, remaining_days, subscription))

    # Send the message with inline keyboard
    await query.edit_message_text(text.replace("-", "\\-"), reply_markup=reply_markup, parse_mode='MarkdownV2')
