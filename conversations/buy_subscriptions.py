import datetime
import re
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, helpers
from telegram.ext import (ContextTypes, ConversationHandler, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.product import Status, Product
from models.server import Server
from models.subscription import Subscription
from models.user import User

config = Config('configuration.yaml')
products_db = config.get_db().products
subscriptions_db = config.get_db().subscriptions
TRAFFIC, TIME, CONFIRM, FINALIZE_PURCHASE = range(4)


def generate_pagination_buttons(page: int, count: int, base_callback: str) -> list[InlineKeyboardButton]:
    """
    Generate pagination buttons for navigation.
    """
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("صفحه قبل ⬅️", callback_data=f'{base_callback}{{{page - 1}}}'))
    if count - page * 10 > 0:
        buttons.append(InlineKeyboardButton("➡️ صفحه بعد", callback_data=f'{base_callback}{{{page + 1}}}'))
    return buttons


def get_products(page: int) -> list[Product]:
    """
    Fetch the list of in-stock products for the given page.
    """
    skip_count = (page - 1) * 10
    product_data = products_db.find({
        'status': {'$in': [Status.Both.value, Status.Shop.value]},
        'stock': {'$gt': 0}  # Products that are in stock
    }).skip(skip_count).limit(10)

    return [Product.model_validate(data) for data in product_data]


