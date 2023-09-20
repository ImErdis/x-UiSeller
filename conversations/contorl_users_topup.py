import re
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (ContextTypes, ConversationHandler,
                          MessageHandler, filters, CallbackQueryHandler)
from callback.menu import menu
from callback.users.control import users_db
from configuration import Config
from models.referral import Referral
from models.user import User

config = Config('configuration.yaml')
referrals_db = config.get_db().referrals

AMOUNT = range(1)
OBJECTID_PATTERN = re.compile(r'[a-fA-F0-9]{24}')


async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    match = re.findall(r"\{(.*?)}", query.data)
    user = users_db.find_one({'_id': int(match[0])})

    if not user:
        return ConversationHandler.END

    context.user_data['control-users_topup'] = {'_id': user['_id']}
    return await _send_message(query, "لطفا مقدار 💰 *موجودی*(_تومان_) برای افزایش را ارسال کنید.", AMOUNT)


async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    money = int(update.message.text)
    user = users_db.find_one(
        {'_id': context.user_data['control-users_topup']['_id']})
    if not user:
        return ConversationHandler.END

    user = User.model_validate(user)
    balance = user.add_balance(money)
    users_db.update_one({'_id': user.id}, {'$set': user.model_dump()})

    text = f"یوزر مورد نظر با موفقیت 🔋 *شارژ* شد. _(موجودی جدید: {balance})_"

    return await _send_message(update.message, text, ConversationHandler.END)


async def _send_message(target, text, next_state):
    keyboard = [[InlineKeyboardButton(
        "🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:  # assuming it's a query object
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return next_state


conv_handler = ConversationHandler(
    per_message=False,
    entry_points=[CallbackQueryHandler(topup, pattern='^control-users_topup')],
    states={
        AMOUNT: [MessageHandler(filters.TEXT, amount)]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^cancel$")],
    allow_reentry=True
)
