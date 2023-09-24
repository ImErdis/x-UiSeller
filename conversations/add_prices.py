import re
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.prices import Prices

config = Config('configuration.yaml')
referrals_db = config.get_db().referrals

NAME, PLANS = range(2)


async def add_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['prices'] = {}
    return await _send_message(query, "لطفا اسم مورد نظرتون برای 📜 *قیمت ها* را ارسال کنید.", NAME)


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['prices']['name'] = update.message.text
    return await _send_message(update.message, f"""لطفا لیست 📜 *قیمت ها* را ارسال کنید.""", PLANS)


async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        list_dict = [{'traffic': int(line.split(" - ")[0].strip()), 'price': int(line.split(" - ")[1].strip())} for line in
                     update.message.text.strip().split("\n")]
    except:
        return await _send_message(update.message, f"""لطفا لیست 📜 *قیمت ها* را ارسال کنید.""", PLANS)

    prices = Prices(name=context.user_data['prices']['name'], plans=list_dict)
    prices.commit_changes()
    return await _send_message(update.message, f"✅ قیمت ها با *موفقیت* اضافه شد.", ConversationHandler.END)


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
    entry_points=[CallbackQueryHandler(add_prices, pattern='^create-prices$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        PLANS: [MessageHandler(filters.TEXT, plans)]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^menu$")],
    allow_reentry=True
)
