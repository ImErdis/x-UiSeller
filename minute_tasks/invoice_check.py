import base64
import hashlib
import json
from typing import Optional

import requests
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

from configuration import Config
from models.invoice import InvoiceResponse

config = Config()
invoices_db = config.get_db().invoices
invoices_queue = config.get_db().invoice_queue
users = config.get_db().users

# API setup
API_ENDPOINT = "https://api.cryptomus.com/v1/payment/info"


def add_job(order_id, user_data) -> bool:
    invoices_queue.insert_one({'order_id': order_id, 'user_data': user_data})
    return True


def generate_sign(api_key: str, data: dict) -> str:
    # Convert the data dictionary to a JSON string
    json_data = json.dumps(data)  # No whitespace in JSON

    # Generate the sign header
    return hashlib.md5(
        (base64.b64encode(json_data.encode()) + api_key.encode()).decode('utf-8').encode('utf-8')).hexdigest()


def check_order_status(order_id: str) -> InvoiceResponse:
    """
    Check the status of the order from the API.
    """
    data = {"order_id": order_id}
    headers = {
        'merchant': config.merchant_uuid,
        'sign': generate_sign(config.payment_key, data),
        'Content-Type': 'application/json'
    }
    response = requests.post(API_ENDPOINT, headers=headers, json=data)
    if response.status_code == 200:
        return InvoiceResponse.model_validate(response.json()["result"])
    else:
        # Handle error or raise an exception
        return None


def update_order_status_in_db(invoice: InvoiceResponse):
    """
    Update the status of the order in the MongoDB database.
    """
    invoices_db.update_one({"_id": invoice.order_id}, {"$set": invoice.model_dump(mongo=True)})


async def process_invoice(bot: Bot, order_id: str) -> Optional[InvoiceResponse]:
    """
    Process an individual invoice and update the database if necessary.
    """
    invoice = check_order_status(order_id)
    if not invoice:
        return None

    update_order_status_in_db(invoice)
    return invoice if invoice.is_final else None


async def send_notification(bot: Bot, user_id: int, money: int, user_data: dict):
    """
    Send a notification to the user about the updated balance.
    """
    text = f"حساب شما به مقدار *💰 {money:,} تومان* شارژ شد."
    keyboard = []

    required_keys = ['product', 'traffic', 'duration']
    if all(key in user_data.keys() for key in required_keys):
        keyboard.append([InlineKeyboardButton('🛍 ادامه خرید اشتراک', callback_data='buy-subscriptions{continue}')])
    keyboard.append([InlineKeyboardButton("🖥️ پنل", callback_data="menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(user_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')


async def cron_job(bot: Bot):
    """
    The function to be run by the cron job every minute.
    """
    orders = invoices_db.find({"is_final": False})
    for order in orders:
        order_id = order["_id"]
        final_invoice = await process_invoice(bot, order_id)
        if final_invoice:
            money = int(final_invoice.additional_data)
            user_id = int(final_invoice.order_id.split('_')[0])
            status = final_invoice.payment_status in ['paid', 'paid_over']
            invoice = invoices_queue.find_one({'order_id': final_invoice.order_id})

            if invoice and status:
                users.update_one({'_id': user_id}, {'$inc': {'balance': money}})
                await send_notification(bot, user_id, money, invoice['user_data'])
            invoices_queue.delete_one({'order_id': final_invoice.order_id})
