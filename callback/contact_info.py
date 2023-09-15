from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram import Update
from configuration import Config

config = Config('configuration.yaml')


async def contact_info(update: Update, context):
    """Sends a message with Contact information."""
    query = update.callback_query
    await query.answer()

    text = f"""🛎 اگر *سوال*، *نگرانی* یا *نیاز به کمک* دارید، لطفاً با ما تماس بگیرید. تیم پشتیبانی ما آماده ارائه خدمات به شما است!

📋 *اطلاعات تماس*:
🆔 @{config.get_support_id()}

_ما سعی می‌کنیم به سرعت و با کمک‌های موثر، رضایت شما را تضمین کنیم. در صورت داشتن هرگونه سؤال، بدون تردید با ما تماس بگیرید._

*🌐 به کانال ما مراجعه کنید: @{config.get_channel_id()}*"""

    keyboard = [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')