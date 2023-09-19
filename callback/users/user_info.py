from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram import Update
from configuration import Config
from utilities.user_handlers import process_user

# Initialize the configuration
config = Config()


async def user_info(update: Update, context):
    """Sends a message with Contact information."""
    query = update.callback_query
    await query.answer()
    user = process_user(query.from_user, context)

    text = f"""💼 اطلاعات *حساب*.

🔢 *ایدی‌عددی*: `{user.id}`
👥 *تعداد زیرمجموعه ها*: {user.referral_amount}
🛍 *تعداد سرویس ها*: {len(user.subscriptions)}
💎 *موجودی شما*: {user.balance:,} تومان

🔋 لینک *دعوت* زیرمجموعه:
`{user.referral_link}`
"""

    keyboard = [
        [InlineKeyboardButton("💳 شارژ حساب", callback_data="topup")],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')