async def buy_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for the conversation to buy subscriptions.
    """
    query = update.callback_query

    # Extract the page number from the callback data
    match = re.findall(r"\{(.*?)}", query.data)
    page = int(match[0])

    # Fetch the products for the given page
    products = get_products(page)

    # Check if there are no products then return with an error
    if not products:
        return await query.answer('محصولی برای خرید وجود ندارد.')

    # Announce to user that the products are being fetched
    await query.answer('درحال دریافت محصولات...')

    # Setup context.user_data for the conversation
    context.user_data['subscription'] = {}

    # Define text
    text = "لطفا 🛍 *محصول* مورد نظرتون را انتخاب کنید.\n\n"

    # Prepare the keyboard
    keyboard = []
    headers = ["🔍 اسم", "💸 طرح پایه"]
    for product in products:
        text += f"🔸 *{product.name}*: _{'_, _'.join([Server.model_validate(data).name for data in product.servers_documents])}_\n"
        name_button = InlineKeyboardButton(f'{product.name}',
                                           callback_data=f'buy-subscription_product{{{product.mongo_id}}}')
        keyboard.append([name_button])

    # Organizing buttons
    header_buttons = [InlineKeyboardButton(header, callback_data="notabutton") for header in headers]
    pagination_buttons = generate_pagination_buttons(page, products_db.count_documents(
        {'status': {'$in': [Status.Both.value, Status.Shop.value]}}), "buy-subscription")
    return_button = [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]

    keyboard = [header_buttons] + keyboard + [pagination_buttons] + [return_button]

    return await _send_message(query, InlineKeyboardMarkup(keyboard), text, TRAFFIC)


async def product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Extract the product ID from the callback data
    match = re.findall(r"\{(.*?)}", query.data)
    product_id = ObjectId(match[0])

    # Fetch the product data
    product_data = products_db.find_one({'_id': product_id})
    if not product_data:
        return await query.answer('محصول مورد نظر یافت نشد.')

    # Convert the product data to the Product model
    product = Product.model_validate(product_data)

    # Update user data
    context.user_data['subscription']['product'] = product.mongo_id

    # Prepare the keyboard
    keyboard = []
    headers = ["🔋 ترافیک", "💸 قیمت"]
    for plan in config.traffic_plans:
        price = round(plan['price'] * product.price_multiplier)
        keyboard.append([InlineKeyboardButton(f'{plan["traffic"]:,}G',
                                              callback_data=f'buy-subscription_traffic{{{plan["traffic"]}}}'),
                         InlineKeyboardButton(f'{price:,}T',
                                              callback_data=f'buy-subscription_traffic{{{plan["traffic"]}}}')])

    # Organizing buttons
    header_buttons = [InlineKeyboardButton(header, callback_data="notabutton") for header in headers]
    return_button = [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    # custom_button = [InlineKeyboardButton("📋 سفارشی", callback_data="buy-subscription_custom-traffic")]
    keyboard = [header_buttons] + keyboard + [return_button]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🔋 *ترافیک* مورد نظرتون را انتخاب کنید."
    return await _send_message(query, reply_markup, text, TIME)


async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    traffic = 0
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Extract the traffic from the callback data
        match = re.findall(r"\{(.*?)}", query.data)
        traffic = int(match[0])

        # Calculate price for the selected traffic, Get the traffic price form the config.traffic_plans list
        traffic_price = next((plan['price'] for plan in config.traffic_plans if plan['traffic'] == traffic), None)
        # Fetch the product data
        product_data = products_db.find_one({'_id': context.user_data['subscription']['product']})
        if not product_data:
            return ConversationHandler.END

        # Convert the product data to the Product model
        product = Product.model_validate(product_data)
        base_price = round(traffic_price * product.price_multiplier)
    else:
        query = update.message
        traffic = int(update.message.text)

    # Update user data
    context.user_data['subscription']['traffic'] = traffic

    # Prepare the keyboard
    keyboard = []
    durations = [
        (1, "1 ماه"),  # 1 month
        (2, "2 ماه"),  # 2 months
        (3, "3 ماه"),  # 3 months
        (6, "6 ماه"),  # 6 months
        (12, "12 ماه")  # 12 months
    ]
    discounts = {
        3: 0.95,
        6: 0.90,
        12: 0.85
    }

    # Headers for durations
    headers = ["⏳ مدت زمان", "💸 قیمت"]
    header_buttons = [InlineKeyboardButton(header, callback_data="notabutton") for header in headers]
    keyboard.append(header_buttons)

    # Organizing buttons
    for duration, label in durations:
        price = base_price * duration
        if duration in discounts:
            price = round(price * discounts[duration])
        duration_button = InlineKeyboardButton(f'{label}', callback_data=f'buy-subscription_duration{{{duration}}}')
        price_button = InlineKeyboardButton(f'{price:,}T', callback_data=f'buy-subscription_duration{{{duration}}}')
        keyboard.append([duration_button, price_button])

    reselect_button = [InlineKeyboardButton("🔄 انتخاب دوباره ترافیک",
                                            callback_data=f"buy-subscription_product{{{context.user_data['subscription']['product']}}}")]
    keyboard.append(reselect_button)

    return_button = [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    keyboard.append(return_button)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "لطفا 🕒 *مدت زمان* مورد نظرتون را انتخاب کنید."
    return await _send_message(query, reply_markup, text, CONFIRM)


# Show the final price and get the confirmation to create the subscription
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Extract the duration from the callback data
    match = re.findall(r"\{(.*?)}", query.data)
    duration = int(match[0])

    # Calculate the final price using the selected product, traffic, and duration
    product_data = products_db.find_one({'_id': context.user_data['subscription']['product']})
    if not product_data:
        await query.answer('محصول مورد نظر یافت نشد.')
        return ConversationHandler.END

    # Convert the product data to the Product model
    product = Product.model_validate(product_data)
    traffic_price = next((plan['price'] for plan in config.traffic_plans if
                          plan['traffic'] == context.user_data['subscription']['traffic']), None)
    base_price = round(traffic_price * product.price_multiplier)
    final_price = base_price * duration

    # Update user data
    context.user_data['subscription']['duration'] = duration

    # Check for discounts based on duration
    discounts = {
        3: 0.95,
        6: 0.90,
        12: 0.85
    }
    if duration in discounts:
        final_price = round(final_price * discounts[duration])

    # Prepare the message text
    text = f"💰 *هزینه نهایی*: {final_price:,}T \n"
    text += "آیا مایل به ادامه خرید و پرداخت هزینه می باشید؟"

    # Prepare the keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ بله", callback_data=f'finalize_purchase'),
            InlineKeyboardButton("❌ خیر", callback_data=f'cancel')
        ],
        [InlineKeyboardButton("🔄 انتخاب دوباره زمان",
                              callback_data=f'buy-subscription_traffic{{{context.user_data["subscription"]["traffic"]}}}')],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    return await _send_message(query, reply_markup, text, FINALIZE_PURCHASE)


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


# This function will check user's balance, create the subscription, or show a top-up button.
async def finalize_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id

    # Retrieve user from the database
    user_data = config.get_db().users.find_one({'_id': user_id})
    user = User.model_validate(user_data)

    # Calculate the final price from the user's conversation data
    product_data = products_db.find_one({'_id': context.user_data['subscription']['product']})
    if not product_data:
        await query.answer('محصول مورد نظر یافت نشد.')
        return ConversationHandler.END

    # Convert the product data to the Product model
    product = Product.model_validate(product_data)
    traffic_price = next((plan['price'] for plan in config.traffic_plans if
                          plan['traffic'] == context.user_data['subscription']['traffic']), None)
    base_price = round(traffic_price * product.price_multiplier)
    final_price = base_price * context.user_data['subscription']['duration']
    discounts = {
        3: 0.95,
        6: 0.90,
        12: 0.85
    }
    duration = context.user_data['subscription']['duration']
    if duration in discounts:
        final_price = round(final_price * discounts[duration])

    # Check if the user has enough balance
    if user.balance >= final_price:
        # Here, you should handle the logic of creating the subscription, updating user's balance, etc.
        user.balance -= final_price
        user.purchase_amount += final_price

        # Count the existing subscriptions for the user
        existing_subscriptions_count = subscriptions_db.count_documents({'user_id': user.id})

        # Append the count to the subscription name
        subscription_name = f"{query.from_user.full_name} #{existing_subscriptions_count + 1}"

        expiry_time = datetime.datetime.now() + datetime.timedelta(
            seconds=context.user_data['subscription']['duration'] * 30 * 24 * 60 * 60)
        subscription = Subscription(
            product=product.mongo_id,
            expiry_time=expiry_time,
            traffic=int(context.user_data['subscription']['traffic'] * context.user_data['subscription']['duration']),
            name=subscription_name,
            user_id=user.id
        )

        # Add the servers to the subscription and initiate it
        subscription.add_servers([Server.model_validate(server) for server in product.servers_documents])
        subscription.initiate_on_servers()
        subscriptions_db.insert_one(subscription.model_dump(by_alias=True))

        # Update product's stock
        products_db.update_one({'_id': product.mongo_id}, {'$inc': {'stock': -1}})

        # Updating user's balance and purchase amount in the database
        config.get_db().users.update_one({'_id': user_id},
                                         {'$set': {'balance': user.balance, 'purchase_amount': user.purchase_amount}})

        await query.answer("خرید با موفقیت انجام شد!")

        # Calculate remaining traffic and days
        remaining_traffic = round(subscription.traffic - subscription.usage, 2)
        remaining_days = (subscription.expiry_time - datetime.datetime.now()).days

        # Compose the message
        text = (
            f"✏️ مشخصات *اشتراک*\\.\n\n"
            f"- 📮 *نام*: _{helpers.escape_markdown(subscription.name, version=2)}_\n"
            f"- 🔑 *آیدی*: `{subscription.mongo_id}`\n\n"
            f"🌐 لینک *اشتراک*:\n"
            f"`{config.subscription_domain}/subscription?uuid={subscription.mongo_id}`"
        )

        reply_markup = InlineKeyboardMarkup(create_keyboard(remaining_traffic, remaining_days, subscription))

        # Send the message with inline keyboard
        await query.edit_message_text(text.replace("-", "\\-"), reply_markup=reply_markup, parse_mode='MarkdownV2')
        return ConversationHandler.END

    else:
        # User doesn't have enough balance, show the top-up button
        keyboard = [
            [InlineKeyboardButton("💳 شارژ حساب", callback_data="topup")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "❌ موجودی حساب شما کافی نمی‌باشد.\nلطفا حساب خود را شارژ کنید."

        return await _send_message(query, reply_markup, text, ConversationHandler.END)


async def _send_message(target, reply_markup, text, next_state):
    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:  # assuming it's a query object
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return next_state


conv_handler = ConversationHandler(
    per_message=False,
    entry_points=[CallbackQueryHandler(buy_subscriptions, pattern='^buy-subscriptions{')],
    states={
        TRAFFIC: [CallbackQueryHandler(product, pattern='^buy-subscription_product{')],
        # CUSTOM_TRAFFIC: [CallbackQueryHandler(custom_traffic, pattern='^buy-subscription_custom-traffic$')],
        TIME: [
            CallbackQueryHandler(time, pattern='^buy-subscription_traffic{')
        ],
        CONFIRM: [CallbackQueryHandler(confirm, pattern='^buy-subscription_duration{'),
                  CallbackQueryHandler(product, pattern='^buy-subscription_product{')],
        FINALIZE_PURCHASE: [CallbackQueryHandler(finalize_purchase, pattern='^finalize_purchase$'),
                            CallbackQueryHandler(time, pattern='^buy-subscription_traffic{')]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^cancel$")],
    allow_reentry=True
)
