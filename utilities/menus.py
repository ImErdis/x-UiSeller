import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models.user import User, Roles
from models.server import Server
from models.product import Product, Status
from models.referral import Referral
from configuration import Config

config = Config('configuration.yaml')


def generate_pagination_buttons(page: int, count: int, base_callback: str) -> list:
    return [x for x in [
        InlineKeyboardButton("صفحه قبل ⬅️", callback_data=f'{base_callback}{{{page - 1}}}') if page > 1 else None,
        InlineKeyboardButton("➡️ صفحه بعد",
                             callback_data=f'{base_callback}{{{page + 1}}}') if count - page * 30 > 0 else None
    ] if x]


def fetch_from_db(db_name: str, model, page: int):
    db = config.get_db()[db_name]
    items = [model.model_validate(x) for x in db.find({}).skip((page - 1) * 30).limit(30)]
    count = db.count_documents({})
    return items, count


def start_menu(user: User) -> InlineKeyboardMarkup:
    test_subscription_available = config.get_db().products.find_one(
        {'status': {'$in': [Status.Test.value, Status.Both.value]}})

    admin_keyboard = [
        [InlineKeyboardButton('👥 لیست کاربران', callback_data="list-users{1}")],
        [InlineKeyboardButton('🛍 لیست محصولات', callback_data="list-products{1}"),
         InlineKeyboardButton('🎰 لیست سرور ها', callback_data="list-servers{1}")],
        [InlineKeyboardButton('📨 لیست رفرال ها', callback_data="list-referrals{1}")]
    ]

    user_keyboard = [
        [InlineKeyboardButton("🛍 خرید اشتراک", callback_data="buy-subscriptions{1}")],
        [InlineKeyboardButton("👥 لیست اشتراک ها", callback_data="list-subscriptions{1}"),
         InlineKeyboardButton("🔬 اشتراک تستی", callback_data="test-subscriptions"),
         InlineKeyboardButton("📋 اطلاعات حساب", callback_data="user_info")],
        [InlineKeyboardButton("📞 ارتباط با ما", callback_data="contact_info"),
         # InlineKeyboardButton("📘 راهنمای اتصال", callback_data="connect_info")
         ]
    ]

    if not test_subscription_available or user.subscriptions:
        test_subscription_button = InlineKeyboardButton("🔬 اشتراک تستی", callback_data="test-subscriptions")
        user_keyboard[1].remove(test_subscription_button)

    keyboard = admin_keyboard if user.role == Roles.Admin else user_keyboard
    return InlineKeyboardMarkup(keyboard)


