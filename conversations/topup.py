import httpx
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, \
    CommandHandler
from cryptomus import Client
from callback.menu import menu
from models.invoice import InvoiceResponse, InvoiceRequest
from configuration import Config
from utilities.currency_converter import converter
from minute_tasks.invoice_check import add_job
import re

config = Config()
invoices_db = config.get_db().invoices
payment = Client.payment(config.payment_key, config.merchant_uuid)

TOPUP_AMOUNT, NETWORK, TX_ID = range(3)
CANCEL = "cancel"
TOPUP = "topup"


class TopUpHandler:
    SERVICES_CACHE = None

    @classmethod
    def services(cls):
        """Retrieve and cache available payment services grouped by currency and network."""
        if not cls.SERVICES_CACHE:
            response_data = payment.services()
            grouped = {}
            for service in response_data:
                currency = service['currency']
                network = service['network']
                minimum = service['limit']['min_amount']
                if currency not in grouped:
                    grouped[currency] = {'name': currency, 'network': []}
                grouped[currency]['network'].append([network, minimum])
            cls.SERVICES_CACHE = grouped
        return cls.SERVICES_CACHE

    @classmethod
    def generate_keyboard(cls, amount):
        """Generate a keyboard with available payment services."""
        keyboard = [[InlineKeyboardButton('💰 پرداخت ریالی', callback_data=f'topup_currency{{IRT}}')]]
        row = []
        count = 0
        services = cls.services()
        for service_name in cls.services().keys():
            converted = amount/converter(service_name)
            if not any([float(x[1]) < converted for x in services[service_name]['network']]):
                continue
            if count % 5 == 0 and count != 0:
                keyboard.append(row)
                row = []
            button = InlineKeyboardButton(service_name, callback_data=f'topup_currency{{{service_name}}}')
            row.append(button)
            count += 1
        if row:
            keyboard.append(row)
        return keyboard

    @classmethod
    def generate_network_keyboard(cls, currency, irt_amount):
        """Generate a keyboard with available networks for the chosen currency."""
        service = cls.services()[currency]
        keyboard = []
        for net, minimum in service['network']:
            limit = cls.limits(currency, net)
            amount = float(irt_amount)/converter(currency)
            if float(amount) < float(limit['min_amount']) or float(amount) > float(limit['max_amount']):
                continue
            keyboard.append(InlineKeyboardButton(f'{net}', callback_data=f'topup_network{{{net}}}'))
        return [keyboard]

    @staticmethod
    def limits(currency, network):
        """Retrieve the minimum and maximum amounts for a given currency and network."""
        response_data = payment.services()
        for service in response_data:
            if service['currency'] == currency and service['network'] == network:
                return {
                    'min_amount': service['limit']['min_amount'],
                    'max_amount': service['limit']['max_amount']
                }
        return None

    @staticmethod
    def generate_order_id(user_id):
        """Generate a unique order ID based on the user ID."""
        count = invoices_db.count_documents({"_id": {"$regex": f"^{user_id}"}})
        return f'{user_id}_{count + 1}'

    @staticmethod
    def create_and_validate_invoice(context, order_id):
        """Create and validate an invoice based on the user's input."""
        invoice_request = InvoiceRequest(
            amount=str(context.user_data['topup']['irt_amount']/converter(context.user_data['topup']['currency'])),
            order_id=order_id,
            currency=context.user_data['topup']['currency'],
            network=context.user_data['topup']['network'],
            additional_data=f'{context.user_data["topup"]["irt_amount"]}'
        )
        return InvoiceResponse.model_validate(payment.create(invoice_request.model_dump(exclude_none=True)))

    @staticmethod
    def insert_invoice_if_not_exists(invoice_response):
        """Insert the invoice into the database if it doesn't exist."""
        if not invoices_db.find_one({'_id': invoice_response.order_id}):
            invoices_db.insert_one(invoice_response.model_dump(by_alias=True, mongo=True))

    @staticmethod
    def generate_invoice_text(invoice_response):
        """Generate a text representation of the invoice."""
        amount_text = f'`{invoice_response.amount}` *{invoice_response.currency}*({invoice_response.network})'
        return f"""💵 *مقدار تراکنش* (_کارمزد ارسال را شما پرداخت میکنید_):
{amount_text}
    
    🔖 *کد رهگیری*: `{invoice_response.uuid}`
🌐 *شبکه*: {invoice_response.network}
💳 *آدرس ولت*: `{invoice_response.address}`

📌 پس از پرداخت و تایید تراکنش توسط شبکه موجودی شما به مبلغ  {int(invoice_response.additional_data):,} تومان شارژ خواهد شد , درنظر داشته باشید ممکن است روند تایید تراکنش  بین 1 تا 20 دقیقه طول بکشد

⚠️ هشدار: در صورت اشتباه وارد کردن مبلغ تراکنش و آدرس ولت، ممکن است تراکنش تایید نشود و بازگشت وجه امکان پذیر نیست

〽️ پرداخت شما به صورت خودکار پردازش می شود"""

    @staticmethod
    async def _send_message(target, text, next_state, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="cancel")]])):
        """Send or edit a message based on the target type."""
        if isinstance(target, Message):
            await target.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:  # assuming it's a query object
            await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return next_state

    async def topup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Entry point for the top-up conversation."""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
        else:
            query = update.message
        context.user_data['topup'] = {}
        return await self._send_message(query, "لطفا 💵 *مبلغ* را به تومان ارسال کتید. (_حداقل پنجاه هزار تومان_)",
                                        TOPUP_AMOUNT)

    async def select_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the user's input for the top-up amount."""
        message = update.message.text
        if int(message) < 50000:
            return await self._send_message(update.message, "❌ دوباره ارسال کنید، حداقل مقدار *پنجاه هزار تومان* است.",
                                            TOPUP_AMOUNT)
        context.user_data['topup']['irt_amount'] = int(message)
        text = "لطفا 💰 *ارز* مورد نظر برای پرداخت رو انتخاب کنید."
        keyboard = self.generate_keyboard(int(message))
        keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data=CANCEL)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        return await self._send_message(update.message, text, NETWORK, reply_markup)

    async def network(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the user's choice of network for the chosen currency."""
        query = update.callback_query
        await query.answer('درحال دریافت شبکه ها')
        match = re.findall(r"\{(.*?)}", query.data)
        currency = match[0]
        context.user_data['topup']['currency'] = currency
        keyboard = self.generate_network_keyboard(currency, context.user_data['topup']['irt_amount'])
        if not keyboard:
            # Handle the case where there are no valid networks for the given amount
            return NETWORK
        text = f'لطفا 🌐 *شبکه* موردنظر خود را برای {currency} انتخاب کنید.'
        keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data=CANCEL)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        return await self._send_message(query, text, TX_ID, reply_markup)

    async def txid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the user's choice of transaction ID."""

        query = update.callback_query
        await query.answer('درحال ساخت فاکتور')

        # Determine network from query data
        network = re.findall(r"\{(.*?)}", query.data)[0]
        context.user_data['topup']['network'] = network

        if query.data == 'topup_currency{IRT}':
            context.user_data['topup']['currency'] = 'TRX'
            context.user_data['topup']['network'] = 'TRON'

        user_id = str(query.from_user.id)
        order_id = self.generate_order_id(user_id)
        invoice_response = self.create_and_validate_invoice(context, order_id)
        self.insert_invoice_if_not_exists(invoice_response)

        reply_markup = None
        if (context.user_data['topup']['currency'] == 'TRX' and
                context.user_data['topup']['network'] == 'TRON'):
            amount = str(context.user_data['topup']['irt_amount'] / converter(context.user_data['topup']['currency']))
            url = httpx.post(
                config.portal_url,
                data={'key': config.portal_key, 'amount': amount, 'wallet': invoice_response.address},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('💰 پرداخت ریالی', url=url.text, callback_data='notabutton')]])

        if 'subscription' not in context.user_data:
            context.user_data['subscription'] = {}

        add_job(invoice_response.order_id, context.user_data['subscription'])
        text = self.generate_invoice_text(invoice_response)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

        return await self._send_message(query.message, "📝  *فاکتور* شما با موفقیت ساخته شد.", ConversationHandler.END)


handler_instance = TopUpHandler()

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handler_instance.topup_start, pattern=f'^{TOPUP}$'),
                  CommandHandler('charge', handler_instance.topup_start)],
    states={
        TOPUP_AMOUNT: [MessageHandler(filters.Regex('^\d{4,}$'), handler_instance.select_amount)],
        NETWORK: [CallbackQueryHandler(handler_instance.txid, pattern='^topup_currency{IRT'),
                  CallbackQueryHandler(handler_instance.network, pattern='^topup_currency{')],
        TX_ID: [CallbackQueryHandler(handler_instance.txid, pattern='^topup_network{')]
    },
    fallbacks=[CallbackQueryHandler(menu, pattern=f"^{CANCEL}$")]
)
