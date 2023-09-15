import re
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler)
from callback.menu import menu
from configuration import Config
from models.server import Server
from models.product import Product

config = Config('configuration.yaml')
servers_db = config.get_db().servers
products_db = config.get_db().products

NAME, SERVERS, PRICE_MULTIPLIER, STOCK = range(4)
OBJECTID_PATTERN = re.compile(r'[a-fA-F0-9]{24}')


async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not servers_db.count_documents({}):
        return await _send_message(query, "❌ هیچگونه *سرور* ذر ربات موجود نیست. (_نیازمندی محصول حداقل 1 سرور است_)", ConversationHandler.END)
    context.user_data['product'] = {}
    return await _send_message(query, "لطفا اسم مورد نظرتون برای 🛍 *محصول* را ارسال کنید.", NAME)


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['product']['name'] = update.message.text
    return await _send_message(update.message, "لطفا آیدی 🌎 *سرور* های مورد نظر را ارسال کنید. (_در یک پیام_)", SERVERS)


async def servers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    object_ids = OBJECTID_PATTERN.findall(update.message.text)
    object_ids = [ObjectId(oid) for oid in object_ids]
    if not object_ids:
        return await _send_message(update.message,
                                   "لطفا آیدی 🌎 *سرور* های مورد نظر را ارسال کنید. (_هیچ آیدی ای پیدا در متن پیدا "
                                   "نشد_)",
                                   SERVERS)
    servers_list = [Server.model_validate(x) for x in list(servers_db.find({"_id": {"$in": object_ids}}))]
    if not servers_list:
        return await _send_message(update.message,
                                   "لطفا آیدی 🌎 *سرور* های مورد نظر را ارسال کنید. (_سرور ای با آیدی های داده شده "
                                   "پیدا نشد_)",
                                   SERVERS)
    context.user_data['product']['servers'] = [server.mongo_id for server in servers_list]
    servers_name = [x.name for x in servers_list]
    text = f"""لطفا مضرب 🪙 *هزینه محاسبه شده* را ارسال کنید.
    
🌎 سرور های دریافت شده:
_{'_, _'.join(servers_name)}_"""
    return await _send_message(update.message, text, PRICE_MULTIPLIER)


async def price_multiplier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['product']['price_multiplier'] = f"{update.message.text}"
    return await _send_message(update.message, "لطفا تعداد 🔋 *اشتراک های موجود اولیه* رو ارسال کنید.",
                               STOCK)


async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['product']['stock'] = f"{update.message.text}"
    product = Product.model_validate(context.user_data['product'])
    products_db.insert_one(product.model_dump())
    del context.user_data['product']
    return await _send_message(update.message, "✅ محصول با *موفقیت* اضافه شد.", ConversationHandler.END)


async def _send_message(target, text, next_state):
    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(target, Message):
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:  # assuming it's a query object
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return next_state


conv_handler = ConversationHandler(
    per_message=False,
    entry_points=[CallbackQueryHandler(add_product, pattern='^create-products$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        SERVERS: [MessageHandler(filters.TEXT, servers)],
        PRICE_MULTIPLIER: [MessageHandler(filters.Regex(r'^[+-]?\d+(\.\d+)?$'), price_multiplier)],
        STOCK: [MessageHandler(filters.Regex(r'^\+?[1-9]\d*$'), stock)]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^cancel$")],
    allow_reentry=True
)
