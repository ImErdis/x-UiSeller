import re
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.referral import Referral

config = Config('configuration.yaml')
referrals_db = config.get_db().referrals

NAME, SERVERS, PRICE_MULTIPLIER, STOCK = range(4)
OBJECTID_PATTERN = re.compile(r'[a-fA-F0-9]{24}')


async def add_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    return await _send_message(query, "لطفا اسم مورد نظرتون برای 📨 *رفرال* را ارسال کنید.", NAME)


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    referral = Referral(name=f"{update.message.text}")
    referrals_db.insert_one(referral.model_dump(by_alias=True))

    text = f"""✅ رفرال با *موفقیت* اضافه شد.
    
    🔋 لینک *دعوت*:
`{referral.link}`
    """

    return await _send_message(update.message, text, ConversationHandler.END)


async def _send_message(target, text, next_state):
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:  # assuming it's a query object
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return next_state


conv_handler = ConversationHandler(
    per_message=False,
    entry_points=[CallbackQueryHandler(add_referral, pattern='^create-referrals$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^menu$")],
    allow_reentry=True
)
