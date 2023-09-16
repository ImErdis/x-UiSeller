from cryptomus import Client
from models.invoice import InvoiceRequest, InvoiceResponse
from configuration import Config

config = Config()
invoices_db = config.get_db().invoices

PAYMENT_KEY = 'if7oiiAZyTGUk5BpC33rLiUCgxx887qD2Eb2pnWXjubj7ATfkX74WS4Cqe8xvHujNQ9qMYgMcCbbr45FHGIHnO5mOoyVbXpuCCy8KKzlRoHgiyuFMjqnKH3xbJyCCQZD'
MERCHANT_UUID = 'f3225265-c19f-4ea5-9d1c-4598c10aed58'

payment = Client.payment(PAYMENT_KEY, MERCHANT_UUID)


result = payment.services()
payment_methods = []
for payment_service in result:
    if payment_service['is_available']:
        payment_methods.append([payment_service['network'], payment_service['currency']])
print(payment_methods)

payment_method = payment_methods[0]
invoice = InvoiceRequest(amount="110", currency='USD', order_id="2")
print(invoice.model_dump(exclude_none=True))
invoice_response = InvoiceResponse.model_validate(payment.create(invoice.model_dump(exclude_none=True)))
if not invoices_db.find_one({'_id': invoice_response.order_id}):
    invoices_db.insert_one(invoice_response.model_dump(by_alias=True, mongo=True))
