from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)

from callback.menu import menu
from configuration import Config
from models.server import Server
from utilities import api_call

config = Config('configuration.yaml')
servers_db = config.get_db().servers

NAME, IP, PORT, USER, PASSWORD, INBOUND_ID, DOMAIN = range(7)


async def add_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data['server'] = {}
    return await _send_message(query, "لطفا اسم مورد نظرتون برای 🌎 *سرور* را ارسال کنید.", NAME)


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['name'] = update.message.text
    return await _send_message(update.message, "لطفا 🧶 *آیپی سرور* رو ارسال کنید.", IP)


async def ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['ip_address'] = update.message.text
    return await _send_message(update.message, "لطفا 🧦 *پورت پنل* رو ارسال کنید.", PORT)


async def port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['panel_port'] = update.message.text
    return await _send_message(update.message, "لطفا 🪪 *یوزرنیم پنل* رو ارسال کنید.", USER)


async def username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['panel_username'] = update.message.text
    return await _send_message(update.message, "لطفا 🔑 *پسورد پنل* رو ارسال کنید.", PASSWORD)


async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['panel_password'] = update.message.text
    return await _send_message(update.message, "لطفا 💡 *آیدی اینباند* رو ارسال کنید.", INBOUND_ID)


async def inbound_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    context.user_data['server']['inbound_id'] = update.message.text

    if servers_db.find_one(
            {'ip_address': context.user_data['server']['ip_address'], 'inbound_id': int(update.message.text)}):
        return await _send_message(update, '❌ لطفا *اینباند دیگری* را ارائه دهید. _(در سرور ها وجود دارد)_', INBOUND_ID)

    r = api_call.get_inbound(
        f"http://{context.user_data['server']['ip_address']}:{context.user_data['server']['panel_port']}",
        context.user_data['server']['panel_username'], context.user_data['server']['panel_password'],
        int(update.message.text))

    if r.status_code == 307:
        return await _send_message(update.message, "❌ لطفا *یوزرنیم* را ارائه دهید. _(یوزرنیم یا پسورد اشتباه است)_",
                                   USER)

    if r.status_code == 503:
        return await _send_message(update.message, "❌ لطفا *آیپی* را ارائه دهید. _(آیپی یا پورت اشتباه است)_", IP)

    if not r.json()['success']:
        return await _send_message(update.message, "❌ لطفا *اینباند دیگری* را ارائه دهید. _(اینباند وجود ندارد)_",
                                   INBOUND_ID)

    return await _send_message(update.message, "لطفا 🌐 *دامین* یا 🧶 *آیپی* برای اتصال رو ارسال کنید.", DOMAIN)


async def domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['server']['connect_domain'] = update.message.text

    server = Server.model_validate(context.user_data['server'])
    server.ip_address = str(server.ip_address)
    while servers_db.find_one({'_id': server.mongo_id}):
        server.mongo_id = ObjectId()

    servers_db.insert_one(server.model_dump(by_alias=True))

    del context.user_data['server']

    return await _send_message(update.message, "✅ سرور با *موفقیت* اضافه شد.", ConversationHandler.END)


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
    entry_points=[CallbackQueryHandler(add_server, pattern='^create-servers$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        IP: [MessageHandler(filters.Regex("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"), ip)],
        PORT: [MessageHandler(filters.Regex("^\d{1,6}$"), port)],
        USER: [MessageHandler(filters.TEXT, username)],
        PASSWORD: [MessageHandler(filters.TEXT, password)],
        INBOUND_ID: [MessageHandler(filters.Regex("^\d{1,6}$"), inbound_id)],
        DOMAIN: [MessageHandler(filters.TEXT, domain)],
    },
    fallbacks=[CallbackQueryHandler(menu, pattern="^cancel$")],
    allow_reentry=True
)
