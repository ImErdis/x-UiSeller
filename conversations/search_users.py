import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.user import User, Roles
from utilities.user_handlers import process_user

config = Config('configuration.yaml')
users_db = config.get_db().users

USER_ID = range(1)
OBJECTID_PATTERN = re.compile(r'[a-fA-F0-9]{24}')


async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    return await _send_message(query, "لطفا آیدی *یوزر* مورد نظرتون را ارسال کنید.", USER_ID)


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = process_user(update.message.from_user, context)

    if user.role != Roles.Admin:
        return ConversationHandler.END

    user = users_db.find_one({'_id': int(update.message.text)})
    if not user:
        return await _send_message(update.message, 'این آیدی در دیتابیس وجود ندارد.', ConversationHandler.END)

    user = User.model_validate(user)

    text = f"""💼 اطلاعات *یوزر*.

    🔢 *ایدی‌عددی*: `{user.id}`
    👥 *تعداد زیرمجموعه ها*: {user.referral_amount}
    🛍 *تعداد سرویس ها*: {len(user.subscriptions)}
    💎 *موجودی*: {user.balance:,} تومان

    🔋 لینک *دعوت* زیرمجموعه:
    `{user.referral_link}`"""

    keyboard = [
        [InlineKeyboardButton("➕ افزایش موجودی", callback_data=f"control-users_topup{{{user.id}}}")],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return await _send_message(update.message, text, ConversationHandler.END, reply_markup=reply_markup)


async def _send_message(target, text, next_state, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]])):
    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:  # assuming it's a query object
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return next_state


conv_handler = ConversationHandler(
    per_message=False,
    entry_points=[CallbackQueryHandler(search_user, pattern='^search-users$')],
    states={
        USER_ID: [MessageHandler(filters.Regex(r'\d+'), user_id)]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^menu$")],
    allow_reentry=True
)