def generate_list_markup(items: list, page: int, count: int, type_: str):
    keyboard = []

    # Depending on the type, adjust headers and item representation
    if type_ == "users":
        headers = ["🔍 آیدی عددی", "🎯 رفرال ها", "💸 مقدار خرید"]
        for user in items:
            keyboard.append([
                InlineKeyboardButton(f'{user.id}', callback_data=f'control-users{{{user.id}}}'),
                InlineKeyboardButton(f'{user.referral_amount}', callback_data=f'control-users{{{user.id}}}'),
                InlineKeyboardButton(f'{user.purchase_amount}', callback_data=f'control-users{{{user.id}}}')
            ])
    elif type_ == "servers":
        headers = ["🔍 اسم", "🎯 آیپی", "🪪 آیدی اینباند"]
        for server in items:
            keyboard.append([
                InlineKeyboardButton(f'{server.name}', callback_data=f'control-servers{{{server.mongo_id}}}'),
                InlineKeyboardButton(f'{server.ip_address}', callback_data=f'control-servers{{{server.mongo_id}}}'),
                InlineKeyboardButton(f'{server.inbound_id}', callback_data=f'control-servers{{{server.mongo_id}}}')
            ])
    elif type_ == "products":
        headers = ["🔍 اسم", "🎲 مضرب هزینه", "⚖️ موجودی"]
        for product in items:
            keyboard.append([
                InlineKeyboardButton(f'{product.name}', callback_data=f'control-products{{{product.mongo_id}}}'),
                InlineKeyboardButton(f'x{product.price_multiplier}',
                                     callback_data=f'control-products{{{product.mongo_id}}}'),
                InlineKeyboardButton(f'{product.stock}x', callback_data=f'control-products{{{product.mongo_id}}}')
            ])
    elif type_ == "referrals":
        headers = ["🔍 اسم", "⚖️ تعداد رفرال ها"]
        for referral in items:
            keyboard.append([
                InlineKeyboardButton(f'{referral.name}', callback_data=f'control-referrals{{{referral.mongo_id}}}'),
                InlineKeyboardButton(f'{referral.amount}',
                                     callback_data=f'control-referrals{{{referral.mongo_id}}}')
            ])
    elif type_ == "subscriptions":
        headers = ["🔍 اسم", "⚡️ حجم", "🎛 فعال"]
        for subscription in items:
            keyboard.append([
                InlineKeyboardButton(f'{subscription.name}', callback_data=f'control-subscriptions{{{subscription.uuid_decoded}}}'),
                InlineKeyboardButton(f'{round( subscription.usage, 2)}/{round(subscription.traffic, 2)} گیگابایت', callback_data=f'control-subscriptions{{{subscription.uuid_decoded}}}'),
                InlineKeyboardButton(f'{"✅" if subscription.active else "❌"}', callback_data=f'control-subscriptions{{{subscription.uuid_decoded}}}')
            ])

    # Add headers
    keyboard.insert(0, [InlineKeyboardButton(header, callback_data="notabutton") for header in headers])
    # Pagination buttons
    pagination = generate_pagination_buttons(page, count, f"list-{type_}")
    if pagination:
        keyboard.append(pagination)

    # Add additional buttons
    if type_ == "users":
        keyboard.extend([
            [InlineKeyboardButton("🔍 جست‌وجو کاربر", callback_data="search-users")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
        ])
    elif type_ == "servers":
        keyboard.extend([
            [InlineKeyboardButton("🔍 جست‌وجو سرور", callback_data="search-servers")],
            [InlineKeyboardButton("⚙️ اضافه کردن سرور", callback_data="create-servers")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
        ])
    elif type_ == "products":
        keyboard.extend([
            [InlineKeyboardButton("🔍 جست‌وجو محصول", callback_data="search-products")],
            [InlineKeyboardButton("⚙️ اضافه کردن محصول", callback_data="create-products")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
        ])
    elif type_ == "referrals":
        keyboard.extend([
            [InlineKeyboardButton("🔍 جست‌وجو رفرال", callback_data="search-products")],
            [InlineKeyboardButton("⚙️ اضافه کردن رفرال", callback_data="create-referrals")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
        ])
    elif type_ == "subscriptions":
        keyboard.extend([
            # [InlineKeyboardButton("🔍 جست‌وجو اشتراک", callback_data="search-subscriptions")],
            [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
        ])

    return InlineKeyboardMarkup(keyboard)


def users_list(page: int) -> InlineKeyboardMarkup:
    users, count = fetch_from_db("users", User, page)
    return generate_list_markup(users, page, count, "users")


def servers_list(page: int) -> InlineKeyboardMarkup:
    servers, count = fetch_from_db("servers", Server, page)
    return generate_list_markup(servers, page, count, "servers")


def products_list(page: int) -> InlineKeyboardMarkup:
    products, count = fetch_from_db("products", Product, page)
    return generate_list_markup(products, page, count, "products")


def referrals_list(page: int) -> InlineKeyboardMarkup:
    referrals, count = fetch_from_db("referrals", Referral, page)
    return generate_list_markup(referrals, page, count, "referrals")


def subscriptions_list(page: int, user: User) -> InlineKeyboardMarkup:
    subscriptions = user.subscriptions[(page - 1) * 30:page * 30]
    return generate_list_markup(subscriptions, page, len(user.subscriptions), "subscriptions")
