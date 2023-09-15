import re
from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from configuration import Config
from models.product import Product, Status
from models.user import Roles
from utilities.user_handlers import process_user

# Constants
BUTTON_HEADERS = ["🎲 مضرب هزینه", "⚖️ موجودی"]
RETURN_BUTTON = "🖥️ بازگشت به پنل"
CHANGE_STATUS_BUTTON = '📔 تغییر وضعیت نمایش'
NOT_A_BUTTON_DATA = "notabutton"
STATUS_BUTTONS = {
    Status.Shop: '🛒 فقط خرید',
    Status.Test: '🧪 فقط تست',
    Status.Both: '🛒🧪 خرید و تست'
}

config = Config()
products_db = config.get_db().products


def get_status_text(product_status):
    return {
        Status.Shop: "فقط خرید",
        Status.Test: "فقط تست",
        Status.Both: "تست و خرید"
    }.get(product_status, "نامشخص")


def fetch_product_from_query(query_data):
    match = re.findall(r"\{(.*?)}", query_data)
    product_id = ObjectId(match[0])
    return Product.model_validate(products_db.find_one({'_id': product_id}))


async def is_admin_or_deny(query, user):
    if user.role != Roles.Admin:
        await query.answer('شما ادمین نیستید!')
        return True
    return False


async def control_products(update: Update, context):
    query = update.callback_query
    user = process_user(query.from_user, context)

    if await is_admin_or_deny(query, user):
        return

    product = fetch_product_from_query(query.data)
    if not product:
        return await query.answer('این محصول وجود ندارد!')

    status_text = get_status_text(product.status)
    text = f"🕹 کنترل محصول *{product.name}*. (_{status_text}_)"
    keyboard = [
        [InlineKeyboardButton(header, callback_data=NOT_A_BUTTON_DATA) for header in BUTTON_HEADERS],
        [InlineKeyboardButton(value, callback_data=NOT_A_BUTTON_DATA) for value in [f"x{product.price_multiplier}", f"{product.stock}x"]],
        [InlineKeyboardButton(CHANGE_STATUS_BUTTON, callback_data=f'control-products_status{{{product.mongo_id}}}{{}}')],
        [InlineKeyboardButton(RETURN_BUTTON, callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def change_product_status(update: Update, context):
    query = update.callback_query
    user = process_user(query.from_user, context)

    if await is_admin_or_deny(query, user):
        return

    product = fetch_product_from_query(query.data)
    if not product:
        return await query.answer('این محصول وجود ندارد!')
    await query.answer()
    match = re.findall(r"\{(.*?)}", query.data)

    if match[1]:
        products_db.update_one({'_id': {'$ne': product.mongo_id}, 'status': {'$in': [Status.Both.value, Status.Test.value]}}, {'$set': {'status': Status.Shop.value}})

        product.change_status(match[1])
        products_db.update_one({'_id': product.mongo_id}, {'$set': product.model_dump()})
        status_text = get_status_text(product.status)
        text = f"📔 وضعیت نمایش محصول به *{status_text}* تغییر یافت."
        keyboard = [[InlineKeyboardButton(RETURN_BUTTON, callback_data="menu")]]
    else:
        status_text = get_status_text(product.status)
        text = f"📔 تغییر وضعیت نمایش محصول *{product.name}*. (_{status_text}_)"
        append = [InlineKeyboardButton(STATUS_BUTTONS[status], callback_data=f'control-products_status{{{product.mongo_id}}}{{{status.value}}}') for status in Status if status != product.status]
        keyboard = [append, [InlineKeyboardButton(RETURN_BUTTON, callback_data="menu")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
