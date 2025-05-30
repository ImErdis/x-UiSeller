import base64
import datetime
import re
import uuid

from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, helpers
from telegram.ext import (ContextTypes, ConversationHandler, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.product import Status, Product
from models.server import Server
from models.subscription import Subscription
from models.user import User
from utilities.subscription_utilites import create_keyboard

config = Config('configuration.yaml')
products_db = config.get_db().products
subscriptions_db = config.get_db().subscriptions
TRAFFIC, TIME, CONFIRM, FINALIZE_PURCHASE = range(4)


def is_valid_uuid4(uuid_string):
    """
    Check if a string is a valid UUID version 4.
    """
    try:
        # Convert the string to a UUID and check if it's version 4.
        return uuid.UUID(bytes=base64.b64decode(uuid_string.encode() + b'==', ), version=4)
    except ValueError:
        # If it's a ValueError, then the string is not a valid UUID.
        return False


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
    Entry point for the conversation to buy subscriptions or renew them.
    """
    query = update.callback_query

    # Check if inside the query is UUID or not
    match = re.findall(r"\{(.*?)}", query.data)

    # Check if match[0] is uuid or number
    if is_valid_uuid4(match[0]):
        subscription_id = is_valid_uuid4(match[0])

        # Fetch the subscription data
        subscription_data = subscriptions_db.find_one(
            {'_id': subscription_id, 'user_id': update.effective_user.id, 'active': False})

        # Check if the subscription exists
        if not subscription_data:
            await query.answer('این اشتراک وجود ندارد.')
            return ConversationHandler.END

        # Add the subscription to the context
        context.user_data['subscription'] = {'_id': subscription_id}

        # Set the page to 1
        page = 1
    else:
        page = int(match[0])

    # Fetch the products for the given page
    products = get_products(page)

    # Check if there are no products then return with an error
    if not products:
        await query.answer('محصولی برای خرید وجود ندارد.')
        return ConversationHandler.END

    # Announce to user that the products are being fetched
    await query.answer('درحال دریافت محصولات...')

    # Define text
    text = "لطفا 🛍 *محصول* مورد نظرتون را انتخاب کنید.\n\n"

    # Prepare the keyboard
    keyboard = []
    headers = ["🔍 اسم"]
    for product in products:
        text += f"🔸 *{product.name}*: _{'_, _'.join([Server.model_validate(data).name for data in product.servers_documents])}_\n"
        name_button = InlineKeyboardButton(f'{product.name}',
                                           callback_data=f'renew-subscription_product{{{product.mongo_id}}}')
        keyboard.append([name_button])

    # Organizing buttons
    header_buttons = [InlineKeyboardButton(header, callback_data="notabutton") for header in headers]
    pagination_buttons = generate_pagination_buttons(page, products_db.count_documents(
        {'status': {'$in': [Status.Both.value, Status.Shop.value]}}), "renew-subscription")
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
    for plan in product.traffic_plans:
        price = round(plan['price'] * product.price_multiplier)
        keyboard.append([InlineKeyboardButton(f'{plan["traffic"]:,}G',
                                              callback_data=f'renew-subscription_traffic{{{plan["traffic"]}}}'),
                         InlineKeyboardButton(f'{price:,}T',
                                              callback_data=f'renew-subscription_traffic{{{plan["traffic"]}}}')])

    # Organizing buttons
    header_buttons = [InlineKeyboardButton(header, callback_data="notabutton") for header in headers]
    return_button = [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    # custom_button = [InlineKeyboardButton("📋 سفارشی", callback_data="buy-subscription_custom-traffic")]
    keyboard = [header_buttons] + keyboard + [return_button]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🔋 *ترافیک* مورد نظرتون را انتخاب کنید."
    return await _send_message(query, reply_markup, text, TIME)


async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        # Extract the traffic from the callback data
        match = re.findall(r"\{(.*?)}", query.data)
        traffic = int(match[0])
        # Fetch the product data
        product_data = products_db.find_one({'_id': context.user_data['subscription']['product']})
        if not product_data:
            return ConversationHandler.END

        # Convert the product data to the Product model
        product = Product.model_validate(product_data)

        # Calculate price for the selected traffic, Get the traffic price form the config.traffic_plans list
        traffic_price = next((plan['price'] for plan in product.traffic_plans if plan['traffic'] == traffic), None)
        if traffic_price is None:
            await query.answer('محصول مورد نظر یافت نشد.')
            return ConversationHandler.END
        await query.answer()
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
        duration_button = InlineKeyboardButton(f'{label}', callback_data=f'renew-subscriptions_duration{{{duration}}}')
        price_button = InlineKeyboardButton(f'{price:,}T', callback_data=f'renew-subscriptions_duration{{{duration}}}')
        keyboard.append([duration_button, price_button])

    reselect_button = [InlineKeyboardButton("🔄 انتخاب دوباره ترافیک",
                                            callback_data=f"renew-subscription_product{{{context.user_data['subscription']['product']}}}")]
    keyboard.append(reselect_button)

    return_button = [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    keyboard.append(return_button)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "لطفا 🕒 *مدت زمان* مورد نظرتون را انتخاب کنید."
    return await _send_message(query, reply_markup, text, CONFIRM)


# Show the final price and get the confirmation to create the subscription
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    match = re.findall(r"\{(.*?)}", query.data)
    duration = context.user_data['duration'] if match[0] == 'continue' else int(match[0])

    # Calculate the final price using the selected product, traffic, and duration
    product_data = products_db.find_one({'_id': context.user_data['subscription']['product']})
    if not product_data:
        await query.answer('محصول مورد نظر یافت نشد.')
        return ConversationHandler.END

    # Check if users subscription is inactive
    subscription_data = subscriptions_db.find_one({'_id': context.user_data['subscription']['_id'], 'active': False})
    if not subscription_data:
        await query.answer('این اشتراک وجود ندارد.')
        return ConversationHandler.END

    # Convert the product data to the Product model
    product = Product.model_validate(product_data)
    traffic_price = next((plan['price'] for plan in product.traffic_plans if
                          plan['traffic'] == context.user_data['subscription']['traffic']), None)
    if traffic_price is None:
        await query.answer('محصول مورد نظر یافت نشد.')
        return ConversationHandler.END
    await query.answer()
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
    text += '\n\n'
    text += f"_{context.user_data['subscription']['traffic']:,}GB_-_{context.user_data['subscription']['duration']}M_"

    # Prepare the keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ بله", callback_data=f'finalize_purchase'),
            InlineKeyboardButton("❌ خیر", callback_data=f'cancel')
        ],
        [InlineKeyboardButton("🔄 انتخاب دوباره زمان",
                              callback_data=f'renew-subscription_traffic{{{context.user_data["subscription"]["traffic"]}}}')],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    return await _send_message(query, reply_markup, text, FINALIZE_PURCHASE)


# This function will check user's balance, create the subscription, or show a top-up button.
async def finalize_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id

    # Check if 'subscription' is in context.user_data
    if 'subscription' not in context.user_data or context.user_data['subscription'] is None:
        await query.answer("There was an error processing your request. Please try again.")
        return ConversationHandler.END

    # Check if users subscription is inactive
    subscription_data = subscriptions_db.find_one({'_id': context.user_data['subscription']['_id'], 'active': False})
    if not subscription_data:
        await query.answer('این اشتراک وجود ندارد.')
        return ConversationHandler.END

    # Convert the subscription data to the Subscription model
    subscription = Subscription.model_validate(subscription_data)

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
    traffic_price = next((plan['price'] for plan in product.traffic_plans if
                          plan['traffic'] == context.user_data['subscription']['traffic']), None)
    if traffic_price is None:
        await query.answer('محصول مورد نظر یافت نشد.')
        return ConversationHandler.END
    await query.answer()
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

        expiry_time = datetime.datetime.now() + datetime.timedelta(
            seconds=context.user_data['subscription']['duration'] * 30 * 24 * 60 * 60)
        mongo_id = subscription.mongo_id
        subscription = Subscription(
            mongo_id=subscription.mongo_id,
            product=product.mongo_id,
            expiry_time=expiry_time,
            traffic=int(context.user_data['subscription']['traffic'] * context.user_data['subscription']['duration']),
            name=subscription.name,
            user_id=user.id
        )
        subscription.mongo_id = mongo_id

        # Add the servers to the subscription and initiate it
        subscription.add_servers([Server.model_validate(server) for server in product.servers_documents])
        subscription.initiate_on_servers()
        subscriptions_db.update_one({'_id': subscription.mongo_id}, {'$set': subscription.model_dump(by_alias=True)})
        # Update product's stock
        products_db.update_one({'_id': product.mongo_id}, {'$inc': {'stock': -1}})

        # Updating user's balance and purchase amount in the database
        config.get_db().users.update_one({'_id': user_id},
                                         {'$set': {'balance': user.balance, 'purchase_amount': user.purchase_amount}})
        del context.user_data['subscription']

        await query.answer("خرید با موفقیت انجام شد!")

        # Calculate remaining traffic and days
        remaining_traffic = round(subscription.traffic - subscription.usage, 2)
        remaining_seconds = (subscription.expiry_time - datetime.datetime.now()).total_seconds()

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
        return ConversationHandler.END

    else:
        # User doesn't have enough balance, show the top-up button
        keyboard = [
            [InlineKeyboardButton("💳 شارژ حساب", callback_data=f"topup{{{final_price}}}")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
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
    entry_points=[CallbackQueryHandler(confirm, pattern='^renew-subscriptions{continue}$'),
                  CallbackQueryHandler(buy_subscriptions, pattern='^renew-subscriptions{')],
    states={
        TRAFFIC: [CallbackQueryHandler(product, pattern='^renew-subscription_product{')],
        # CUSTOM_TRAFFIC: [CallbackQueryHandler(custom_traffic, pattern='^buy-subscription_custom-traffic$')],
        TIME: [
            CallbackQueryHandler(time, pattern='^renew-subscription_traffic{')
        ],
        CONFIRM: [CallbackQueryHandler(confirm, pattern='^renew-subscriptions_duration{'),
                  CallbackQueryHandler(product, pattern='^renew-subscription_product{')],
        FINALIZE_PURCHASE: [CallbackQueryHandler(finalize_purchase, pattern='^finalize_purchase$'),
                            CallbackQueryHandler(time, pattern='^renew-subscription_traffic{')]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^cancel$")],
    allow_reentry=True
)
