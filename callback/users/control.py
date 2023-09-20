import base64
import datetime
import re
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, helpers
from configuration import Config
from models.subscription import Subscription
from models.user import Roles, User
from utilities.user_handlers import process_user

config = Config()
subscriptions_db = config.get_db().subscriptions
users_db = config.get_db().users


async def control(update: Update, context):
    """Sends a message with Contact information."""

    # Process user data and retrieve query
    query = update.callback_query
    user = process_user(query.from_user, context)

    if user.role != Roles.Admin:
        return

    match = re.findall(r"\{(.*?)}", query.data)
    user = users_db.find_one({'_id': int(match[0])})
    if not user:
        return

    await query.answer()

    user = User.model_validate(user)

    text = f"""💼 اطلاعات *یوزر*.

    🔢 *ایدی‌عددی*: `{user.id}`
    👥 *تعداد زیرمجموعه ها*: {user.referral_amount}
    🛍 *تعداد سرویس ها*: {len(user.subscriptions)}
    💎 *موجودی*: {user.balance:,} تومان

    🔋 لینک *دعوت* زیرمجموعه:
    `{user.referral_link}`
    """

    keyboard = [
        [InlineKeyboardButton("➕ افزایش موجودی", callback_data=f"control-users_topup{{{user.id}}}")],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with inline keyboard
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
