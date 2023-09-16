import base64
import hashlib
import json

import requests
from configuration import Config
from models.invoice import InvoiceResponse

config = Config()
invoices_db = config.get_db().invoices

# API setup
API_ENDPOINT = "https://api.cryptomus.com/v1/payment/info"


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


def cron_job():
    """
    The function to be run by the cron job every minute.
    """
    orders = invoices_db.find({"is_final": False})
    for order in orders:
        order_id = order["_id"]
        invoice = check_order_status(order_id)
        if invoice:
            update_order_status_in_db(invoice)
