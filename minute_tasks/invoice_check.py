import base64
import hashlib
import json
from typing import Optional

import httpx
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

from configuration import Config
from models.invoice import InvoiceResponse

config = Config()

# Initialize an async MongoDB client
client = AsyncIOMotorClient(config.mongo_uri)['xui']
invoices_db = client.invoices
invoices_queue = client.invoice_queue
users = client.users

API_ENDPOINT = "https://api.cryptomus.com/v1/payment/info"


async def add_job(order_id, user_data) -> bool:
    """
    Add a new job to the invoices_queue.

    Args:
        order_id (str): The ID of the order.
        user_data (dict): Data related to the user.

    Returns:
        bool: True if the job was added successfully, otherwise False.
    """
    await invoices_queue.insert_one({'order_id': order_id, 'user_data': user_data})
    return True


def generate_sign(api_key: str, data: dict) -> str:
    """
    Generate a cryptographic signature for API requests.

    Args:
        api_key (str): The API key.
        data (dict): The data to be signed.

    Returns:
        str: The generated signature.
    """
    json_data = json.dumps(data)
    return hashlib.md5(
        (base64.b64encode(json_data.encode()) + api_key.encode()).decode('utf-8').encode('utf-8')).hexdigest()


async def check_order_status(order_id: str) -> Optional[InvoiceResponse]:
    """
    Check the payment status of an order via the API.

    Args:
        order_id (str): The ID of the order.

    Returns:
        Optional[InvoiceResponse]: Returns the status if found, otherwise None.
    """
    data = {"order_id": order_id}
    headers = {
        'merchant': config.merchant_uuid,
        'sign': generate_sign(config.payment_key, data),
        'Content-Type': 'application/json'
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(API_ENDPOINT, headers=headers, json=data)
        if response.status_code == 200:
            return InvoiceResponse.model_validate(response.json()["result"])
        else:
            return None


async def update_order_status_in_db(invoice: InvoiceResponse):
    """
    Update the status of an invoice in the database.

    Args:
        invoice (InvoiceResponse): The invoice whose status needs to be updated.
    """
    await invoices_db.update_one({"_id": invoice.order_id}, {"$set": invoice.model_dump(mongo=True)})


async def process_invoice(order_id: str) -> Optional[InvoiceResponse]:
    """
        Process the invoice, check its status, and update the database.

        Args:
            bot (Bot): The telegram bot instance.
            order_id (str): The ID of the order.

        Returns:
            Optional[InvoiceResponse]: Returns the invoice if it's final, otherwise None.
    """
    invoice = await check_order_status(order_id)
    if not invoice:
        return None

    await update_order_status_in_db(invoice)
    return invoice if invoice.is_final else None


async def send_notification(bot: Bot, user_id: int, money: int, user_data: dict):
    """
        Send a notification to a user regarding their updated balance.

        Args:
            bot (Bot): The telegram bot instance.
            user_id (int): The ID of the user.
            money (int): The amount added to the user's account.
            user_data (dict): Additional user-related data.
    """
    text = f"حساب شما به مقدار *💰 {money:,} تومان* شارژ شد."
    keyboard = []

    required_keys = ['product', 'traffic', 'duration']
    if all(key in user_data.keys() for key in required_keys):
        keyboard.append([InlineKeyboardButton('🛍 ادامه خرید اشتراک', callback_data='buy-subscriptions{continue}')])
    keyboard.append([InlineKeyboardButton("🖥️ پنل", callback_data="menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(user_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')


async def send_expired_notification(bot: Bot, user_id: int, order_id: str):
    """
    Send a notification to a user regarding an expired invoice.

    Args:
        bot (Bot): The telegram bot instance.
        user_id (int): The ID of the user.
        order_id (str): The ID of the order that is expired.
    """
    text = f"""❌ تراکنش زیر بدلیل عدم پرداخت منقضی شد، لطفا وجهی بابت این تراکنش پرداخت نکنید

🔖 کد رهگیری:  {order_id}"""
    keyboard = [[InlineKeyboardButton("🔍 بررسی فاکتورها", callback_data="check-invoices")],
                [InlineKeyboardButton("🖥️ پنل", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(user_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')


async def cron_job(bot: Bot):
    """
        Periodically checks the status of pending orders and updates the users and database accordingly.

        Args:
            bot (Bot): The telegram bot instance.
    """
    orders = await invoices_db.find({"is_final": False}).to_list(None)
    for order in orders:
        order_id = order["_id"]
        final_invoice = await process_invoice(order_id)
        if final_invoice:
            money = int(final_invoice.additional_data)
            user_id = int(final_invoice.order_id.split('_')[0])
            status = final_invoice.payment_status in ['paid', 'paid_over']
            invoice = await invoices_queue.find_one({'order_id': final_invoice.order_id})

            if invoice and status:
                await send_notification(bot.bot, user_id, money, invoice['user_data'])
                try:
                    await send_notification(bot.bot, config.admin, money, {})
                except:
                    continue
                await users.update_one({'_id': user_id}, {'$inc': {'balance': money}})
            else:
                await send_expired_notification(bot.bot, user_id, invoice['uuid'])
            await invoices_queue.delete_one({'order_id': final_invoice.order_id})
